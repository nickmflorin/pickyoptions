# from abc import ABCMeta, abstractproperty
from copy import deepcopy
import functools
import logging

from pickyoptions import settings
from pickyoptions.exceptions import PickyOptionsError


logger = logging.getLogger(settings.PACKAGE_NAME)


def track_init(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        func(instance, *args, **kwargs)
        instance.finish_init()
    return inner


class BaseModel(object):
    _initialized = False

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def finish_init(self):
        self._initialized = True

    @property
    def initialized(self):
        return self._initialized

    def raise_with_self(self, *args, **kwargs):
        cls = kwargs.pop('cls', PickyOptionsError)

        strict = kwargs.pop('strict', None)
        level = kwargs.pop('level', logging.ERROR)
        return_exception = kwargs.pop('return_exception', False)

        exc = cls(*args, **kwargs)
        if strict is False:
            logger.log(level, "%s" % exc)
            return exc
        elif return_exception:
            return exc
        else:
            raise exc
