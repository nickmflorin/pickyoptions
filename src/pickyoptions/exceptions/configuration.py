from .base import PickyOptionsError, ObjectTypeError


class ConfigurationError(PickyOptionsError):
    """
    Base class for exceptions that are raised during configuration of the options or option.
    """
    identifier = "Configuration Error"


class NotConfiguredError(ConfigurationError):
    pass


class ConfigurationDoesNotExist(ConfigurationError):
    default_message = "Configuration for `{field}` does not exist."


class ConfigurationCannotReconfigureError(ConfigurationError):
    default_message = (
        "The configuration for `{field}` has already been configured and cannot be reconfigured.")


class ConfigurationInvalidError(ConfigurationError):
    """
    Raised when a provided configuration value is invalid.
    """
    identifier = "Invalid Configuration Error"
    default_message = "The configuration `{field}` is invalid."


class ConfigurationRequiredError(ConfigurationError):
    default_message = "The configuration `{field}` is required but was not provided."


class ConfigurationTypeError(ObjectTypeError, ConfigurationInvalidError):
    @property
    def default_message(self):
        if len(self.types) != 0:
            if getattr(self, 'field', None) is not None:
                return "The configuration field `{field}` must be of type {types}."
            return "The configuration must be of type {types}."
        if getattr(self, 'field', None) is not None:
            return "The configuration `{field}` is not of the correct type."
        return "The configuration is of invalid type."
