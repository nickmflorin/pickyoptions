from copy import deepcopy
import contextlib
import functools
import logging
import six
import sys

from src.lib.utils import check_num_function_arguments

from ..option.exceptions import OptionUnrecognizedError, OptionInvalidError
from .exceptions import OptionsConfigurationError, OptionsInvalidError


logger = logging.getLogger("pickyoptions")


class Options(object):
    def __init__(self, *args, strict=True, validate=None, post_process=None):
        self._validate = validate
        self._post_process = post_process

        # Keeps track of the options that were set on initialization so the state of the
        # `obj:Options` instance can be restored after overrides.
        self._originally_set_options = {}

        # Keeps track of whether or not options are currently being set or have already been set,
        # which allows for the overall validation and post processing routines to take place once
        # all the options have been set.
        self._settings_options = False
        self._options = list(*args)
        self._strict = strict

        # Validate the configuration of the overall `obj:Options` instance.  The individual
        # `obj:Option` instances will have their configurations validated independently on
        # initialization.
        self._validate_configuration()

    def __call__(self, *args, **kwargs):
        # Set the options provided on initialization and run the post processing routines and
        # validation routines after all of the options have been set.
        with self.settings_options():
            data = dict(*args, **kwargs)
            for opt in self._options:
                if opt.field in data:
                    # Keep track of the fields that were explicitly set so that they can be
                    # reset to the originals at a later point in time.
                    self._originally_set_options[opt.field] = data[opt.field]
                setattr(self, opt.field, data.get(opt.field, opt.default))

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            if k not in self.option_fields:
                raise OptionUnrecognizedError(k)

    def __repr__(self):
        return "<Options {params}>".format(
            params=", ".join(["{k}={v}".format(k=k, v=v) for k, v in self.__dict__.items()])
        )

    @contextlib.contextmanager
    def settings_options(self):
        self._settings_options = True
        try:
            yield self
        finally:
            self._settings_options = False
            self.validate()
            self.post_process()

    @property
    def __dict__(self):
        data = {}
        for option in self._options:
            data[option.field] = getattr(self, option.field)
        return data

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        result._settings_options = self._settings_options
        result._originally_set_options = self._originally_set_options
        result._options = self._options[:]
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def __setattr__(self, k, v):
        if k.startswith('_'):
            super(Options, self).__setattr__(k, v)
        else:
            option = self.option(k)
            option.validate(v, self)
            value_to_set = option.normalize(v, self)

            # If the option is mergable and the current/new value are both `obj:dict` instances,
            # the existing value of the option will be updated with the new value for the option,
            # not replaced.

            # TODO: Should we only do this if the option is defaulted?  We might want to override
            # user specific options.
            if option.mergable:
                current_value = getattr(self, option.field, None)
                if (
                    current_value is not None
                    and isinstance(value_to_set, dict)
                    and isinstance(current_value, dict)
                ):
                    current_value = deepcopy(current_value)
                    current_value.update(value_to_set)
                    value_to_set = deepcopy(current_value)

            super(Options, self).__setattr__(option.field, value_to_set)

            # If all the options have been set, validate the `obj:Options` instance as a whole and
            # perform the post processing routines on the individual options as well.
            if not self._settings_options:
                self.validate()
                if option.post_process:
                    option.post_process(value_to_set, self)

    @property
    def options(self):
        # TODO: We have to create a setter for this that will prune the values already provided
        # if the options are changed, or a setter that will clear the option values if this
        # changes.
        return self._options

    @property
    def option_fields(self):
        return [opt.field for opt in self.options]

    def option(self, k):
        """
        Returns the `obj:Option` associated with the provided field.
        """
        try:
            return [opt for opt in self._options if opt.field == k][0]
        except IndexError:
            raise OptionUnrecognizedError(k)

    def raise_invalid_option(self, field, **kwargs):
        """
        Raises an OptionInvalidError (or an extension) for the `obj:Option` associated with
        the provided field.
        """
        option = self.option(field)
        option.raise_invalid(**kwargs)

    def raise_invalid(self, *args, **kwargs):
        """
        Raises an OptionsInvalidError (or an extension) for the overall `obj:Options`.
        """
        raise OptionsInvalidError(*args, **kwargs)

    def _handle_exception(self, e, level=logging.ERROR):
        if self.strict:
            raise e
        logger.log(level, "%s" % e)

    @classmethod
    def display(self):
        """
        Displays the options to the user.
        """
        sys.stdout.write("\n\n".join(opt.display for opt in self.__options__))

    def validate(self):
        """
        Validates the overall `obj:Options` instance, based on the provided `validate` argument
        on initialization, after the options have been initialized, configured or overidden.

        Unlike the individual `obj:Option` validation routines, this has a chance to perform
        validation after all of the individual `obj:Option`(s) have been set on the `obj:Options`.

        The provided `validate` method must be a callable that takes the `obj:Options` as it's
        first and only argument.  To indicate that the `obj:Options` as a whole are invalid,
        it can either raise `obj:OptionsInvalidError`, `obj:OptionInvalidError`, call the
        `raise_invalid` method on the `obj:Options` or one of the children `obj:Option`(s) or
        it can return a string message.  If the `obj:Options` are valid, it must return `None`.
        """
        if self._validate is not None:
            # In the case that the options are invalid, validation method either returns a
            # string method or raises one of OptionInvalidError or OptionsInvalidError (or an
            # extension of).
            try:
                result = self._validate(self)
            except Exception as e:
                if isinstance(e, (OptionsInvalidError, OptionInvalidError)):
                    six.reraise(*sys.exc_info())
                else:
                    exc = OptionsConfigurationError(
                        field='validate',
                        message=(
                            "If raising an exception to indicate that the options are invalid, "
                            "the exception must be an instance of OptionsInvalidError or "
                            "OptionInvalidError.  It is recommended to use the `raise_invalid` "
                            "method on the options instance or on the specific option."
                        )
                    )
                    self._handle_exception(exc)
            else:
                if result is not None:
                    if not isinstance(result, six.string_types):
                        exc = OptionsConfigurationError(
                            field='validate',
                            message=(
                                "The option validate method must return a string error "
                                "message, raise an instance of OptionInvalidError or raise an "
                                "instance of OptionsInvalidError in the case that the value or "
                                "values are invalid.  If the value is valid, it must return None."
                            )
                        )
                        self._handle_exception(exc)
                    else:
                        self.raise_invalid(message=result)

    def post_process(self):
        """
        Performs the post-processing routines associated with the overall `obj:Options` and
        all of the individual `obj:Option`(s) after the options have been initialized, configured
        or overridden.

        The `post_process` method of the overall `obj:Options` must be a callable that takes the
        `obj:Options` instance as it's only argument.  The individual `obj:Option` `post_process`
        methods must be callables that take the set value as it's first argument and the
        overall `obj:Options` instance as it's second argument.
        """
        if self._post_process is not None:
            self._post_process(self)

        # Post process the individual options that make up the options instance.
        for opt in self.__options__:
            if opt.post_process:
                opt.post_process(getattr(self, opt.field), self)

    def override(self, *args, **kwargs):
        """
        Overrides certain options in the existing `obj:Options` instance with new options.
        """
        with self.settings_options():
            data = dict(*args, **kwargs)
            with self.settings_options():
                for k, v in data.items():
                    setattr(self, k, v)

    def reset(self):
        """
        Resets the `obj:Options` instance to it's state immediately after it was first initialized.
        Any overrides or post-init configurations since that first initialization will be wiped.
        """
        with self.settings_options():
            for opt in self.__options__:
                if opt.field in self._originally_set_options:
                    super(Options, self).__setattr__(
                        opt.field, self._originally_set_options[opt.field])
                else:
                    super(Options, self).__setattr__(opt.field, opt.default)

    def configure(self, *args, **kwargs):
        """
        Configures the `obj:Options` instance by resetting to it's original state before any
        overrides were applied and applying a new set of overrides.
        """
        # Note that this will call the validation and post processing routines in between the
        # reset and override, which is not ideal but there is likely not a way around that.
        self.reset()
        self.override(*args, **kwargs)

    def local_override(self, func):
        """
        Decorator for functions that allows the global options to be temporarily overridden while
        inside the context of the decorated method.  The decorated method can be provided
        additional keyword arguments to specify the values of the options to be overridden.
        """
        @functools.wraps(func)
        def inner(*args, **kwargs):
            local_options = {}
            for k, v in kwargs.items():
                if k in [option.field for option in self.__options__]:
                    local_options[k] = kwargs.pop(k)

            # Store current options before the local override in memory, so they can be used after the
            # function returns to reset the `obj:Options` instance.
            current_options = deepcopy(self.__dict__)

            # Apply overrides and allow the method to run with the overrides applied.
            self.override(local_options)
            result = func(*args, **kwargs)

            # Wipe out the locally scoped overrides and reset the state back to what it was before the
            # method was called.
            self.configure(current_options)
            return result

        return inner

    def _validate_configuration(self):
        """
        Validates the configuration of the `obj:Options` instance.
        """
        if self._validate is not None:
            if (not six.callable(self._validate)
                    or not check_num_function_arguments(self._validate, 1)):
                raise OptionsConfigurationError(
                    param='validate',
                    message=(
                        "Must be a callable that takes the options instance as it's first and "
                        "only argument."
                    )
                )

        if self._post_process is not None:
            if (not six.callable(self._post_processv)
                    or not check_num_function_arguments(self._post_process, 1)):
                raise OptionsConfigurationError(
                    param='post_process',
                    message=(
                        "Must be a callable that takes the options instance as it's first and "
                        "only argument."
                    )
                )


options = Options()
