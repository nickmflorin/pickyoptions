from abc import ABCMeta, abstractproperty, abstractmethod
from copy import deepcopy
import functools
import logging
import six

from pickyoptions import settings

from .exceptions import PickyOptionsError


logger = logging.getLogger(settings.PACKAGE_NAME)


def track_init(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        func(instance, *args, **kwargs)
        instance.finish_init()
    return inner


class BaseModelMeta(ABCMeta):
    def __new__(cls, name, bases, dct):
        # TODO: To make this work for inheritance cases, we have to merge the
        # abstract method of the parent and the children classes.

        # Assign abstract properties.
        if 'abstract_properties' in dct:
            for abstract_property_name in dct['abstract_properties']:
                @abstractproperty
                def func(*args, **kwargs):
                    pass
                func.__name__ = abstract_property_name
                dct[abstract_property_name] = func

        # Assign abstract methods.
        if 'abstract_methods' in dct:
            for abstract_method_name in dct['abstract_methods']:
                @abstractmethod
                def func(*args, **kwargs):
                    pass
                func.__name__ = abstract_method_name
                dct[abstract_method_name] = func

        return super(BaseModelMeta, cls).__new__(cls, name, bases, dct)


class BaseModel(six.with_metaclass(BaseModelMeta)):
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

    def create_routine(self, **kwargs):
        pass

    def raise_with_self(self, *args, **kwargs):
        cls = kwargs.pop('cls', PickyOptionsError)

        strict = kwargs.pop('strict', None)
        level = kwargs.pop('level', logging.ERROR)
        return_exception = kwargs.pop('return_exception', False)

        kwargs.setdefault('instance', self)
        exc = cls(*args, **kwargs)
        if strict is False:
            logger.log(level, "%s" % exc)
            return exc
        elif return_exception:
            return exc
        else:
            raise exc
