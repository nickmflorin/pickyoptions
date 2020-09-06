from pickyoptions.exceptions import PickyOptionsError, ObjectTypeError


class ConfigurationError(PickyOptionsError):
    """
    Base class for exceptions that are raised during configuration of the options or option.
    """
    identifier = "Configuration Error"


class NotConfiguredError(ConfigurationError):
    pass


# TODO: Allow this to be more descriptive about what class the configuration is referring to.
class ConfigurationDoesNotExist(ConfigurationError):
    default_message = "Configuration does not exist."


class ConfigurationInvalidError(ConfigurationError):
    """
    Raised when the configuration provided to an `obj:Option` is invalid.
    """
    identifier = "Configuration Error"


class ConfigurationRequiredError(ConfigurationError):
    default_message = "The configuration `{field}` is required but was not provided."


class ConfigurationTypeError(ObjectTypeError, ConfigurationInvalidError):
    @property
    def default_message(self):
        if getattr(self, 'field', None) is not None:
            return "The configuration `{field}` must be an instance of {types}."
        return "Must be an instance of {types}."
