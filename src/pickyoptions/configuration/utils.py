from pickyoptions import constants
from pickyoptions.lib.utils import optional_parameter_decorator


def configurable_property_setter(obj, configuration_name=None):

    def decorator(func):
        # configuration_name = configuration_name or func.__name__

        @obj.setter
        def inner(instance, value):
            # assert configuration_name in instance._configuration
            instance._configuration[func.__name__] = value

            # If we are not in the process of setting multiple different configurations values,
            # we should validate after they are all set.
            if not instance.configuring:
                instance.validate_configuration()
        return inner
    return decorator


@optional_parameter_decorator
def configurable_property(func, configuration_name=None):
    configuration_name = configuration_name or func.__name__

    @property
    def inner(instance):
        # Get the actual configuration object.
        configuration = instance.configuration(configuration_name)

        # If the value associated with the configuration object was configured, return
        # it.  Otherwise, we need to return the default.
        if configuration.field in instance._configuration:
            return instance._configuration[configuration.field]

        # This might be redundant, since we also do it when the configurations are populated.
        configuration.validate_not_provided()

        # This would be an error on our end, not a user error.
        if configuration.required:
            # This applies when the default value is None as well.
            if configuration.default != constants.NOTSET:
                raise Exception(
                    "Cannot provide a default configuration value for %s if the "
                    "configuration is required." % configuration_name
                )
            raise Exception("The configuration %s is required." % configuration_name)
        else:
            # TODO: We have to potentially revisit this, we don't want this to cause runtime
            # errors for users which it might do if we don't set things up properly.
            if configuration.default == "NOTSET":
                raise Exception(
                    "The configuration %s is not required, but no default is specified. "
                    "The default value must be specified in the case that the configuration "
                    "value is not provided." % configuration_name
                )

            # This can be None, as long as the default was explicitly set to None.
            return configuration.default

    return inner
