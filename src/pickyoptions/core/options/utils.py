import functools


def require_populated(func):
    """
    Decorator to ensure that the instance is populated before proceeding.

    This decorator can only be applied to instances of `obj:Option` and
    `obj:Options`.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from pickyoptions.core.options.option import Option
        from pickyoptions.core.options.options import Options

        assert isinstance(instance, (Option, Options))
        if not instance.populated:
            instance.raise_not_populated()
        return func(instance, *args, **kwargs)
    return inner


def require_populating_or_populated(func):
    """
    Decorator to ensure that the instance is either populated or populating
    before proceeding..

    This decorator can only be applied to instances of `obj:Option` and
    `obj:Options`.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from pickyoptions.core.options.option import Option
        from pickyoptions.core.options.options import Options

        assert isinstance(instance, (Option, Options))
        if not instance.populated and not instance.populating:
            instance.raise_not_populated_or_populating()
        return func(instance, *args, **kwargs)
    return inner


def require_populated_property(func):
    """
    Decorator for instance properties to ensure that the instance is populated
    before accessing the property value.

    This decorator can only be applied to instances of `obj:Option` and
    `obj:Options`.

    NOTE:
    ----
    Be careful applying this to properties with setters!
    """
    @property
    def inner(instance):
        from pickyoptions.core.options.option import Option
        from pickyoptions.core.options.options import Options

        assert isinstance(instance, (Option, Options))
        if not instance.populated:
            instance.raise_not_populated()
        return func(instance)
    return inner
