import functools


def requires_configured(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if not instance.configured:
            instance.raise_not_configured()
        return func(instance, *args, **kwargs)
    return inner
