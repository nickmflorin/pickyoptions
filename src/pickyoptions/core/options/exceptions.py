from pickyoptions.core.exceptions import (
    PickyOptionsError,
    DoesNotExistError,
    ValueNotSetError,
    ValueLockedError,
    ValueRequiredError,
    ValueNullNotAllowedError,
    DoesNotExistError
)
from pickyoptions.core.configuration.exceptions import (
    NotConfiguredError, ConfiguringError, ConfigurationError,
    ChildError, ChildInvalidError, ChildTypeError, ConfigurationValidationError)


class OptionsError(PickyOptionsError):
    """
    Abstract base class for all exceptions that are raised in reference to a
    specific set of of `obj:Options`.
    """
    pass


class OptionsNotConfiguredError(NotConfiguredError, OptionsError):
    default_message = "The options are not yet configured."


class OptionsConfiguringError(ConfiguringError, OptionsError):
    identifier = "Options Configuring Error"
    default_message = "The options are already configuring."


class OptionsInvalidError(OptionsError):
    """
    Raised when the `obj:Options` are invalid as a whole.
    """
    identifier = "Invalid Options"
    default_message = "The options are invalid."


class OptionsNotPopulatedError(OptionsError):
    default_message = "The options are not yet populated."


class OptionsPopulatedError(OptionsError):
    default_message = "The options are already populated."


class OptionsNotPopulatedPopulatingError(OptionsError):
    default_message = (
        "The options are not yet populated and are not in the process "
        "of populating."
    )


class OptionError(ChildError):
    """
    Abstract base class for all exceptions that are raised in reference to a
    specific `obj:Option`.
    """
    identifier = "Option Error"
    default_injection = {"name": "value"}


class OptionNotPopulatedError(OptionError):
    default_message = "The option {name} is not yet populated."


class OptionPopulatedError(OptionError):
    default_message = "The option {name} is already populated."


class OptionNotPopulatedPopulatingError(OptionError):
    default_message = (
        "The option {name} is not yet populated and is not in the process "
        "of populating."
    )


class OptionNotConfiguredError(NotConfiguredError, OptionError):
    identifier = "Option Not Configured"
    default_message = "The option {name} is not yet configured."


class OptionConfiguringError(ConfiguringError, OptionError):
    identifier = "Option Configuring Error"
    default_message = "The option {name} is already configuring."


class OptionConfigurationError(ConfigurationError, OptionError):
    identifier = "Option Configuration Error"
    default_message = "There was an error configuring option {name}."


class OptionConfigurationValidationError(
        ConfigurationValidationError, OptionError):
    identifier = "Option Configuration Validation Error"
    default_message = (
        "The value supplied to the option configuration {name} is invalid."
    )


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


class OptionDoesNotExistError(DoesNotExistError, OptionError):
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


class OptionInvalidError(ChildInvalidError, OptionError):
    """
    Base class for all exceptions that are raised when a an option value is
    invalid.
    """
    default_message = "The option {name} is invalid."
    identifier = "Invalid Option"


class OptionNullNotAllowedError(ValueNullNotAllowedError, OptionInvalidError):
    default_message = "The option {name} is not allowed to be null."


class OptionRequiredError(ValueRequiredError, OptionError):
    """
    Raised when an option value is required but not specified.
    """
    identifier = "Required Option"
    default_message = "The option {name} is required, but was not provided."


class OptionTypeError(ChildTypeError, OptionInvalidError):
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
