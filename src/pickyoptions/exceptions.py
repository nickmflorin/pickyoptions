from pickyoptions.lib.utils import ensure_iterable


class PickyOptionsError(Exception):
    """
    Base class for all pickyoptions exceptions.
    """
    default_message = "There was an error."

    def __init__(self, *args, **kwargs):
        super(PickyOptionsError, self).__init__()
        try:
            self._message = args[0] if len(args) != 0 else kwargs.pop('message',
                getattr(self, 'default_message'))
        except AttributeError:
            raise AttributeError(
                "Must provide the exception message or set a default on the class."
            )

    @property
    def arguments(self):
        return ()

    def _inject_message_parameters(self, message):
        injection = {}
        for k in self.arguments:
            if "{%s}" % k in message:
                injection[k] = getattr(self, k)
        return message.format(**injection)

    @property
    def bare_message(self):
        return self._message or self.default_message

    @property
    def message(self):
        bare_message = self._inject_message_parameters(self.bare_message)
        if hasattr(self, "identifier"):
            return "%s: %s" % (self.identifier, bare_message)
        return bare_message

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.message


class PickyOptionsUsageError(PickyOptionsError):
    """
    Base class for exceptions that are raised due to package external users, not internal
    configuration errors.
    """
    pass


class PickyOptionsConfigurationError(PickyOptionsError):
    """
    Base class for exceptions that are raised during configuration of the options.
    """
    pass


class FieldParameterizedError(PickyOptionsError):
    """
    Abstract base class for exceptions that include a parameter argument.
    """
    def __init__(self, *args, **kwargs):
        self._field = kwargs.pop('field', None)
        super(FieldParameterizedError, self).__init__(*args, **kwargs)

    @property
    def arguments(self):
        arguments = super(FieldParameterizedError, self).arguments
        return arguments + ('field', )

    @property
    def field(self):
        return self._field

    @property
    def bare_message(self):
        if self.field is None:
            return super(FieldParameterizedError, self).bare_message
        elif self._message is not None:
            return "{field} - %s" % self._message
        return "{field}"


class ValueParameterizedError(FieldParameterizedError):
    """
    Abstract base class for exceptions that include a value argument.
    """
    def __init__(self, *args, **kwargs):
        self._value = kwargs.pop("value", None)
        super(ValueParameterizedError, self).__init__(*args, **kwargs)

    @property
    def arguments(self):
        arguments = super(ValueParameterizedError, self).arguments
        return arguments + ('value', )

    @property
    def value(self):
        return self._value

    @property
    def bare_message(self):
        if self.value is None:
            return super(ValueParameterizedError, self).bare_message
        elif self.field is None:
            if self._message is not None:
                return "{value} - %s" % self._message
            return "{value}"
        else:
            if self._message is not None:
                return "{field} = {value} - %s" % self._message
            return "{field} = {value}"


class InstanceOfError(ValueParameterizedError):
    """
    Raised when an option is not of the right type.
    """
    def __init__(self, param=None, types=None):
        types = ensure_iterable(types)
        super(InstanceOfError, self).__init__(
            param=param,
            message="Must be an instance of %s." % types if types else None
        )


class OptionError(FieldParameterizedError, PickyOptionsUsageError):
    """
    Abstract base class for all exceptions that are raised in reference to a specific
    configured option.
    """
    pass


class OptionConfigurationError(FieldParameterizedError, PickyOptionsConfigurationError):
    """
    Abstract base class for all exceptions that are raised in reference to the configuration
    of a specific option.
    """
    pass


class OptionUnrecognizedError(OptionError):
    """
    Raised when an option is provided but not recognized.
    """
    identifier = "Unrecognized Option"
    default_message = "The option {field} not a recognized option."


class OptionInvalidError(ValueParameterizedError, OptionError):
    """
    Raised when an option is invalid.
    """
    default_message = "The option {field} is invalid."
    identifier = "Invalid Option"


class OptionInstanceOfError(InstanceOfError, OptionInvalidError):
    pass


class OptionRequiredError(OptionInvalidError):
    """
    Raised when an option is required but not specified.
    """
    default_message = "The option {field} is required."


class OptionConfigurationInstanceOfError(InstanceOfError, OptionConfigurationError):
    pass
