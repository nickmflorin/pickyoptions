from pickyoptions.core.exceptions import PickyOptionsError
from pickyoptions.core.configuration.exceptions import (
    NotConfiguredError, ConfiguringError)


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
