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
