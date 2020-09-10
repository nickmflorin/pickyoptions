from copy import deepcopy
import functools
import logging
import six
import sys

from pickyoptions import settings, constants
from pickyoptions.exceptions import (
    OptionUnrecognizedError,
    OptionInvalidError,
    OptionsInvalidError,
    OptionsNotConfiguredError,
    OptionsNotPopulatedError,
    OptionsPopulatingError
)
from pickyoptions.lib.utils import check_num_function_arguments

from .base import track_init
from .configurable import Configurable, requires_configured
from .configuration import Configuration
from .configurations import Configurations
from .option import Option
from .parent import Parent
from .populating import Populating, requires_not_populating, requires_populated


logger = logging.getLogger(settings.PACKAGE_NAME)


class PostProcessConfiguration(Configuration):
    def __init__(self, field):
        super(PostProcessConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(PostProcessConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 1):
                self.raise_invalid(
                    "Must be a callable that takes the options instance as it's first and "
                    "only argument."
                )


class ValidateConfiguration(Configuration):
    def __init__(self, field):
        super(ValidateConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(ValidateConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 1):
                self.raise_invalid(
                    "Must be a callable that takes the options instance as it's first and "
                    "only argument."
                )


class Options(Configurable, Populating, Parent):
    """
    The entry point for using pickyoptions in a project.

    Represents a series of configurable `obj:Option`(s) that define the framework for which
    package users can specify and override options in the package.

    Configuring your package with options can be done either by a direct import from pickyoptions
    or by explicitly instantiating the `obj:Options` itself:

    ~~~ my_package.__init__

    >>> from pickyoptions import options
    >>> options.configure(
    >>>     Option(field="foo", type=(str, int)),
    >>>     Option(field="bar", type=(str, int))
    >>> )
    >>> options.populate(foo="fooey")

    or

    >>> from pickyoptions import Options
    >>> options = Options(
    >>>     Option(field="foo", type=(str, int)),
    >>>     Option(field="bar", type=(str, int))
    >>> )
    >>> options.populate(foo="fooey")

    ~~~ my_package.file

    >>> from pickyoptions import options
    >>> assert options.foo = "fooey"

    or

    ~~~ my_package.file

    >>> from my_package import options
    >>> assert options.foo = "fooey"
    """
    # Configurable Implementation Properties
    not_configured_error = OptionsNotConfiguredError
    not_populated_error = OptionsNotPopulatedError

    # Populating Implmentation Properties
    populating_error = OptionsPopulatingError

    # Parent Implementation Properties
    child_cls = Option
    child_identifier = "field"
    unrecognized_child_error = OptionUnrecognizedError

    configurations = Configurations(
        PostProcessConfiguration('post_process'),
        ValidateConfiguration('validate'),
        Configuration('strict', default=False, types=(bool, )),
    )

    @track_init
    def __init__(self, *args, **kwargs):
        # Keeps track of the `obj:Option`(s) that were set on population so the state of the
        # `obj:Options` instance can be restored after overrides are applied.
        # self._populated_option_values = {}

        # Keeps track of which `obj:Option`(s) are in the process of being populated, so they can
        # be cleared and post populated after the population finishes.
        self._population_queue = []
        self._overridden_queue = []

        Populating.__init__(self)
        Configurable.__init__(self, reverse_assign_configurations=False, **kwargs)
        Parent.__init__(self, children=list(args))

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls, **self.configurations.configured_configurations)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            object.__setattr__(result, k, deepcopy(v, memo))
        return result

    def __repr__(self):
        # We have to use the initialized property because that is set at the very fore front
        # of instantiation - populated may or may not be set at this point.
        if self._initialized:
            if self.populated:
                return "<{cls_name} {params}>".format(
                    cls_name=self.__class__.__name__,
                    params=", ".join(["{k}={v}".format(k=k, v=v) for k, v in self.zipped])
                )
            # Note: This causes problems if the options are not set as the private variable yet.
            return "<{cls_name} UNPOPULATED [{options}]>".format(
                cls_name=self.__class__.__name__,
                options=", ".join([option.field for option in self.children])
            )
        return "<{cls_name} {state}>".format(
            state=constants.NOT_INITIALIZED,
            cls_name=self.__class__.__name__
        )

    def __getattr__(self, k):
        # TODO: Do we need to check if it is configured here?
        # TODO: Should this part be moved to configurable?
        # WARNING: This might break if there is a configuration that is named the same as an
        # option - we should prevent that.
        # If the value is referring to a configuration, return the configuration value.
        if self.configured and self.configurations.has_child(k):
            configuration = getattr(self.configurations, k)
            return configuration.value

        # We have to assume that the value is referring to an `obj:Option` child.  Note that the
        # value of the option is returned in the super() method, because of the definition of the
        # child_value() method here.
        option_value = super(Options, self).__getattr__(k)
        if not self.populated:
            self.raise_not_populated()
        return option_value

    def __call__(self, *args, **kwargs):
        self.populate(*args, **kwargs)

    def __setattr__(self, k, v):
        if k.startswith('_'):
            super(Options, self).__setattr__(k, v)
        else:
            if self.overriding or self.populating:
                raise ValueError()

            # TODO: Do we need to check if it is configured here?
            # TODO: Should this part be moved to configurable?
            # WARNING: This might break if there is a configuration that is named the same as an
            # option - we should prevent that.
            # If the value is referring to a configuration, set the configuration value.
            if self.configured and self.configurations.has_child(k):
                setattr(self.configurations, k, v)
            else:
                # TODO: Do we want to allow the setting of new options that are not already set?
                option = self.get_child(k)

                # NOTE: These first two conditionals aren't really necessary anymore?  It looks like
                # if the options are overriding or populating, the option methods .populate and
                # .override are called themselves inside the methods...

                # If the `obj:Options` are populating, we will wait to do the `obj:Option`
                # validation and post-processing with options until the `obj:Options` are done
                # populating - otherwise, the `obj:Options` won't have the most recent values yet.
                # We will also wait to do the validation and post-processing of the overall
                # # `obj:Options` until they are populated, for the same reasons.
                # if self.populating:
                #     option.populate(v)
                #     # Add the populated option to the queue of options populated during this
                #     # population cycle.
                #     assert option.field not in [opt.field for opt in self._population_queue]
                #     self._population_queue.append(option)
                # elif self.overriding:
                #     option.override(v)
                #     assert option.field not in [opt.field for opt in self._overridden_queue]
                #     self._overridden_queue.append(option)
                # else:
                # The `obj:Option` will not be populating, so setting the value directly on the
                # `obj:Option` will trigger the `obj:Option` to do validation and post-processing
                # with the `obj:Options` instance.
                option.value = v
                self.do_validate()
                self.do_post_process()

    def child_value(self, child):
        return child.value

    @property
    def options(self):
        # Not stored as a separate configuration variable but still requires validation of the
        # configuration when set/changed.
        return self._children

    @options.setter
    def options(self, value):
        # Not stored as a separate configuration variable but still requires validation of the
        # configuration when set/changed.
        # NOTE: This would not get triggered if we were to set `children`, but `children` is not
        # directly setable.
        self.new_children(value)
        self.validate_configuration()
        # for option in self._options:
        #     option._options = self

    def configure(self, *args, **kwargs):
        self.reset()
        super(Options, self).configure(*args, **kwargs)

    def raise_invalid_option(self, field, **kwargs):
        """
        Raises an OptionInvalidError (or an extension) for the `obj:Option` associated with
        the provided field.
        """
        option = self.get_child(field)
        return option.raise_invalid(**kwargs)

    def raise_invalid(self, *args, **kwargs):
        """
        Raises an OptionsInvalidError (or an extension) for the overall `obj:Options`.
        """
        kwargs.setdefault('cls', OptionsInvalidError)
        return self.conditional_raise(*args, **kwargs)

    def populate(self, *args, **kwargs):
        """
        Populates the configured `obj:Options` instance with values for each defined `obj:Option`.
        """
        data = dict(*args, **kwargs)

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            if k not in self.identifiers:
                self.raise_no_child(field=k)

        self.reset()
        with self.population_routine():
            for option in self.options:
                if option.field in data:
                    option.populate(data[option.field])
                    assert option.field not in [opt.field for opt in self._population_queue]
                    # Add the `obj:Option` to the queue of `obj:Option`(s) that were populated
                    # in a given routine, so the queue can be cleared and the `obj:Option`(s) in the
                    # queue can be post routined, after the `obj:Options` are done with the routine.
                    self._population_queue.append(option)
                    # Keep track of the fields that were explicitly set so that they can be
                    # reset to the originals at a later point in time.  This isn't really necessary
                    # anymore, because the options themselves track it - nonetheless we keep track
                    # for completeness.  This isn't really the populated value either, because the
                    # real value would be the `obj:Options` instance.
                    if self._populated_value == constants.NOTSET:
                        self._populated_value = {}
                    self._populated_value[option.field] = data[option.field]
                else:
                    # This will validate that the option is not required before proceeding any
                    # further.
                    option.value = None

    def override(self, *args, **kwargs):
        data = dict(*args, **kwargs)

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            if k not in self.identifiers:
                self.raise_no_child(field=k)

        with self.override_routine():
            for option in self.options:
                if option.field in data:
                    option.override(data[option.field])
                    assert option.field not in [opt.field for opt in self._overridden_queue]
                    # Add the `obj:Option` to the queue of `obj:Option`(s) that were populated
                    # in a given routine, so the queue can be cleared and the `obj:Option`(s) in the
                    # queue can be post routined, after the `obj:Options` are done with the routine.
                    self._overridden_queue.append(option)
                    # Keep track of the fields that were explicitly set so that they can be
                    # reset to the originals at a later point in time.  This isn't really necessary
                    # anymore, because the options themselves track it - nonetheless we keep track
                    # for completeness.  This isn't really the populated value either, because the
                    # real value would be the `obj:Options` instance.
                    if self._overridden_value == constants.NOTSET:
                        self._overridden_value = {}
                    self._overridden_value[option.field] = data[option.field]

    # In the case of the options, post population requires the values are populated.  In the case
    # of the option, post population requires that they are set.
    @requires_not_populating
    @requires_populated
    def post_population(self):
        """
        Performs routines that are meant to be performed immediately after the `obj:Options`
        population finishes.

        The overall `obj:Options` are validated and post-processed based on the user provided
        `post_process` and `validate` configurations.

        Then, because the the `obj:Options` were still populating at the time each `obj:Option`
        was populated, even the last, the queue of populated options is cleared - as each
        individual `obj:Option` in the queue is triggered to perform their own post population
        routines.
        """
        super(Options, self).post_population()
        self.do_validate()
        self.do_post_process()
        self.clear_population_queue()

    # @requires_not_overriding
    @requires_populated
    def post_override(self):
        super(Options, self).post_override()
        self.do_validate()
        self.do_post_process()
        self.clear_options_queue()

    @requires_not_populating
    def pre_population(self):
        logger.debug('Performing pre-population on %s.' % self.__class__.__name__)
        super(Options, self).pre_population()
        assert self._options_queue == []  # ??
        self._options_queue = []

    # @requires_not_restoring
    # @requires_not_overriding
    @requires_not_populating
    def clear_options_queue(self):
        """
        Clears the queue of `obj:Option`(s) that were either ... in the last routine cycle
        and triggers the post population routines on each individual `obj:Option`.
        """
        logger.debug("Clearing %s options from population queue." % len(self._population_queue))
        for option in self._options_queue:
            # We can't make this assertion now that we are using this method more generally.
            # assert option.populated
            option.post_routine()
            # I think we need to post populate with options here, right?
            option.post_routine_with_options()
        self._options_queue = []

    # @requires_not_overriding
    # def clear_overridden_queue(self):
    #     logger.debug("Clearing %s options from overridden queue." % len(self._overridden_queue))
    #     for option in self._overridden_queue:
    #         assert option.overridden
    #         option.post_routine()
    #         # I think we need to post populate with options here, right?
    #         option.post_routine_with_options()
    #     self._population_queue = []

    def reset(self):
        """
        Resets the `obj:Options` state back to the post configuration state before any options
        were populated.

        Note that after the `obj:Options` have been reset, the `obj:Options` require
        re-population of the options before any option values can be accessed on the `obj:Options`
        instance.  This is because potentially required options will not be set anymore, so
        we cannot access their values until they are set.
        """
        super(Options, self).reset()
        # Do these assertions make sense?  We clear the queues when the routines are finished...
        assert self._options_queue == []

    @requires_populated
    def restore(self):
        """
        Resets the `obj:Options` instance to it's state immediately after it was last populated.
        Any overrides applied since the last population will be removed and the `obj:Options`
        values will correspond to their values from the last population of the `obj:Options`
        instance.
        """
        if not self.overridden:
            logger.debug(
                "Not restoring %s because the instance is not "
                "overridden." % self.__class__.__name__
            )
            return

        # Do we really want to use the population cycle here?  There has got to be a cleaner
        # way of doing that.
        with self.population_routine():
            for option in self.options:
                # Note:  We can't simply reset the options and reapply the last populated
                # options because the reset removes the populated options.  This is why we should
                # keep a queue of the populated options in memory.
                if option.field in self._overrides:
                    # The option need not be in the populated options, since the override
                    # could have been applied to a default value.  In this case, we have to
                    # remove from the mapping.
                    if option.field not in self._populated_option_values:
                        assert option.required is False
                        # TODO: Implement __delattr__ method and __delitem__ method?
                        del self._mapping[option.field]
                    else:
                        setattr(self, option.field, self._populated_options[option.field])
        self._overrides = {}

    @requires_populated
    def do_validate(self):
        """
        Validates the overall `obj:Options` instance (after the children `obj:Option`(s) are fully
        populated) based on the user provided `validate` configuration.

        NOTE:
        ----
        In this case, the validation of the children `obj:Option`(s) is different than the
        validation that runs when values are set on the children `obj:Option`(s).  In this case,
        the validation of the children `obj:Option`(s) includes the parent `obj:Options` instance,
        since it has been fully populated at this point.

        NOTE:
        ----
        The provided `validate` configuration value must be a callable that takes the `obj:Options`
        as it's first and only argument.  To indicate that the `obj:Options` are invalid, one of
        3 things can be done:

        (1) Raise an instance of `obj:OptionInvalidError` to indicate that a single option in
            the `obj:Options` is invalid.

            Example:
            -------
            def validate(options):
                if options.foo > options.bar:
                    raise OptionInvalidError("`foo` is too large.")

        (2) Raise an instance of `obj:OptionsInvalidError` to indicate that the options as a whole
            are invalid.

            Example:
            -------
            def validate(options):
                if options.foo > options.bar:
                    raise OptionsInvalidError("`foo` must be less than or equal to `bar`.")

        (3) Call the `.raise_invalid()` method on the passed in `obj:Options` instance.

            Example:
            -------
            def validate(options):
                if options.foo > options.bar:
                    options.raise_invalid("`foo` must be less than or equal to `bar`.")

        (4) Return a string error message.

            Example:
            -------
            def validate(options):
                if options.foo > options.bar:
                    return "`foo` must be less than or equal to `bar`."

        If the `obj:Options` are deemed valid, `None` must be returned.  If the returned value
        is not `None` and the validate method does not comform to the (4) protocols above, an
        exception will be raised.
        """
        configuration = self.configurations['validate']
        if configuration.value is not None:
            logger.debug("Validating overall options.")
            try:
                result = configuration.value(self)
            except Exception as e:
                if isinstance(e, (OptionsInvalidError, OptionInvalidError)):
                    six.reraise(*sys.exc_info())
                else:
                    configuration.raise_invalid(
                        message=(
                            "If raising an exception to indicate that the options are invalid, "
                            "the exception must be an instance of OptionsInvalidError or "
                            "OptionInvalidError.  It is recommended to use the `raise_invalid` "
                            "method on the options instance or on the specific option."
                        )
                    )
            else:
                if result is not None:
                    if not isinstance(result, six.string_types):
                        configuration.raise_invalid(
                            message=(
                                "The option validate method must return a string error "
                                "message, raise an instance of OptionInvalidError or raise an "
                                "instance of OptionsInvalidError in the case that the value or "
                                "values are invalid.  If the value is valid, it must return None."
                            )
                        )
                    self.raise_invalid(message=result)

    @requires_populated
    def do_post_process(self, children=None):
        """
        Performs the post-process routine for the overall `obj:Options` instance (after the
        children `obj:Option`(s) are fully populated) based on the user provided `post_process`
        configuration.  Optionally post-processes the provided children `obj:Option`(s) with the
        populated `obj:Options`.

        NOTE:
        ----
        In this case, the post-processing of the children `obj:Option`(s) is different than the
        post-processing that runs when values are set on the children `obj:Option`(s).  In this
        case, the post-processing of the children `obj:Option`(s) includes the parent `obj:Options`
        instance, since it has been fully populated at this point.

        NOTE:
        ----
        The `post_process` method provided in the `obj:Options` configuration must be a callable
        that takes the `obj:Options` instance as it's first and only argument.

        The `post_process_with_options` methods of the children `obj:Option`(s) must be callables
        that take the `obj:Option` value as their first argument, the `obj:Option` instance
        as their second argument and the populated `obj:Options` instance as their third argument.
        """
        if self.post_process is not None:
            logger.debug("Post processing options")
            self.post_process(self)

    @requires_populated
    def local_override(self, func):
        """
        Decorator for functions that allows the global options to be temporarily overridden while
        inside the context of the decorated method.  The decorated method can be provided
        additional keyword arguments to specify the values of the options to be overridden.

        Example:
        -------
        from my_package import options

        options.configure(HOST_NAME="0.0.0.0")

        @options.local_override
        def get_host_name(port):
            if options.HOST_NAME == "0.0.0.0":
                return "localhost:port"
            return "%s:%s" % (options.HOST_NAME, port)

        >>> get_host_name(8000)
        >>> "localhost:8000"

        >>> get_host_name(8000, HOST_NAME="123.123.123.123")
        >>> "123.123.123.123:8000"
        """
        @functools.wraps(func)
        def inner(*args, **kwargs):
            local_options = {}
            option_overrides = kwargs.get('options', kwargs)
            for k, v in option_overrides.items():
                if k in self.option_fields:
                    local_options[k] = kwargs.pop(k)

            # Store current options before the local override in memory, so they can be used
            # after the function returns to reset the `obj:Options` instance.
            current_options = deepcopy(self.__dict__)

            # Apply overrides and allow the method to run with the overrides applied.
            self.override(local_options)
            result = func(*args, **kwargs)

            # Wipe out the locally scoped overrides and reset the state back to what it was
            # before the method was called.
            self.populate(current_options)
            return result

        return inner

    @requires_configured
    def validate_configuration(self, *args, **kwargs):
        pass


options = Options()
