import functools
import six
import sys


try:
    from inspect import signature
except ImportError:
    if six.PY3:
        six.reraise(*sys.exc_info())
    from inspect import getargspec


def check_num_function_arguments(func, num_arguments=0):
    if six.PY3:
        sig = signature(func)
        return len(sig.parameters) == num_arguments
    else:
        spec = getargspec(func)
        return len(spec.args) == num_arguments


def optional_parameter_decorator(f):
    """
    A decorator for a decorator, allowing the decorator to be used both with and without
    arguments applied.

    Example:
    ------
    @decorator(arg1, arg2, kwarg1='foo')
    @decorator
    """
    @functools.wraps(f)
    def wrapped_decorator(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            # Return the actual decorated function.
            return f(args[0])
        else:
            # Wrap the function in a decorator in the case that arguments are applied.
            return lambda realf: f(realf, *args, **kwargs)
    return wrapped_decorator
