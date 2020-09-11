from copy import deepcopy
import functools
import logging
import six
import sys

from pickyoptions import settings, constants

from pickyoptions.base import track_init
from pickyoptions.configuration import Configuration
from pickyoptions.configuration.configurations import CallableConfiguration
from pickyoptions.configurable import Configurable
from pickyoptions.configurations import Configurations
from pickyoptions.option import Option
from pickyoptions.option.exceptions import (
    OptionUnrecognizedError, OptionInvalidError)
from pickyoptions.parent import Parent
from pickyoptions.routine import Routine, Routines

from .exceptions import (
    OptionsInvalidError, OptionsNotConfiguredError, OptionsConfiguringError)


logger = logging.getLogger(settings.PACKAGE_NAME)


class OptionsRoutine(Routine):
    @Routine.require_not_in_progress
    def clear_queue(self):
        """
        Clears the queue of `obj:Option`(s) that were either ... in the last
        routine cycle and triggers the post population routines on each
        individual `obj:Option`.
        """
        logger.debug(
            "Clearing %s options from population queue."
            % len(self.queue)
        )
        for option in self.queue:
            # We can't make this assertion now that we are using this method
            # more generally.
            # assert option.populated
            # I don't think we need to call the post_routine, because that will
            # be called when the value is set...
            # option.post_routine()
            # I think we need to post populate with options here, right?
            option.post_routine_with_options()
        super(OptionsRoutine, self).clear_queue()

    # In the case of the options, post population requires the values are
    # populated.  In the case  of the option, post population requires that
    # they are set.
    @Routine.require_finished
    def post_routine(self, instance):
        """
        Performs routines that are meant to be performed immediately after the
        `obj:Options` population finishes.

        The overall `obj:Options` are validated and post-processed based on the
        user provided `post_process` and `validate` configurations.

        Then, because the the `obj:Options` were still populating at the time
        each `obj:Option` was populated, even the last, the queue of populated
        options is cleared - as each individual `obj:Option` in the queue is
        triggered to perform their own post population routines.
        """
        super(OptionsRoutine, self).post_routine(instance)
        instance.do_validate()
        instance.do_post_process()


