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
