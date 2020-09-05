from pickyoptions.exceptions import PickyOptionsError, FieldParameterizedError


class PickyOptionsConfigurationError(PickyOptionsError):
    """
    Base class for exceptions that are raised during configuration of the options or option.
    """
    pass


# TODO: Allow this to be more descriptive about what class the configuration is referring to.
class ConfigurationDoesNotExist(FieldParameterizedError, PickyOptionsConfigurationError):
    default_message = "Configuration does not exist."
