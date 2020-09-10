from pickyoptions.exceptions import PickyOptionsError
from pickyoptions.configuration.exceptions import NotConfiguredError


class OptionsError(PickyOptionsError):
    """
    Abstract base class for all exceptions that are raised in reference to a specific set
    of of `obj:Options`.
    """
    pass


class OptionsNotConfiguredError(NotConfiguredError, OptionsError):
    default_message = "The options are not yet configured."


# TODO: Be able to include the individual errors from individual options being invalid.
class OptionsInvalidError(OptionsError):
    """
    Raised when the `obj:Options` are invalid as a whole.
    """
    identifier = "Invalid Options"
    default_message = "The options are invalid."