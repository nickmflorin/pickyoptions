from abc import ABCMeta, abstractproperty, abstractmethod
from copy import deepcopy
import functools
import logging
import six

from pickyoptions import settings
from pickyoptions.lib.utils import ensure_iterable

from .exceptions import PickyOptionsError


logger = logging.getLogger(settings.PACKAGE_NAME)


def track_init(func):
    assert func.__name__ == "__init__"
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        func(instance, *args, **kwargs)
        # This will not save the initialization state if it has already been
        # manually saved inside the __init__ method.
        instance.save_initialization_state(*args, **kwargs)
        # Perform the post init operations on the instance.
        instance.post_init(*args, **kwargs)
        # Mark the instance as initialized.
        instance.__initialized__ = True
    return inner


def lazy_init(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        instance.perform_lazy_init()
        return func(instance, *args, **kwargs)
    return inner


# TODO: Make sure this works properly with property setter.
def lazy_init_property(prop):
    @property
    def inner(instance, *args, **kwargs):
        instance.perform_lazy_init()
        return prop.fget(instance)
    return inner


class BaseMeta(ABCMeta):
    def __new__(cls, name, bases, dct):
        # Note: The abstract_properties and abstract_methods are not inherited,
        # which is what we want.

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

        instance = super(BaseMeta, cls).__new__(cls, name, bases, dct)

        # If the model is not an abstract one, we want to track the init to
        # perform the post_init method when it is finished.
        abstract = dct.get('__abstract__', True)
        if abstract is False:
            dct['__lazyinitargs__'] = ()
            dct['__lazyinitkwargs__'] = {}

            # If the model is not abstract, it's parents should all be abstract.
            for kls in bases:
                if kls.__abstract__ is False:
                    raise PickyOptionsError(
                        "Each __abstract__ model can only have "
                        "non-__abstract__ parents."
                    )
            instance.__init__ = track_init(instance.__init__)
        return instance


class Base(six.with_metaclass(BaseMeta)):
    __abstract__ = True
    __initialized__ = False
    __lazy_initialized__ = False
    __lazyinit_state_stored__ = False

    def __init__(self, routines=None):
        from pickyoptions.core.routine.routines import Routines

        if not self.__initialized__:
            if not isinstance(routines, Routines):
                routines = ensure_iterable(routines, cast=tuple)
                self.routines = Routines(*routines)
            else:
                self.routines = routines

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def save_initialization_state(self, *args, **kwargs):
        """
        Stores the arguments provided on initialization so they can be
        reapplied to lazy initialization routines later on.

        The initialization state is only allowed to be saved once.  If
        attempting to save the state outside of __init__, the state will not
        update (since the save_initialization_state decorator already applied
        them at the end of __init__).

        If manually saving the initialization state, the state must be saved
        inside of the __init__ method.
        """
        if self.__initialization_state_stored__ is False:
            self.__lazyinitargs__ = tuple(args)
            self.__lazyinitkwargs__ = dict(**kwargs)
            self.__lazyinit_state_stored__ = True

    @property
    def initialized(self):
        return self.__initialized__

    def perform_lazy_init(self):
        if not self.__lazy_initialized__:
            self.lazy_init(*self.__lazyinitargs__, **self.__lazyinitkwargs__)
            self.__lazy_initialized__ = True

    def post_init(self, *args, **kwargs):
        if self.initialized:
            raise PickyOptionsError(
                "Cannot perform post_init once the instance is initialized.")

    def lazy_init(self, *args, **kwargs):
        pass

    def create_routine(self, id, cls=None, **kwargs):
        from pickyoptions.core.routine.routine import Routine
        cls = cls or Routine
        routine = cls(self, id, **kwargs)
        self.routines.append(routine)

    def reset_routines(self):
        self.routines.reset()

    def clear_routine_queues(self):
        self.routines.clear_queues()

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
