from pickyoptions.core.exceptions import (
    PickyOptionsError,
    DoesNotExistError,
    ValueNotSetError,
    ValueLockedError,
    ValueTypeError,
    ValueInvalidError,
    ValueRequiredError,
    ValueNullNotAllowedError,
    ValueSetError,
    ValueNotRequiredError
)


class ParentError(PickyOptionsError):
    identifier = "Parent Error"


class ChildError(PickyOptionsError):
    identifier = "Child Error"


class ChildInvalidError(ValueInvalidError, ChildError):
    identifier = "Invalid Child"
    default_message = "The child {name} is invalid."


class ChildTypeError(ValueTypeError, ChildInvalidError):
    @property
    def default_message(self):
        types = getattr(self, 'types', None)
        if types:
            if len(types) != 0:
                return "The child `{name}` must be of type {types}."
            return "The child `{name}` is not of the correct type."
        return "The child `{name}` is of invalid type."


# TODO: Should this be a parent error instead?
class ChildDoesNotExistError(DoesNotExistError, ChildError):
    default_message = "The child `{name}` does not exist."


class ConfigurationError(PickyOptionsError):
    """
    Base class for exceptions that are raised during configuration of the
    options or option.
    """
    identifier = "Configuration Error"
    default_injection = {"name": "value"}
    default_message = "There was an error configuring {name}."


class NotConfiguredError(ConfigurationError):
    """
    General error to indicate that a specific instance requires configuration
    but has not yet been configured.
    """
    default_message = "The configuration {name} has not been configured."


class ConfiguringError(ConfigurationError):
    """
    General error to indicate that a specific instance is still in the process
    of configuring.
    """
    default_message = "The configuration {name} is already configuring."


class ConfigurationDoesNotExistError(ChildDoesNotExistError, ConfigurationError):
    """
    Raised when a specific `obj:Configuration` is accessed in the
    `obj:Configurations` but the `obj:Configuration` does not exist in the
    `obj:Configurations`.

    NOTE:
    ----
    This exception has to extend AttributeError because it is raised in the
    __getattr__ method, and we want that error to trigger __hasattr__ to return
    False in the case that the `obj:Configuration` does not exist.
    """
    default_message = "The configuration {name} does not exist."


class ConfigurationNotSetError(ValueNotSetError, ConfigurationError):
    """
    Raised when the value for a specific `obj:Configuration` is required to
    be set but it has not been set yet.
    """
    default_message = (
        "The configuration {name} has not been set on on the instance yet."
    )


class ConfigurationSetError(ValueSetError, ConfigurationError):
    """
    Raised when the value for a specific `obj:Configuration` has already been
    set but it is not expected to be set.
    """
    default_message = (
        "The configuration {name} has already been set."
    )


class ConfigurationLockedError(ValueLockedError, ConfiguringError):
    """
    Raised when the `obj:Configuration` has already been configured and
    cannot be reconfigured.
    """
    default_message = (
        "The configuration {name} has already been configured and "
        "cannot be reconfigured."
    )


class ConfigurationInvalidError(ChildInvalidError, ConfigurationError):
    """
    Raised when a provided configuration value is invalid.
    """
    identifier = "Invalid Configuration Error"
    default_message = "The configuration {name} is invalid."


class ConfigurationNullNotAllowedError(
        ValueNullNotAllowedError, ConfigurationInvalidError):
    default_message = "The configuration {name} is not allowed to be null."


class ConfigurationRequiredError(ValueRequiredError, ConfigurationError):
    """
    Raised when a `obj:Configuration` is required but no value is provided
    to configure it with.
    """
    default_message = (
        "The configuration {name} is required but was not provided."
    )


class ConfigurationNotRequiredError(ValueNotRequiredError, ConfigurationError):
    """
    Raised when a `obj:Configuration` is not required but we are expecting it
    to be required.
    """
    default_message = (
        "The configuration {name} is not required."
    )


class ConfigurationTypeError(ChildTypeError, ConfigurationInvalidError):
    """
    Raised when the value supplied to the `obj:Configuration` is of the
    incorrect type.
    """
    @property
    def default_message(self):
        types = getattr(self, 'types', None)
        if types:
            if len(types) != 0:
                return "The configuration {name} must be of type {types}."
            return "The configuration {name} is not of the correct type."
        return "The configuration {name} is of invalid type."


class ConfigurationValidationError(ConfigurationError):
    identifier = "Configuration Validation Error"
    default_message = "The value supplied for configuration {name} is invalid."