class Options(Configurable, Parent):
    """
    The entry point for using pickyoptions in a project.

    Represents a series of configurable `obj:Option`(s) that define the
    framework for which package users can specify and override options in the
    package.

    Parameters:
    ----------

    Usage:
    -----
    Configuring your package with options can be done either by a direct import
    from pickyoptions or by explicitly instantiating the `obj:Options` itself:

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
    # SimpleConfigurable Implementation Properties
    not_configured_error = OptionsNotConfiguredError
    configuring_error = OptionsConfiguringError

    # Parent Implementation Properties
    child_cls = Option
    child_identifier = "field"
    unrecognized_child_error = OptionUnrecognizedError

    configurations = Configurations(
        CallableConfiguration(
            'post_process',
            num_arguments=1,
            error_message="Must be a callable that takes the options instance as "
            "it's first and only argument."
        ),
        CallableConfiguration(
            'validate',
            num_arguments=1,
            error_message="Must be a callable that takes the options instance as "
            "it's first and only argument."
        ),
        Configuration('strict', default=False, types=(bool, )),
    )

    @track_init
    def __init__(self, *args, **kwargs):
        self.routines = Routines(
            OptionsRoutine(id='populating'),
            OptionsRoutine(id='overriding'),
            OptionsRoutine(id='restoring')
        )
        Parent.__init__(self,
            children=list(args), child_value=lambda child: child.value)
        Configurable.__init__(self, **kwargs)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(
            cls, **self.configurations.explicitly_set_configurations)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            object.__setattr__(result, k, deepcopy(v, memo))
        return result

    def __repr__(self):
        if self.initialized:
            if self.routines.populating.finished:
                return "<Populated {cls_name} {params}>".format(
                    cls_name=self.__class__.__name__,
                    params=", ".join([
                        "{k}={v}".format(k=k, v=v)
                        for k, v in self.zipped
                    ])
                )
            return "<{state} {cls_name} [{options}]>".format(
                cls_name=self.__class__.__name__,
                state=constants.NOT_POPULATED,
                options=", ".join([option.field for option in self.children])
            )
        return "<{state} {cls_name}>".format(
            state=constants.NOT_INITIALIZED,
            cls_name=self.__class__.__name__
        )

    def __getattr__(self, k):
        # TODO: Revisit this - do we even want to be checking for the underscore?
        # Do we need to be checking if the options are initialized?
        if settings.DEBUG and k.startswith('_'):
            raise AttributeError(
                "The %s instance does not have attribut %s."
                % (self.__class__.__name__, k)
            )
        # TODO: Do we need to check if it is configured here?
        # TODO: Should this part be moved to configurable?
        # WARNING: This might break if there is a configuration that is named the
        # same as an option - we should prevent that.
        # If the value is referring to a configuration, return the configuration
        # value.
        if self.configured and self.configurations.has_child(k):
            configuration = getattr(self.configurations, k)
            return configuration.value

        # We have to assume that the value is referring to an `obj:Option`.
        # The return of the super() method is the `obj:Option` value, not the
        # `obj:Option` itself.=
        option_value = super(Options, self).__getattr__(k)
        if not self.routines.populating.finished:
            self.raise_not_populated()
        return option_value

    def __call__(self, *args, **kwargs):
        self.populate(*args, **kwargs)

    def __setattr__(self, k, v):
        if not self.initialized:
            object.__setattr__(self, k, v)
        else:
            assert self.configured
            if self.configurations.has_child(k):
                configuration = self.configurations[k]
                assert configuration.configured == self.configurations.configured == self.configured  # noqa
                setattr(self.configurations, k, v)
            else:
                option = self.get_child(k)
                option.value = v
                self.do_validate()
                self.do_post_process()

    def get_option(self, k):
        return self.get_child(k)

    @property
    def options(self):
        return self._children

    @options.setter
    def options(self, value):
        # Not stored as a separate configuration variable but it is treated as a
        # configuration, in the sense that changing it requires re-validation of
        # the configuration.
        self.reset()
        self.new_children(value)
        self.validate_configuration()

    def pre_configuration(self):
        self.reset()

    def raise_invalid_option(self, field, **kwargs):
        """
        Raises an OptionInvalidError (or an extension) for the `obj:Option`
        associated with the provided field.
        """
        option = self.get_child(field)
        return option.raise_invalid(**kwargs)

    def raise_invalid(self, *args, **kwargs):
        """
        Raises an error to indicate that the overall `obj:Options` are invalid.
        """
        kwargs.setdefault('cls', OptionsInvalidError)
        return self.raise_with_self(*args, **kwargs)

    def populate(self, *args, **kwargs):
        """
        Populates the configured `obj:Options` instance with values for each
        defined `obj:Option`.
        """
        assert len(self.routines.populating.queue) == 0
        self.reset()

        data = dict(*args, **kwargs)

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            self.raise_if_child_missing(k)

        with self.routines.populating(self) as routine:
            for option in self.options:
                # Add the `obj:Option` to the queue of `obj:Option`(s) that were
                # populated in a given routine so we can track which options need
                # to be post validated and # post processed with the most up to
                # date `obj:Options` when the routine finishes. This needs to
                # happen regardless of whether or not the option is in the data.
                assert option not in routine.queue
                routine.add_to_queue(option)

                if option.field in data:
                    option.populate(data[option.field])
                    # Keep track of the options that were explicitly populated so
                    # they can be used to reset the `obj:Options` to it's
                    # previously populated state at a later point in time.
                    routine.store(option)
                else:
                    # This will set the default on the `obj:Option` if it is not
                    # required.  It will also validate that the option is not
                    # required before proceeding any further.
                    option.set_default()

    def override(self, *args, **kwargs):
        """
        Overrides the configured `obj:Options` instance with values for each
        defined `obj:Option`.
        """
        # Note that we do not reset the overriding queue.
        assert self.routines.overriding.queue == []
        data = dict(*args, **kwargs)

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            self.raise_if_child_missing(k)

        with self.routines.overriding(self) as routine:
            for k, v in data.items():
                option = self.get_child(k)
                option.override(v)
                # Add the `obj:Option` to the queue of `obj:Option`(s) that were
                # populated in a given routine, so we can track which options
                # need to be post validated and post processed with the most up
                # to date `obj:Options` when the routine finishes.
                assert option not in routine.queue
                routine.add_to_queue(option)

            # Keep track of the options that were overridden AT EACH overriding
            # routine, so the state of the `obj:Options` can be reverted back to
            # a previous override or not overrides at all.
            routine.store(routine.queue)

    def clear_override(self):
        raise NotImplementedError()

    def clear_overrides(self, n=1):
        raise NotImplementedError()

    @property
    def overridden_options(self):
        all_overridden_options = []
        for set_of_options in self.routines.overriding.history:
            for option in set_of_options:
                if option not in all_overridden_options:
                    all_overridden_options.append(option)
        return all_overridden_options

    @Routine.require_finished(routine='populating')
    def restore(self):
        """
        Resets the `obj:Options` instance to it's state immediately after it was
        last populated.  Any overrides applied since the last population will be
        removed and the `obj:Options` values will correspond to their values
        from the last population of the `obj:Options` instance.

        NOTE:
        ----
        Since we are restoring the values back to something that already existed
        on the `obj:Options`, the re-validation from the routine might be
        overkill.  However, we still need the routine for the post-processing,
        as we want to post-process after any change to the options.
        """
        # Currently, resetting the restoring routine is not necessary/does not
        # have an affect, but  we will still do it for purposes of consistency.
        # Down the line, it might be important  to do so.
        self.routines.restoring.reset()

        # TODO: Should we maybe just check the number of options in the override
        # queue?
        if not self.routines.overriding.finished:
            logger.debug(
                "Not restoring %s because the instance is not overridden."
                % self.__class__.__name__)
            return

        with self.routines.restoring(self) as routine:
            # Restore the options that were at any point overridden.
            for option in self.overridden_options:
                option.restore()
                # I don't think we really need to do these, but for completenes
                # sake we will.
                routine.add_to_queue(option)
                routine.store(option)

        self.routines.overriding.clear_history()

    def reset(self):
        """
        Resets the `obj:Options` state back to the post configuration state
        before any options were populated.

        Note that after the `obj:Options` have been reset, the `obj:Options`
        require re-population of the options before any option values can be
        accessed on the `obj:Options` instance.  This is because potentially
        required options will not be set anymore, so we cannot access their
        values until they are set.
        """
        self.routines.reset()
        for option in self.options:
            option.reset()

    @Routine.require_finished(routine='populating')
    def do_validate(self):
        """
        Validates the overall `obj:Options` instance (after the children
        `obj:Option`(s) are fully populated) based on the user provided
        `validate` configuration.

        NOTE:
        ----
        In this case, the validation of the children `obj:Option`(s) is different
        than the validation that runs when values are set on the children
        `obj:Option`(s).  In this case, the validation of the children
        `obj:Option`(s) includes the parent `obj:Options` instance,
        since it has been fully populated at this point.

        NOTE:
        ----
        The provided `validate` configuration value must be a callable that
        takes the `obj:Options` as it's first and only argument.  To indicate
        that the `obj:Options` are invalid, one of 3 things can be done:

        (1) Raise an instance of `obj:OptionInvalidError` to indicate that a
            single option in the `obj:Options` is invalid.

            Example:
            -------
            def validate(options):
                if options.foo > options.bar:
                    raise OptionInvalidError("`foo` is too large.")

        (2) Raise an instance of `obj:OptionsInvalidError` to indicate that the
            options as a whole are invalid.

            Example:
            -------
            def validate(options):
                if options.foo > options.bar:
                    raise OptionsInvalidError("`foo` must be less than or
                        equal to `bar`.")

        (3) Call the `.raise_invalid()` method on the passed in `obj:Options`
            instance.

            Example:
            -------
            def validate(options):
                if options.foo > options.bar:
                    options.raise_invalid("`foo` must be less than or equal to
                        `bar`.")

        (4) Return a string error message.

            Example:
            -------
            def validate(options):
                if options.foo > options.bar:
                    return "`foo` must be less than or equal to `bar`."

        If the `obj:Options` are deemed valid, `None` must be returned.  If the
        returned value is not `None` and the validate method does not comform
        to the (4) protocols above, an exception will be raised.
        """
        configuration = self.configurations['validate']
        if configuration.value is not None:
            logger.debug("Validating overall options.")
            try:
                result = configuration.value(self)
            except Exception as e:
                # This is very problematic, because we can't tell the difference
                # between actual errors and errors that were intentionally raised.
                # We should fix this...
                if isinstance(e, (OptionsInvalidError, OptionInvalidError)):
                    six.reraise(*sys.exc_info())
                else:
                    if settings.DEBUG:
                        six.reraise(*sys.exc_info())
                    configuration.raise_invalid(
                        message=(
                            "If raising an exception to indicate that the "
                            "options are invalid, the exception must be an "
                            "instance of OptionsInvalidError or "
                            "OptionInvalidError.\nIt is recommended to use the "
                            "`raise_invalid` method on the options instance or "
                            "on the specific option."
                        )
                    )
            else:
                if result is not None:
                    if not isinstance(result, six.string_types):
                        configuration.raise_invalid(
                            message=(
                                "The option validate method must return a "
                                "string error message, raise an instance of "
                                "OptionInvalidError or raise an instance of "
                                "OptionsInvalidError in the case that the value "
                                "or values are invalid.  If the value is valid, "
                                "it must return None."
                            )
                        )
                    self.raise_invalid(message=result)

    @Routine.require_finished(routine='populating')
    def do_post_process(self, children=None):
        """
        Performs the post-process routine for the overall `obj:Options` instance
        (after the children `obj:Option`(s) are fully populated) based on the
        user provided `post_process` configuration.  Optionally post-processes
        the provided children `obj:Option`(s) with the populated `obj:Options`.

        NOTE:
        ----
        In this case, the post-processing of the children `obj:Option`(s) is
        different than the post-processing that runs when values are set on the
        children `obj:Option`(s).  In this case, the post-processing of the
        children `obj:Option`(s) includes the parent `obj:Options` instance,
        since it has been fully populated at this point.

        NOTE:
        ----
        The `post_process` method provided in the `obj:Options` configuration
        must be a callable that takes the `obj:Options` instance as it's first
        and only argument.

        The `post_process_with_options` methods of the children `obj:Option`(s)
        must be callables that take the `obj:Option` value as their first
        argument, the `obj:Option` instance as their second argument and the
        populated `obj:Options` instance as their third argument.
        """
        if self.post_process is not None:
            logger.debug("Post processing options")
            self.post_process(self)

    @Routine.require_finished(routine='populating')
    def local_override(self, func):
        """
        Decorator for functions that allows the global options to be temporarily
        overridden while inside the context of the decorated method.  The
        decorated method can be provided additional keyword arguments to specify
        the values of the options to be overridden.

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

            # Store current options before the local override in memory, so they
            # can be used after the function returns to reset the `obj:Options`
            # instance.
            current_options = deepcopy(self.__dict__)

            # Apply overrides and allow the method to run with the overrides
            # applied.
            self.override(local_options)
            result = func(*args, **kwargs)

            # Wipe out the locally scoped overrides and reset the state back to
            # what it was before the method was called.
            self.populate(current_options)
            return result

        return inner

    def validate_configuration(self, *args, **kwargs):
        pass


options = Options()
