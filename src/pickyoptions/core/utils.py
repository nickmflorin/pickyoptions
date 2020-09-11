from pickyoptions.lib.utils import optional_parameter_decorator
from .exceptions import PickyOptionsError


@optional_parameter_decorator
def accumulate_errors(func, error_cls=None, *args, **kwargs):
    error_cls = error_cls or PickyOptionsError
    error = error_cls(*args, **kwargs)

    def inner(*args, **kwargs):
        gen = func(*args, **kwargs)
        for exc in gen:
            assert isinstance(exc, Exception)
            error.append(exc)
        if error.has_children:
            raise error
    return inner
