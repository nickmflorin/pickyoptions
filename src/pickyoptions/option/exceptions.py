from pickyoptions.exceptions import (
    ValueParameterizedError, PickyOptionsUserError, PickyOptionsConfigurationError)
from pickyoptions.lib.utils import ensure_iterable


__all__ = (
    'OptionInvalidError',
    'OptionInstanceOfError',
    'OptionRequiredError',
)


class OptionError(ValueParameterizedError):
    """
    Abstract base class for all exceptions that are raised in reference to a specific
    `obj:Option`.
    """
    pass


class OptionUserError(OptionError, PickyOptionsUserError):
    """
    Abstract base class for all exceptions that are raised in reference to a user provided
    value to an already configured `obj:Option`.
    """
    pass


class OptionConfigurationError(OptionError, PickyOptionsConfigurationError):
    """
    Raised when the configuration provided to an `obj:Option` is invalid.
    """
    identifier = "Option Configuration Error"


class OptionUnrecognizedError(OptionUserError):
    """
    Raised when a user provided option is not recognized - this means that it was never configured
    as a part of the `obj:Options`.
    """
    identifier = "Unrecognized Option"
    default_message = "The option {field} not a recognized option."


class OptionInvalidError(OptionUserError):
    """
    Base class for all exceptions that are raised when a user provided option value is
    invalid.
    """
    default_message = "The option {field} is invalid."
    identifier = "Invalid Option"


class OptionInstanceOfError(OptionInvalidError):
    """
    Raised when an option user provided value is required to be of a specific type but is
    not of that type.
    """
    def __init__(self, param=None, types=None):
        types = ensure_iterable(types)
        super(OptionInstanceOfError, self).__init__(
            param=param,
            message="Must be an instance of %s." % types if types else None
        )


class OptionRequiredError(OptionInvalidError):
    """
    Raised when an option value is required but not specified.
    """
    default_message = "The option {field} is required."
