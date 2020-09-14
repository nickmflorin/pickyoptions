from pickyoptions.core.exceptions import PickyOptionsError, DoesNotExistError
from pickyoptions.core.value.exceptions import (
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
    default_injection = {"name": "value"}


class OptionNotConfiguredError(NotConfiguredError, OptionError):
    identifier = "Option Not Configured"
    default_message = "The option {name} is not yet configured."


class OptionConfiguringError(ConfiguringError, OptionError):
    identifier = "Option Configuring Error"
    default_message = "The option {name} is already configuring."


class OptionConfigurationError(ConfigurationError, OptionError):
    identifier = "Option Configuration Error"
    default_message = "The option {name} is already configuring."


class OptionLockedError(ValueLockedError, OptionError):
    default_message = (
        "The option {name} is locked and thus cannot be "
        "changed after it's initial population."
    )


class OptionNotSetError(ValueNotSetError, OptionError):
    """
    Raised when trying to access values or functionality on the `obj:Option`
    that require that the `obj:Option` was set.
    """
    identifier = "Option Not Set"
    default_message = "The option {name} has not been set yet."


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
    default_message = "There is no configured option {name}."


class OptionInvalidError(ValueInvalidError, OptionError):
    """
    Base class for all exceptions that are raised when a an option value is
    invalid.
    """
    default_message = "The option {name} is invalid."
    identifier = "Invalid Option"


class OptionRequiredError(ValueRequiredError, OptionError):
    """
    Raised when an option value is required but not specified.
    """
    identifier = "Required Option"
    default_message = "The option {name} is required, but was not provided."


class OptionTypeError(ValueTypeError, OptionInvalidError):
    """
    Raised when an option value is required to be of a specific type but is not
    of that type.
    """
    # Required to be specified because of the inheritance pattern.
    identifier = "Invalid Option"

    @property
    def default_message(self):
        types = getattr(self, 'types', None)
        if types:
            return "The option {name} must be of type {types}."
        return "The option {name} is not of the correct type."
