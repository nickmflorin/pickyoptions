from pickyoptions.core.exceptions import (
    PickyOptionsError,
    DoesNotExistError,
    ValueNotSetError,
    ValueLockedError,
    ValueTypeError,
    ValueInvalidError,
    ValueRequiredError
)


class ConfigurationError(PickyOptionsError):
    """
    Base class for exceptions that are raised during configuration of the
    options or option.
    """
    identifier = "Configuration Error"


class NotConfiguredError(ConfigurationError):
    default_message = "The configuration has not been configured."


class ConfiguringError(ConfigurationError):
    default_message = "The configuration is already configuring."


class ConfigurationDoesNotExist(DoesNotExistError, ConfigurationError):
    """
    NOTE:
    ----
    This exception has to extend AttributeError because it is raised in the
    __getattr__ method, and we want that error to trigger __hasattr__ to return
    False.
    """
    default_message = "Configuration for `{field}` does not exist."


class ConfigurationNotConfiguredError(NotConfiguredError, ConfigurationError):
    default_message = "The configuration for `{field}` has not been configured."


class ConfigurationConfiguringError(ConfiguringError):
    default_message = (
        "The configuration for field `{field}` is already configuring.")


class ConfigurationNotSetError(ValueNotSetError, ConfigurationError):
    default_message = (
        "The configuration for field `{field}` has not been set on the "
        "{instance} instance."
    )


class ConfigurationLockedError(ValueLockedError, ConfiguringError):
    default_message = (
        "The configuration for `{field}` has already been configured and "
        "cannot be reconfigured."
    )


class ConfigurationInvalidError(ValueInvalidError, ConfigurationError):
    """
    Raised when a provided configuration value is invalid.
    """
    identifier = "Invalid Configuration Error"
    default_message = "The configuration `{field}` is invalid."


class ConfigurationRequiredError(ValueRequiredError, ConfigurationError):
    default_message = (
        "The configuration `{field}` is required but was not provided.")


class ConfigurationTypeError(ValueTypeError, ConfigurationInvalidError):
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
