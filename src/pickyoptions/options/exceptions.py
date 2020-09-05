from pickyoptions.exceptions import ValueParameterizedError, PickyOptionsUserError
from pickyoptions.configuration.exceptions import PickyOptionsConfigurationError

__all__ = (
    'OptionsInvalidError',
)


class OptionsError(ValueParameterizedError):
    """
    Abstract base class for all exceptions that are raised in reference to a specific set
    of of `obj:Options`.
    """
    pass


class OptionsNotPopulatedError(OptionsError):
    pass


class OptionsUserError(OptionsError, PickyOptionsUserError):
    """
    Abstract base class for all exceptions that are raised in reference to a user provided
    values to an already configured `obj:Options` instance.
    """
    pass


class OptionsConfigurationError(OptionsError, PickyOptionsConfigurationError):
    """
    Raised when the configuration provided to an `obj:Options` is invalid.
    """
    pass


class OptionsInvalidError(OptionsUserError):
    """
    Raised when the overall `obj:Options` values are invalid as a set.
    """
    pass
