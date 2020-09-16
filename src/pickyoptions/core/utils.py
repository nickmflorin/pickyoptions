import functools
import six

from pickyoptions.lib.utils import optional_parameter_decorator
from .exceptions import PickyOptionsError


@optional_parameter_decorator
def accumulate_errors(func, error_cls=None, *args, **kwargs):
    error_cls = error_cls or PickyOptionsError

    def inner(*args, **kwargs):
        # Allow the error class to be a string attribute on the instance.
        if isinstance(error_cls, six.string_types):
            assert len(args) != 0
            assert hasattr(args[0], error_cls)
            error = getattr(args[0], error_cls)(*args, **kwargs)
        else:
            error = error_cls(*args, **kwargs)

        gen = func(*args, **kwargs)
        for exc in gen:
            assert isinstance(exc, Exception)
            error.append(exc)
        if error.has_children:
            raise error
    return inner


def require_set(func):
    """
    Decorator to ensure that the instance value is set before proceeding.

    This decorator can only be applied to instances of `obj:Value` and
    `obj:Valued`.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from pickyoptions.core.configuration import Configuration
        from pickyoptions.core.options import Option

        assert isinstance(instance, (Configuration, Option))
        if not instance.set:
            instance.raise_not_set()
        return func(instance, *args, **kwargs)
    return inner


def require_set_property(prop):
    """
    Decorator for instance properties to ensure that the instance value is
    set before accessing the property value.

    This decorator can only be applied to instances of `obj:Value` and
    `obj:Valued`.

    NOTE:
    ----
    Be careful applying this to properties with setters!
    """
    @property
    def inner(instance):
        from pickyoptions.core.configuration import Configuration
        from pickyoptions.core.options import Option

        assert isinstance(instance, (Configuration, Option))
        if not instance.set:
            instance.raise_not_set()
        return prop.fget(instance)
    return inner
