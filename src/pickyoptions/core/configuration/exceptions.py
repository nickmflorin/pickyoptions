from pickyoptions.core.exceptions import PickyOptionsError, ObjectTypeError
from pickyoptions.core.configurable.exceptions import (
    NotConfiguredError, CannotReconfigureError, ConfiguringError)


class ConfigurationError(PickyOptionsError):
    """
    Base class for exceptions that are raised during configuration of the
    options or option.
    """
    identifier = "Configuration Error"


class ConfigurationNotConfiguredError(NotConfiguredError, ConfigurationError):
    default_message = "The configuration for `{field}` has not been configured."


class ConfigurationCannotReconfigureError(CannotReconfigureError,
        ConfigurationError):
    default_message = (
        "The configuration for `{field}` has already been configured and "
        "cannot be reconfigured."
    )


class ConfigurationConfiguringError(ConfiguringError, ConfigurationError):
    default_message = (
        "The configuration for field `{field}` is already configuring.")


class ConfigurationNotSetError(ConfigurationError):
    default_message = "The configuration for field `{field}` has not been set."


class ConfigurationInvalidError(ConfigurationError):
    """
    Raised when a provided configuration value is invalid.
    """
    identifier = "Invalid Configuration Error"
    default_message = "The configuration `{field}` is invalid."


class ConfigurationRequiredError(ConfigurationError):
    default_message = (
        "The configuration `{field}` is required but was not provided.")


class ConfigurationTypeError(ObjectTypeError, ConfigurationInvalidError):
    @property
    def default_message(self):
        if len(self.types) != 0:
            if getattr(self, 'field', None) is not None:
                return (
                    "The configuration field `{field}` must be of type {types}.")
            return "The configuration must be of type {types}."
        if getattr(self, 'field', None) is not None:
            return "The configuration `{field}` is not of the correct type."
        return "The configuration is of invalid type."
