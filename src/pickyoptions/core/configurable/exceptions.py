from pickyoptions.core.exceptions import PickyOptionsError


class ConfigurableError(PickyOptionsError):
    identifier = "Configurable Error"


class NotConfiguredError(ConfigurableError):
    default_message = "The configuration has not been configured."


class CannotReconfigureError(ConfigurableError):
    default_message = "The configuration cannot be reconfigured."


class ConfiguringError(ConfigurableError):
    default_message = "The configuration is already configuring."
