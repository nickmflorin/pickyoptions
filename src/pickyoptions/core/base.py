from abc import ABCMeta, abstractproperty, abstractmethod
from copy import deepcopy
import functools
import logging
import six

from pickyoptions import settings
from pickyoptions.lib.utils import ensure_iterable, merge_dicts

from .exceptions import PickyOptionsError


logger = logging.getLogger(settings.PACKAGE_NAME)


def track_init(func):
    assert func.__name__ == "__init__"
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        assert not instance.__initialized__
        instance.__initializing__ = True

        func(instance, *args, **kwargs)

        # This will not save the initialization state if it has already been
        # manually saved inside the __init__ method.
        instance.save_initialization_state(*args, **kwargs)

        # Mark the instance as initialized.
        instance.__initialized__ = True
        instance.__initializing__ = False

        # Perform the post init operations on the instance.
        if hasattr(instance, '__postinit__'):
            instance.__postinit__(*args, **kwargs)
    return inner


def lazy_init(func):
    assert func.__name__ == "__lazyinit__"
    @functools.wraps(func)
    def inner(instance):
        assert instance.__initialized__
        assert not instance.__lazyinitialized__
        instance.__lazy_initializing__ = True

        func(instance,
            *instance.__lazyinitargs__, **instance.__lazyinitkwargs__)

        # Mark the instance as initialized.
        instance.__lazyinitialized__ = True
        instance.__lazy_initializing__ = False
    return inner


