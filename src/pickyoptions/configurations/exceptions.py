from pickyoptions.configuration.exceptions import ConfigurationError


class ConfigurationDoesNotExist(ConfigurationError):
    default_message = "Configuration for `{field}` does not exist."
