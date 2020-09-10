from pickyoptions.exceptions import PickyOptionsError, ObjectTypeError
from pickyoptions.configuration.exceptions import NotConfiguredError


class OptionError(PickyOptionsError):
    """
    Abstract base class for all exceptions that are raised in reference to a specific
    `obj:Option`.
    """
    pass


class OptionNotConfiguredError(NotConfiguredError, OptionError):
    identifier = "Option Not Configured"
    default_message = "The option for field `{field}` is not yet configured."


class OptionNotSetError(OptionError):
    """
    Raised when trying to access values or functionality on the `obj:Option` that require
    that the `obj:Option` was set.
    """
    identifier = "Option Not Set"
    default_message = "The option for field `{field}` has not been set yet."


class OptionUnrecognizedError(OptionError):
    """
    Raised when a provided option is not recognized - this means that it was never configured
    as a part of the `obj:Options`.
    """
    identifier = "Unrecognized Option"
    default_message = "There is no configured option for field `{field}`."


class OptionInvalidError(OptionError):
    """
    Base class for all exceptions that are raised when a an option value is invalid.
    """
    default_message = "The option for field `{field}` is invalid."
    identifier = "Invalid Option"


class OptionRequiredError(OptionError):
    """
    Raised when an option value is required but not specified.
    """
    identifier = "Required Option"
    default_message = "The option for field `{field}` is required, but was not provided."


class OptionTypeError(ObjectTypeError, OptionInvalidError):
    """
    Raised when an option value is required to be of a specific type but is not of that type.
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