def lazy(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        assert instance.initialized
        if not instance.__lazyinitialized__:
            instance.__lazyinit__()
        return func(instance, *args, **kwargs)
    return inner


# TODO: Make sure this works properly with property setter.
def lazy_property(prop):
    @property
    def inner(instance, *args, **kwargs):
        instance.perform_lazy_init()
        return prop.fget(instance)
    return inner


class BaseMeta(ABCMeta):
    """
    Metaclass for the `obj:Base` model.
    """
    def __new__(cls, name, bases, dct):

        def merge_base_dicts(attribute):
            """
            Merges in data from the provided bases and joins that data with
            the data for this class.
            """
            # Merge all of the dicts for each base together.
            results = []
            for base in bases:
                default_value = deepcopy(getattr(base, attribute, dict()))
                assert isinstance(default_value, dict)
                if default_value not in results:
                    results.append(default_value)
            results = merge_dicts(results)

            # Merge the dictionary of merged base values with the dictionary of
            # values on this class.
            current_value = deepcopy(dct.get(attribute, dict()))
            results.update(**current_value)
            return results

        def merge_base_iterables(attribute, cast=list):
            """
            Merges in data from the provided bases and joins that data with
            the data for this class.
            """
            # Merge all of the lists for each base together.
            results = []
            for base in bases:
                default_value = deepcopy(getattr(base, attribute, tuple()))
                assert isinstance(default_value, (tuple, list))
                for val in default_value:
                    if val not in results:
                        results.append(val)

            # Merge the list of merged base values with the list of values
            # on this class.
            current_value = dct.get(attribute, tuple())
            for val in current_value:
                assert not isinstance(val, (list, tuple))
                results.append(val)
            return cast(results)

        is_abstract = dct.get('__abstract__', True)

        # These properties are not allowed to be on a class if it is not
        # abstract.
        abstracts = (
            'abstract_properties',
            'abstract_methods',
            'required_errors'
        )

        # Make sure the above properties are not on a class if it is not
        # abstract.
        if not is_abstract and any([x in dct for x in abstracts]):
            found = [x for x in abstracts if x in dct]
            assert len(found) != 0
            raise TypeError(
                "Cannot specify properties %s for a non-abstract "
                "class." % ", ".join(found)
            )

        # Conglomerate the error mappings together, regardless of whether or
        # not it is abstract.
        dct['errors'] = merge_base_dicts('errors')

        if is_abstract:
            # If the class is abstract, conglomerate abstract properties with the
            # bases and assign @abstractproperty decorated properties to the
            # abstract class.
            abstract_properties = merge_base_iterables('abstract_properties')
            # Only store the combined abstract properties on the class if it
            # is not abstract - this allows for multiple levels of inheritance.
            dct['abstract_properties'] = tuple(abstract_properties)

            # NOTE: This might cause some @abstractproperty decorated properties
            # to be overwritten from the exact form in the inheritance - this is
            # not a big deal but should be noted.
            for prop in abstract_properties:
                @abstractproperty
                def func(*args, **kwargs):
                    pass
                func.__name__ = prop
                dct[prop] = func

            # If the class is abstract, conglomerate abstract methods with the
            # bases and assign @abstractmethod decorated methods to the abstract
            # class.
            abstract_methods = merge_base_iterables('abstract_methods')
            # Only store the combined abstract methods on the class if it
            # is not abstract - this allows for multiple levels of inheritance.
            dct['abstract_methods'] = tuple(abstract_methods)

            # NOTE: This might cause some @abstractmethod decorated properties
            # to be overwritten from the exact form in the inheritance - this is
            # not a big deal but should be noted.
            for method in abstract_methods:
                @abstractmethod
                def func(*args, **kwargs):
                    pass
                func.__name__ = method
                dct[method] = func

            # Conglomerate the required errors together.
            required_errors = merge_base_iterables('required_errors')
            dct['required_errors'] = tuple(required_errors)

            # Make sure all of the required errors are present.
            for err in dct['required_errors']:
                if err not in dct['errors'] and not is_abstract:
                    raise Exception("Error %s is missing from class %s." % (
                        err, name))
        else:
            # If the model is not an abstract one, we want to track the init to
            # perform the post_init method when it is finished.
            dct['__lazyinitargs__'] = ()
            dct['__lazyinitkwargs__'] = {}

        instance = super(BaseMeta, cls).__new__(cls, name, bases, dct)

        # Note: For the __init__ and lazy_init methods, we cannot have a
        # non-abstract class extend a non-abstract class and override these
        # methods - the decorators will be applied to both.  We should build in
        # a check for this, or maybe just manually place the decorators.
        if not is_abstract:
            if hasattr(instance, '__init__'):
                # Make sure that the instance __init__ method is not already
                # decorated.
                assert not hasattr(instance.__init__, '__decorated__')
                instance.__init__ = track_init(instance.__init__)
                instance.__init__.__decorated__ = True

            if hasattr(instance, '__lazyinit__'):
                # Make sure that the instance __lazyinit__ method is not already
                # decorated.
                assert not hasattr(instance.__lazyinit__, '__decorated__')
                instance.__lazyinit__ = lazy_init(instance.__lazyinit__)
                instance.__lazyinit__.__decorated__ = True

        return instance


# In an attempt to mitigate the chance of recursion problems.
def during_lazy_init(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        instance.__lazy_initializing__ = True
        func(instance, *args, **kwargs)
        instance.__lazy_initializing__ = False
    return inner


class BaseMixin(object):
    errors = {}
    require_errors = ()

    @property
    def is_abstract(self):
        return getattr(self, '__abstract__', True) is True

    # def perform_lazy_init(self):
    #     if self.is_abstract:
    #         raise Exception("Only non-abstract classes can lazily initialize.")
    #
    #     # In an attempt to mitigate the chance of recursion problems.
    #     if self.__lazy_initializing__:
    #         raise Exception("The class instance is already lazy initializing.")
    #
    #     if not self.__lazy_initialized__:
    #         # Lazy init might not actually be present on the instance.
    #         # This is all in an attempt to quell the recursion issues.
    #         # if hasattr(self, 'lazy_init'):
    #         # This now means that lazy_init cannot be called publically.
    #         self.__lazy_initializing__ = True
    #         assert hasattr(self, 'lazy_init')
    #         self.lazy_init(*self.__lazyinitargs__, **self.__lazyinitkwargs__)
    #         self.__lazy_initializing__ = False
    #         self.__lazy_initialized__ = True

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

        if settings.DEBUG:
            kwargs['instance'] = self.__class__.__name__

        exc = cls(*args, **kwargs)
        if strict is False:
            logger.log(level, "%s" % exc)
            return exc
        elif return_exception:
            return exc
        else:
            raise exc

    @property
    def is_child(self):
        from pickyoptions.core.configuration.child import ChildMixin
        return isinstance(self, ChildMixin)

    @property
    def is_parent(self):
        from pickyoptions.core.configuration.parent import ParentMixin
        return isinstance(self, ParentMixin)


class Base(six.with_metaclass(BaseMeta, BaseMixin)):
    __abstract__ = True

    __initialized__ = False
    __initializing__ = False

    __lazyinitialized__ = False
    __lazyinitializing__ = False

    __lazyinit_state_stored__ = False

    def __init__(self, routines=None, errors=None):
        # TODO: We might want to consider allowing the init args and kwargs to
        # be passed to the init method of the Base.
        from pickyoptions.core.routine.routines import Routines

        # If the base is initialized multiple times, routines that were created
        # in __init__ will be overridden.
        if self.initialized:
            raise Exception("The base is being initialized multiple times.")

        if not isinstance(routines, Routines):
            routines = ensure_iterable(routines, cast=tuple)
            self.routines = Routines(*routines)
        else:
            self.routines = routines

        # Allow errors to be overridden on initialization.  To do this, we need
        # to make sure the class errors are not mutated.
        errors = errors or {}
        self.errors = deepcopy(self.errors)
        self.errors.update(**errors)

    @property
    def initialized(self):
        return self.__initialized__

    @property
    def lazy_initialized(self):
        return self.__lazyinitialized__

    @property
    def initializing(self):
        return self.__initializing__

    @property
    def lazy_initializing(self):
        return self.__lazyinitializing__

    def __repr__(self, **kwargs):
        return "<%s %s>" % (
            self.__class__.__name__,
            " ".join(["%s=%s" % (k, v) for k, v in kwargs.items()])
        )

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def override_errors(self, *args, **kwargs):
        """
        Overrides the errors on the instance class with different errors.  The
        provided errors must already exist in the error mapping for the
        instance.
        """
        data = dict(*args, **kwargs)
        for k, v in data.items():
            if k not in self.errors:
                raise Exception(
                    "Cannot override error %s on %s instance as it does not "
                    "have the error to begin with." % (
                        k, self.__class__.__name__)
                )
            if v is not None:
                self.errors[k] = v

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
        if self.__lazyinit_state_stored__ is False:
            self.__lazyinitargs__ = tuple(args)
            self.__lazyinitkwargs__ = dict(**kwargs)
            self.__lazyinit_state_stored__ = True
