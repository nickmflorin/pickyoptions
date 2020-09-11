from abc import ABCMeta, abstractproperty
import logging
import six

from pickyoptions import settings
from pickyoptions.base import BaseModel
from pickyoptions.exceptions import PickyOptionsError, ObjectTypeError


logger = logging.getLogger(settings.PACKAGE_NAME)


class Child(six.with_metaclass(ABCMeta, BaseModel)):
    def __init__(self, parent=None):
        self._assigned = False
        self._parent = None
        # self._value = constants.NOTSET
        # self._set = False
        # self._defaulted = constants.NOTSET

        if parent is not None:
            self.assign_parent(parent)

    @abstractproperty
    def parent_cls(self):
        pass

    @abstractproperty
    def child_identifier(self):
        pass

    @property
    def assigned(self):
        return self._assigned
    #
    # def reset(self):
    #     self._value = constants.NOTSET
    #     self._defaulted = constants.NOTSET
    #     self._set = False
    #
    # @property
    # def set(self):
    #     if self._set:
    #         assert self._value != constants.NOTSET
    #         return self._set
    #     self._value == constants.NOTSET
    #     return self._set
    #
    # @property
    # def defaulted(self):
    #     self.assert_set()
    #     return self._defaulted

    @property
    def identifier(self):
        child_identifier = getattr(self, 'child_identifier')
        if six.callable(child_identifier):
            return child_identifier(self)
        return getattr(self, child_identifier)

    def raise_with_self(self, *args, **kwargs):
        kwargs.setdefault('field', self.identifier)
        super(Child, self).raise_with_self(*args, **kwargs)

    def assert_set(self, *args, **kwargs):
        if not self.set:
            self.raise_not_set(*args, **kwargs)

    def raise_not_set(self, *args, **kwargs):
        kwargs.setdefault('cls', getattr(self, 'child_not_set_error', None))
        return self.raise_with_self(*args, **kwargs)

    def raise_invalid(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is invalid.
        """
        kwargs.setdefault('cls', getattr(self, 'invalid_child_error', None))
        return self.raise_with_self(*args, **kwargs)

    def raise_invalid_type(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is of
        invalid type.
        """
        kwargs.setdefault('cls', getattr(self, 'invalid_child_type_error', None))
        return self.raise_invalid(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is
        required and does not exist.
        """
        kwargs.setdefault('cls', getattr(self, 'required_child_error', None))
        return self.raise_invalid(*args, **kwargs)

    @property
    def parent(self):
        """
        Returns the assigned parent of the `obj:Child` instance if it is
        assigned.  If the parent is not assigned to the `obj:Child` instance,
        an exception will be thrown - so it is necessary to check if the
        `obj:Child` is assigned before accessing the parent.

        TODO:
        ----
        - What should we do if the parent is changed?  We don't have a setter
          for parent, but the parent can still be removed/re-assigned.  Do we
          have to trigger some sort of reconfiguration?
        """
        if self._parent is None:
            raise PickyOptionsError(
                "The %s instance has not been assigned a parent yet."
                % self.__class__.__name__
            )
        return self._parent

    def validate_parent(self, parent):
        if isinstance(self.parent_cls, six.string_types):
            if parent.__class__.__name__ != self.parent_cls:
                raise ObjectTypeError(
                    value=parent,
                    message="The parent must be of type `{types}`.",
                    types=self.parent_cls,
                )
        elif hasattr(self.parent_cls, '__iter__'):
            assert all([isinstance(v, six.string_types) for v in self.parent_cls])
            if parent.__class__.__name__ not in self.parent_cls:
                raise ObjectTypeError(
                    value=parent,
                    message="The parent must be of type `{types}`.",
                    types=self.parent_cls
                )
        elif isinstance(self.parent_cls, type):
            if not isinstance(parent, self.parent_cls):
                raise ObjectTypeError(
                    value=parent,
                    message="The parent must be of type `{types}`.",
                    types=type(self.parent_cls),
                )
        else:
            raise ValueError(
                "The parent type %s is not a valid parent of child %s."
                % (type(parent), self.__class__.__name__)
            )

    def remove_parent(self):
        """
        Removes the parent from the `obj:Child` instance.
        """
        if not self.assigned:
            raise PickyOptionsError(
                "The %s instance does not have an assigned parent."
                % self.__class__.__name__
            )
        self._parent = None
        self._assigned = False

    def assign_parent(self, parent):
        """
        Assigns an `obj:Parent` (or another object) instance as the parent of
        the `obj:Child` instance.

        Parameters:
        ----------
        parent: `obj:object`
            The parent which we want to assign to this `obj:Child` instance.

            The parent can be arbitrary - it does need not be an instance of
            `obj:Parent` or have this `obj:Child` class defined in it's
            `child_cls` property.  This is because there are cases where we want
            to assign a `obj:Parent` to a `obj:Child` but not assign the
            `obj:Child` as a child to the `obj:Parent`.  Usually, this is because
            the `obj:Parent` is a parent to another set of children.
        """
        from .parent import Parent
        self.validate_parent(parent)

        if self.assigned:
            raise PickyOptionsError(
                "The %s instance already has an assigned parent."
                % self.__class__.__name__
            )

        self._parent = parent
        if isinstance(parent, Parent) and isinstance(self, parent.child_cls):
            if not parent.has_child(self):
                parent.assign_child(self)
            else:
                logger.debug(
                    "Not adding child %s instance as a child of the parent, "
                    "since it is already a child." % self.__class__.__name__
                )

        self._assigned = True
