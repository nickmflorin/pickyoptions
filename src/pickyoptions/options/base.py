from copy import deepcopy
import contextlib
import functools
import logging
import six
import sys

from pickyoptions.exceptions import PickyOptionsError, PickyOptionsAttributeError
from pickyoptions.env import DEBUG

from pickyoptions.configuration.base import (
    ConfigurableModel, configurable_property, configurable_property_setter)
from pickyoptions.option.exceptions import (
    OptionUnrecognizedError, OptionInvalidError, OptionRequiredError)

from .configuration import (
    PostProcessorConfiguration, ValidateConfiguration, OptionsConfiguration)
from .exceptions import OptionsConfigurationError, OptionsInvalidError, OptionsNotPopulatedError


logger = logging.getLogger("pickyoptions")


def requires_population(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if not instance.populated:
            if DEBUG:
                raise PickyOptionsError(
                    "Operation %s not permitted if the options are not "
                    "yet populated." % func.__name__,
                )
            raise PickyOptionsError(
                "Operation not permitted if the options are not yet populated."
            )
        return func(instance, *args, **kwargs)
    return inner


class OptionsConfiguration(ConfigurableModel):
    configurations = (
        PostProcessorConfiguration('post_process'),
        ValidateConfiguration('validate'),
        OptionsConfiguration('strict', default=False, types=(bool, )),
    )

    @configurable_property
    def post_process(self):
        pass

    @configurable_property_setter(post_process)
    def post_process(self, value):
        pass

    @configurable_property
    def validate(self):
        pass

    @configurable_property_setter(validate)
    def validate(self, value):
        pass

    @configurable_property
    def strict(self):
        pass

    @configurable_property_setter(strict)
    def strict(self, value):
        pass


class Options(OptionsConfiguration):
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

    or

    >>> from pickyoptions import Options
    >>> options = Options(
    >>>     Option(field="foo", type=(str, int)),
    >>>     Option(field="bar", type=(str, int))
    >>> )

    ~~~ my_package.file

    >>> from pickyoptions import options
    >>> assert options.foo = "fooey"

    or

    ~~~ my_package.file

    >>> from my_package import options
    >>> assert options.foo = "fooey"
    """
    def __init__(self, *args, **kwargs):
        # Keeps track of the options that were set on population so the state of the
        # `obj:Options` instance can be restored after overrides are applied.
        self._populated_options = {}

        # Keeps track of whether or not the `obj:Options` instance has already been populated
        # and whether or not it is actively being populated.
        self._populated = False
        self._populating = False

        # Keeps track of the option values that are overridden after population.
        self._overrides = {}
        self._option_values = {}
        self._options = list(args)

        super(Options, self).__init__(**kwargs)

    def __repr__(self):
        if self.populated:
            return "<{cls_name} {params}>".format(
                cls_name=self.__class__.__name__,
                params=", ".join(["{k}={v}".format(k=k, v=v) for k, v in self.__dict__.items()])
            )
        return "<{cls_name} UNPOPULATED [{options}]>".format(
            cls_name=self.__class__.__name__,
            options=", ".join([option.field for option in self.options])
        )

    def __call__(self, *args, **kwargs):
        self.populate(*args, **kwargs)

    @property
    def __dict__(self):
        data = {}
        for option in self.options:
            # data[option.field] = getattr(self, option.field)
            data[option.field] = self._option_values[option.field]
        return data

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)

        # State Properties
        result._populating = self._populating
        result._populated = self._populated
        result._configuring = self._configuring
        result._configured = self._configured
        result._configurations = self._configurations

        result._populated_options = self._populated_options

        # Configuration Properties
        result._strict = self._strict
        result._options = self._options[:]

        result._data = deepcopy(self._option_values)

        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def __getattr__(self, k):
        # If the options are not yet populated, we only allow the retrieval of a configuration
        # value, not the option values themselves.
        if not self.populated:
            if DEBUG:
                raise PickyOptionsAttributeError(
                    "Operation %s not permitted if the options are not "
                    "yet populated." % self.__getattr__.__name__,
                )
            raise PickyOptionsAttributeError(
                "The attribute %s does not exist in the options configuration and the "
                "options have not been populated yet.  If accessing a specific option, the "
                "options must be populated."
            )
        option = self.option(k)
        try:
            value = self._option_values[option.field]
        except KeyError:
            assert not option.required
            return option.default
        else:
            return option.normalize_option(value)

    def __setattr__(self, k, v):
        if k.startswith('_'):
            super(Options, self).__setattr__(k, v)
        else:
            option = self.option(k)

            # Only validate if we are not actively populating the options, otherwise they will
            # all be validated afterwards.
            if not self.populating:
                option.validate_option(v)

            self._option_values[option.field] = v

            # If all the options have been set, validate the `obj:Options` instance as a whole and
            # perform the post processing routines on the individual options as well.
            if not self.populating:
                self.validate_options()
                option.post_process_option(v, self)

    def __getitem__(self, k):
        return self.__getattr__(k)

    def __setitem__(self, k, v):
        # We have to check if the option exists first when setting the item by key.
        option = self.option(k)
        self.__setattr__(option.field, v)

    def _pre_configure(self):
        self.reset()

    @property
    def populated(self):
        return self._populated

    @property
    def populating(self):
        return self._populating

    def populate(self, *args, **kwargs):
        """
        Populates the configured `obj:Options` instance with values for each defined
        `obj:Option`.
        """
        self.reset()

        with self.populating_context():
            data = dict(*args, **kwargs)
            for option in self.options:
                if option.field not in data:
                    # If the option is required it should not have a default - at least we are
                    # logging a warning that the circumstance is redundant.
                    if option.required:
                        if option.default:
                            logger.warn()
                        else:
                            option.raise_invalid(cls=OptionRequiredError)
                else:
                    # Keep track of the fields that were explicitly set so that they can be
                    # reset to the originals at a later point in time.
                    self._populated_options[option.field] = data[option.field]
                    setattr(self, option.field, data[option.field])

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            if k not in self.option_fields:
                raise OptionUnrecognizedError(k)

    @contextlib.contextmanager
    def populating_context(self):
        self._populating = True
        try:
            yield self
        except Exception:
            six.reraise(*sys.exc_info())
        else:
            self._populating = False
            self._post_population()

    def _post_population(self):
        self._populated = True
        self.validate_options(individual_options=True)
        self.post_process_options(individual_options=True)

    def reset(self):
        # TODO: Maybe we should check if the options are configuring before resetting this?
        self._option_values = {}
        self._populated_options = {}
        self._overrides = {}

    @requires_population
    def override(self, *args, **kwargs):
        """
        Overrides certain option values in the existing `obj:Options` instance with new option
        values.
        """
        data = dict(*args, **kwargs)
        with self.populating_context():
            for k, v in data.items():
                setattr(self, k, v)
                self._overrides[k] = v

    @requires_population
    def restore(self):
        """
        Resets the `obj:Options` instance to it's state immediately after it was last
        populated.  Any overrides since the last population will be removed.
        """
        with self.populating_context():
            for option in self.options:
                if option.field in self._overrides:
                    # The option need not be in the populated options, since the override
                    # could have been applied to a default value.  If the override was defaulted,
                    # it will not be in the populated options and we can restore the default by
                    # setting it to None.
                    setattr(self, option.field, self._populated_options.get(option.field))

    @property
    def options(self):
        # TODO: We have to create a setter for this that will prune the values already provided
        # if the options are changed, or a setter that will clear the option values if this
        # changes.
        return self._options

    @options.setter
    def options(self, value):
        # TODO: We have to validate the configuration once these are set, since they are
        # not being stored as a separate configuration variable.
        self._options = value

    @property
    def option_fields(self):
        """
        Returns the fields associated with the `obj:Option`(s) configured in the `obj:Options`
        instance.
        """
        return [opt.field for opt in self.options]

    def option(self, k):
        """
        Returns the `obj:Option` associated with the provided field.
        """
        if not self.configured:
            raise OptionsNotPopulatedError()
        try:
            return [opt for opt in self.options if opt.field == k][0]
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

    @requires_population
    def validate_options(self, individual_options=False):
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
        # Conditionally validate the individual options, this will happen at the end of the setting
        # options context when options are being populated or overriden in bulk, but will not
        # happen when setting one option at a time - in that case it will happen in the
        # __setattr__ method.
        # TODO: Conglomerate errors together.
        if individual_options:
            for option in self.options:
                # The option wont be in the data if it is allowed to be defaulted, so we need
                # to check that first and raise an exception if it's supposed to be required.
                assert option.field in self._option_values
                option.validate_option(self._option_values[option.field], self)

        # Validate the overall options set if the validator is provided.
        if self.validate is not None:
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

    @requires_population
    def post_process_options(self, individual_options=False):
        """
        Performs the post-processing routines associated with the overall `obj:Options` and
        all of the individual `obj:Option`(s) after the options have been initialized, configured
        or overridden.

        The `post_process` method of the overall `obj:Options` must be a callable that takes the
        `obj:Options` instance as it's only argument.  The individual `obj:Option` `post_process`
        methods must be callables that take the set value as it's first argument and the
        overall `obj:Options` instance as it's second argument.
        """
        # Conditionally post process the individual options, this will happen at the end of the
        # setting options context when options are being populated or overriden in bulk, but will
        # not happen when setting one option at a time - in that case it will happen in the
        # __setattr__ method.
        if individual_options:
            for option in self.options:
                assert option.field in self._option_values
                option.post_process_option(self._option_values[option.field], self)

        if self.post_process is not None:
            self.post_process(self)

    @requires_population
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

    def validate_configuration(self):
        """
        Validates the configuration for configuration variables that depend on one another,
        after they are set.
        """
        pass


options = Options()
