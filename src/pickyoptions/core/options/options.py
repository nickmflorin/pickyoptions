from copy import deepcopy
import functools
import logging
import six
import sys

from pickyoptions import settings

from pickyoptions.core.configuration import (
    Configuration, Configurations, ConfigurationsConfigurable)
from pickyoptions.core.configuration.configuration_lib import (
    CallableConfiguration)
from pickyoptions.core.family import Parent
from pickyoptions.core.routine import Routine
from pickyoptions.core.routine.routine import (
    require_not_in_progress, require_finished)

from .constants import OptionsState
from .exceptions import (
    OptionsInvalidError, OptionsNotConfiguredError, OptionsConfiguringError,
    OptionDoesNotExist, OptionInvalidError)
from .option import Option


logger = logging.getLogger(settings.PACKAGE_NAME)


class OptionsRoutine(Routine):
    @require_not_in_progress
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
    @require_finished
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


class Options(ConfigurationsConfigurable, Parent):
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
    ___abstract__ = False

    # SimpleConfigurable Implementation Properties
    not_configured_error = OptionsNotConfiguredError
    configuring_error = OptionsConfiguringError

    # Parent Implementation Properties
    child_cls = Option
    child_identifier = "field"
    does_not_exist_error = OptionDoesNotExist

    # TODO: We should consider moving this inside the instance, because it might
    # be causing code to be run unnecessarily on import.
    configurations = Configurations(
        CallableConfiguration(
            'post_process',
            num_arguments=1,
            error_message=(
                "Must be a callable that takes the options instance as "
                "it's first and only argument."
            )
        ),
        CallableConfiguration(
            'validate',
            num_arguments=1,
            error_message=(
                "Must be a callable that takes the options instance as "
                "it's first and only argument."
            )
        ),
        Configuration('strict', default=False, types=(bool, )),
        validation_error=OptionsInvalidError,
    )

    def __init__(self, *args, **kwargs):
        self._state = OptionsState.NOT_INITIALIZED
        Parent.__init__(
            self,
            children=list(args),
            child_value=lambda child: child.value
        )
        ConfigurationsConfigurable.__init__(self, **kwargs)
        self.create_routine(
            id="populating",
            cls=OptionsRoutine,
            post_routine=self.post_populate
        )
        self.create_routine(
            id="overriding",
            cls=OptionsRoutine,
            post_routine=self.post_override
        )
        self.create_routine(
            id="restoring",
            cls=OptionsRoutine,
            post_routine=self.post_restore
        )

    def post_init(self, *args, **kwargs):
        # TODO: Now that post_init is slightly different, does the not poulated
        # state still make sense here?  Should we have both a post init and
        # a lazy post init method?  YES
        self._state = OptionsState.NOT_POPULATED
        super(Options, self).post_init(*args, **kwargs)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(
            cls, **self.configurations.explicitly_set_configuration_values)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            object.__setattr__(result, k, deepcopy(v, memo))
        return result

    def __call__(self, *args, **kwargs):
        self.populate(*args, **kwargs)

    def __repr__(self):
        if self.initialized:
            if self.populated:
                return "<{cls_name} state={state} {params}>".format(
                    cls_name=self.__class__.__name__,
                    state=self.state,
                    params=", ".join([
                        "{k}={v}".format(k=k, v=v)
                        for k, v in self.zipped
                    ])
                )
            return "<{cls_name} state={state} [{options}]>".format(
                cls_name=self.__class__.__name__,
                state=self.state,
                options=", ".join([option.field for option in self.children])
            )
        return "<{cls_name} state={state}>".format(
            state=self.state,
            cls_name=self.__class__.__name__
        )

    def __getattr__(self, k):
        if self.configurations.has_child(k):
            self.assert_configured()
            configuration = getattr(self.configurations, k)
            return configuration.value

        # We have to assume that the value is referring to an `obj:Option`.
        option_value = super(Options, self).__getattr__(k)
        if not self.routines.populating.finished:
            self.raise_not_populated()
        return option_value

    def __setattr__(self, k, v):
        if not self.initialized or k.startswith('_'):
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

    @property
    def state(self):
        return self._state

    @property
    def populated(self):
        if self.routines.populating.did_run:
            assert self.state != OptionsState.NOT_POPULATED
        return self.routines.populating.did_run

    @property
    def overridden(self):
        if self.routines.populating.did_run:
            assert self.state != OptionsState.POPULATED_NOT_OVERRIDDEN
        return self.routines.overriding.did_run

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
        self.configurations.validate()

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

    # @with_routine(id="populating")
    def populate(self, *args, **kwargs):
        """
        Populates the configured `obj:Options` instance with values for each
        defined `obj:Option`.
        """
        self.reset()
        data = dict(*args, **kwargs)

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            self.raise_if_child_missing(k)

        with self.routines.populating as routine:
            for option in self.options:
                option.assert_configured()
                if option.field in data:
                    option.populate(data[option.field])
                    # Keep track of the options that were explicitly populated so
                    # they can be used to reset the `obj:Options` to it's
                    # previously populated state at a later point in time.
                    routine.register(option)
                else:
                    option.set_default()
                    # If the option wasn't explicitly populated we don't store it
                    # in the routine history because we only need the explicitly
                    # populated options to revert state.
                    routine.register(option, history=False)

    def post_populate(self):
        assert self.state == OptionsState.NOT_POPULATED
        self._state = OptionsState.POPULATED_NOT_OVERRIDDEN

    def override(self, *args, **kwargs):
        """
        Overrides the configured `obj:Options` instance with values for each
        defined `obj:Option`.
        """
        data = dict(*args, **kwargs)

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            self.raise_if_child_missing(k)

        with self.routines.overriding as routine:
            for k, v in data.items():
                option = self.get_child(k)
                option.override(v)
                # Add the `obj:Option` to the queue of `obj:Option`(s) that were
                # populated in a given routine, so we can track which options
                # need to be post validated and post processed with the most up
                # to date `obj:Options` when the routine finishes.
                routine.register(option, history=False)
            # Keep track of the options that were overridden AT EACH overriding
            # routine, so the state of the `obj:Options` can be reverted back to
            # a previous override or not overrides at all.
            routine.save()

    def post_override(self):
        assert self.state in (
            OptionsState.POPULATED_NOT_OVERRIDDEN,
            OptionsState.POPULATED_OVERRIDDEN
        )
        self._state = OptionsState.POPULATED_OVERRIDDEN
        self.do_validate()
        self.do_post_process()

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

    @require_finished(id='populating')
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
        # Down the line, it might be important to do so.
        self.routines.restoring.reset()

        # TODO: Should we maybe just check the number of options in the override
        # queue?
        if not self.routines.overriding.finished:
            logger.debug(
                "Not restoring %s because the instance is not overridden."
                % self.__class__.__name__)
            return

        with self.routines.restoring as routine:
            # Restore the options that were at any point overridden.
            for option in self.overridden_options:
                option.restore()
                # These are currently not necessary to do, but may in the future.
                routine.add_to_queue(option)
                routine.store(option)

        self.routines.overriding.clear_history()

    def post_restore(self):
        self._state = OptionsState.POPULATED_NOT_OVERRIDDEN

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
        self._state = OptionsState.NOT_POPULATED
        # If initialized, all of the routines we want to reset will be present.
        # Otherwise, it will just be the configuration routine - which we don't
        # want to reset.  Do we have to worry about the defaulting routine?
        assert 'defaulting' not in [routine.id for routine in self.routines]
        if self.initialized:
            self.routines.subsection(
                ['populating', 'overriding', 'restoring']).reset()
        for option in self.options:
            option.reset()

    @require_finished(id='populating')
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

    @require_finished(id='populating')
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

    @require_finished(id='populating')
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


# TODO: This is causing code to run on import, which isn't ideal.  What we should
# do is make the configuration validation conditionally lazy - so it is performed
# when the options are first used, not when they are first instantiated.
# >>> optinos = Options(lazy=True)
options = None
