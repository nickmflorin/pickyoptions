import functools


def require_configured(func):
    """
    Decorator to ensure that the instance is configured before proceeding.

    This decorator can only be applied to instances of `obj:Configurable`.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from .configurable import ConfigurableMixin

        assert isinstance(instance, ConfigurableMixin)
        if not instance.configured:
            instance.raise_not_configured()
        return func(instance, *args, **kwargs)
    return inner


def require_configured_property(func):
    """
    Decorator for instance properties to ensure that the instance is configured
    before accessing the property value.

    This decorator can only be applied to instances of `obj:Configurable`.

    NOTE:
    ----
    Be careful applying this to properties with setters!
    """
    @property
    def inner(instance, *args, **kwargs):
        from .configurable import ConfigurableMixin

        assert isinstance(instance, ConfigurableMixin)
        if not instance.configured:
            instance.raise_not_configured()
        return func(instance, *args, **kwargs)
    return inner
