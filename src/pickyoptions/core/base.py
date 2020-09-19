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
        func(instance, *args, **kwargs)
        # This will not save the initialization state if it has already been
        # manually saved inside the __init__ method.
        instance.save_initialization_state(*args, **kwargs)
        # Perform the post init operations on the instance.
        instance.post_init(*args, **kwargs)
        # Mark the instance as initialized.
        instance.__initialized__ = True
    return inner


def lazy(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        instance.perform_lazy_init()
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
        # Assign abstract properties.  Note that the abstract properties are not
        # inherited, which is what we want.
        if 'abstract_properties' in dct:
            for abstract_property_name in dct['abstract_properties']:
                @abstractproperty
                def func(*args, **kwargs):
                    pass
                func.__name__ = abstract_property_name
                dct[abstract_property_name] = func

        # Assign abstract methods.  Note that the abstract methods are not
        # inherited, which is what we want.
        if 'abstract_methods' in dct:
            for abstract_method_name in dct['abstract_methods']:
                @abstractmethod
                def func(*args, **kwargs):
                    pass
                func.__name__ = abstract_method_name
                dct[abstract_method_name] = func

        # Conglomerate the required errors together.
        required_errors = list(dct.get('required_errors', ()))[:]
        for base in bases:
            base_required_errors = getattr(base, 'required_errors', [])
            for err in base_required_errors:
                if err not in required_errors:
                    required_errors.append(err)
        dct['required_errors'] = tuple(required_errors)

        # Conglomerate the parent error mappings for all base classes.
        parent_error_mappings = []
        for parent in bases:
            base_mapping = deepcopy(getattr(parent, 'errors', {}))
            assert isinstance(base_mapping, dict)
            parent_error_mappings.append(base_mapping)
        errors = merge_dicts(parent_error_mappings)

        # Update the parent error mappings with the instance error mappings.
        this_errors = deepcopy(dct.pop('errors', {}))
        assert isinstance(this_errors, dict)
        errors.update(this_errors)

        # Make sure all of the required errors are present.
        for err in dct['required_errors']:
            if err not in errors:
                raise Exception("Error %s is missing from class %s." % (
                    err, name))

        # Set the merged error mapping on the class.
        dct['errors'] = errors

        # If the model is not an abstract one, we want to track the init to
        # perform the post_init method when it is finished.
        if dct.get('__abstract__', True) is False:
            dct['__lazyinitargs__'] = ()
            dct['__lazyinitkwargs__'] = {}

            # If the model is not abstract, it's parents should all be abstract.
            for kls in bases:
                base_abstract = getattr(kls, '__abstract__', True)
                if base_abstract is False:
                    raise PickyOptionsError(
                        "Each __abstract__ model can only have "
                        "non-__abstract__ parents."
                    )

        instance = super(BaseMeta, cls).__new__(cls, name, bases, dct)
        if dct.get('__abstract__', True) is False:
            assert not hasattr(instance.__init__, '__tracked__')
            instance.__init__ = track_init(instance.__init__)
            instance.__init__.__tracked__ = True
            # Note: This means the lazy_init cannot be used in parent abstract
            # classes - we should validate this.
            # This is all in an attempt to quell the recursion issues.
            # if hasattr(instance, 'lazy_init'):
            #     instance.lazy_init = during_lazy_init(instance.lazy_init)

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

    @property
    def initialized(self):
        return self.__initialized__

    @property
    def is_abstract(self):
        return getattr(self, '__abstract__', True) is True

    def perform_lazy_init(self):
        if self.is_abstract:
            raise Exception("Only non-abstract classes can lazily initialize.")

        # In an attempt to mitigate the chance of recursion problems.
        if self.__lazy_initializing__:
            raise Exception("The class instance is already lazy initializing.")

        if not self.__lazy_initialized__:
            # Lazy init might not actually be present on the instance.
            # This is all in an attempt to quell the recursion issues.
            # if hasattr(self, 'lazy_init'):
            # This now means that lazy_init cannot be called publically.
            self.__lazy_initializing__ = True
            assert hasattr(self, 'lazy_init')
            self.lazy_init(*self.__lazyinitargs__, **self.__lazyinitkwargs__)
            self.__lazy_initializing__ = False
            self.__lazy_initialized__ = True

    def post_init(self, *args, **kwargs):
        if self.initialized:
            raise PickyOptionsError(
                "Cannot perform post_init once the instance is initialized.")

    # The lazy init cannot be used in parent abstract classes because we are
    # tracking it, the base lazy init is the only one that can be called.
    # def lazy_init(self, *args, **kwargs):
    #     pass

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
    __lazy_initialized__ = False
    __lazy_initializing__ = False
    __lazyinit_state_stored__ = False

    def __init__(self, routines=None, errors=None):
        # TODO: We might want to consider allowing the init args and kwargs to
        # be passed to the init method of the Base.
        from pickyoptions.core.routine.routines import Routines

        if not self.__initialized__:
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
