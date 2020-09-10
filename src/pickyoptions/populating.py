# from abc import ABCMeta, abstractproperty, abstractmethod
import contextlib
import functools
import logging
import six
import sys

from pickyoptions import settings, constants
from pickyoptions.base import BaseModel


logger = logging.getLogger(settings.PACKAGE_NAME)


def requires_not_populating(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if instance.populating:
            instance.raise_populating()
        return func(instance, *args, **kwargs)
    return inner


def requires_populated(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if not instance.populated:
            instance.raise_not_populated()
        return func(instance, *args, **kwargs)
    return inner


# Only currently applicable for the Option.
def requires_value_set(func):
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        if not instance.set:
            instance.raise_not_set()
        return func(instance, *args, **kwargs)
    return inner


class Restorable(BaseModel):
    def __init__(self):
        self._restoring = False


class Overriding(Restorable):
    def __init__(self):
        # Keeps track of whether or not the instance has been overridden.
        super(Overriding, self).__init__()
        self._overridden = False
        self._overriding = False
        self._overridden_value = constants.NOTSET

    @property
    def overridden(self):
        return self._overridden

    @property
    def overriding(self):
        return self._overriding

    @property
    def overridden_value(self):
        return self._overridden_value

    def pre_override(self):
        logger.debug('Performing pre-override on %s.' % self.__class__.__name__)

    def post_override(self):
        logger.debug('Performing post-override on %s.' % self.__class__.__name__)

    def reset(self):
        # Do we want this?  We usually only reset right before populating, which resets the
        # overridden value anyways.
        self._overridden_value = constants.NOTSET
        self._overridden = False

    @contextlib.contextmanager
    def override_routine(self):
        self._overriding = True
        self.pre_override()
        try:
            logger.debug("Entering override routine context.")
            yield self
        except Exception:
            six.reraise(*sys.exc_info())
        else:
            self._overriding = False
            # Populated will only be False before the first population, afterwards it will always
            # be True, until the options are reset.
            self._overridden = True
            # We don't reset the overridden value because that is not reset until the object
            # is repopulated.
            # self._overridden_value = constants.NOTSET

            self.post_override()
            logger.debug("Exiting override routine context.")


class Populating(Overriding):
    def __init__(self):
        super(Populating, self).__init__()
        # TODO: Move this to the `obj:Option` instance.
        self._set = False  # This is only applicable for the `obj:Option` right now...

        # Keeps track of whether or not the instance has already been populated and whether or not
        # the instance value has been set.  The instance will only be populated if the associated
        # field is in the data, but the instance will always be set after it's value is assigned,
        # regardless of whether or not it is through population or direct set.
        self._populated = False
        # Tracks what the populated value was so it can be restored to that value at a later
        # point in time.  This is only really applicable for the Option right now, so maybe
        # it should be moved there.  The Options could have a `populated_value` in theory, but
        # they don't need to really track this since the options themselves do.
        self._populated_value = constants.NOTSET

        # Keeps track of whether or not the instance is in the process of being populated.
        self._populating = False

        # Keeps track of whether or not the instance has been overridden.
        self._overridden = False
        self._overriding = False
        self._overridden_value = constants.NOTSET

    @property
    def populated(self):
        """
        Returns whether or not the instance has been populated.

        This value will only be False before the first population, afterwards it will remain
        True unless the instance is reset - which would require another population afterwards.
        """
        return self._populated

    @property
    def set(self):
        return self._set

    @property
    def populating(self):
        """
        Returns whether or not the instance is in the process of populating.
        """
        return self._populating

    def raise_populating(self, *args, **kwargs):
        # ABCMeta is causing some problems, so instead we will (at least temporarily) assert that
        # the methods/properties are defined.
        assert hasattr(self, 'populating_error')
        kwargs.setdefault('cls', self.populating_error)
        return self.raise_with_self(*args, **kwargs)

    def raise_not_populated(self, *args, **kwargs):
        # ABCMeta is causing some problems, so instead we will (at least temporarily) assert that
        # the methods/properties are defined.
        assert hasattr(self, 'not_populated_error')
        kwargs.setdefault('cls', self.not_populated_error)
        return self.raise_with_self(*args, **kwargs)

    def raise_not_set(self, *args, **kwargs):
        # Right now, this is only applicable for the `obj:Option` - so the error property is
        # optional.
        # ABCMeta is causing some problems, so instead we will (at least temporarily) assert that
        # the methods/properties are defined.
        assert hasattr(self, 'not_set_error')
        kwargs.setdefault('cls', getattr(self, 'not_set_error', None))
        return self.raise_with_self(*args, **kwargs)

    def reset(self):
        # TODO: Do we want to require population here?
        logger.debug("Resetting %s." % self.__class__.__name__)
        super(Populating, self).reset()
        self._populated = False
        self._populated_option_values = {}

    def pre_population(self):
        self._overridden_value = constants.NOTSET
        logger.debug('Performing pre-population on %s.' % self.__class__.__name__)

    def post_population(self):
        logger.debug('Performing post-population on %s.' % self.__class__.__name__)

    @contextlib.contextmanager
    def population_routine(self):
        self.pre_population()
        self._populating = True
        try:
            logger.debug("Entering population routine context.")
            yield self
        except Exception:
            six.reraise(*sys.exc_info())
        else:
            self._populating = False
            # Populated will only be False before the first population, afterwards it will always
            # be True, until the options are reset.
            self._populated = True
            self._populated_value = constants.NOTSET

            self.post_population()
            logger.debug("Exiting population routine context.")
