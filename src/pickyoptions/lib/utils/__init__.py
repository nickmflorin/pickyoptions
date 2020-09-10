from .arrays import *  # noqa
from .functions import *  # noqa
from .path_utils import *  # noqa


def is_null(value):
    if hasattr(value, '__iter__') and len(value) == 0:
        return True
    elif value is None:
        return True
    return False
