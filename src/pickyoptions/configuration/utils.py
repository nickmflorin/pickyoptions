import functools


def doublewrap(f):
    '''
    a decorator decorator, allowing the decorator to be used as:
    @decorator(with, arguments, and=kwargs)
    or
    @decorator
    '''
    @functools.wraps(f)
    def new_dec(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # actual decorated function
            return f(args[0])
        else:
            # decorator arguments
            return lambda realf: f(realf, *args, **kwargs)

    return new_dec


def configurable_property_setter(obj, configuration_name=None):
    def _decorator(func):
        @obj.setter
        def inner(instance, value):
            instance._configuration[func.__name__] = value

            # If we are not in the process of setting multiple different configurations values,
            # we should validate after it is set.
            if not instance.configuring:
                instance.validate_configuration()
        return inner
    return _decorator


@doublewrap
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

        assert not configuration.required
        return configuration.default
    return inner
