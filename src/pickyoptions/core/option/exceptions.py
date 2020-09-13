from pickyoptions.core.exceptions import (
    PickyOptionsError,
    DoesNotExistError,
    ValueNotSetError,
    ValueLockedError,
    ValueTypeError,
    ValueInvalidError,
    ValueRequiredError
)
from pickyoptions.core.configuration.exceptions import (
    NotConfiguredError, ConfiguringError, ConfigurationError)


class OptionError(PickyOptionsError):
    """
    Abstract base class for all exceptions that are raised in reference to a
    specific `obj:Option`.
    """
    identifier = "Option Error"


class OptionNotConfiguredError(NotConfiguredError, OptionError):
    identifier = "Option Not Configured"
    default_message = "The option for field `{field}` is not yet configured."


class OptionConfiguringError(ConfiguringError, OptionError):
    identifier = "Option Configuring Error"
    default_message = "The option for field `{field}` is already configuring."


class OptionConfigurationError(ConfigurationError, OptionError):
    identifier = "Option Configuration Error"
    default_message = "The option for field `{field}` is already configuring."


class OptionLockedError(ValueLockedError, OptionError):
    default_message = (
        "The option for field `{field}` is locked and thus cannot be "
        "changed after it's initial population."
    )


class OptionNotSetError(ValueNotSetError, OptionError):
    """
    Raised when trying to access values or functionality on the `obj:Option`
    that require that the `obj:Option` was set.
    """
    identifier = "Option Not Set"
    default_message = "The option for field `{field}` has not been set yet."


class OptionDoesNotExist(DoesNotExistError, OptionError):
    """
    Raised when a provided option is not recognized - this means that it was
    never configured as a part of the `obj:Options`.

    NOTE:
    ----
    This exception has to extend AttributeError because it is raised in the
    __getattr__ method, and we want that error to trigger __hasattr__ to return
    False.
    """
    identifier = "Unrecognized Option"
    default_message = "There is no configured option for field `{field}`."


class OptionInvalidError(ValueInvalidError, OptionError):
    """
    Base class for all exceptions that are raised when a an option value is
    invalid.
    """
    default_message = "The option for field `{field}` is invalid."
    identifier = "Invalid Option"


class OptionRequiredError(ValueRequiredError, OptionError):
    """
    Raised when an option value is required but not specified.
    """
    identifier = "Required Option"
    default_message = (
        "The option for field `{field}` is required, but was not provided.")


class OptionTypeError(ValueTypeError, OptionInvalidError):
    """
    Raised when an option value is required to be of a specific type but is not
    of that type.
    """
    @property
    def default_message(self):
        if len(self.types) != 0:
            if getattr(self, 'field', None) is not None:
                return "The option for field `{field}` must be of type {types}."
            return "The option must be of type {types}."
        if getattr(self, 'field', None) is not None:
            return "The option for field `{field}` is not of the correct type."
        return "The option is of invalid type."