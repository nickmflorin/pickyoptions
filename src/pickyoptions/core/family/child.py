import logging
import six

from pickyoptions import settings
from pickyoptions.lib.utils import extends_or_instance_of

from pickyoptions.core.base import BaseModel
from pickyoptions.core.exceptions import PickyOptionsError
from pickyoptions.core.value.exceptions import (
    ValueTypeError,
    ValueNotSetError,
    ValueRequiredError,
    ValueInvalidError,
    ValueLockedError
)


logger = logging.getLogger(settings.PACKAGE_NAME)


class OnlyChild(BaseModel):
    abstract_properties = ('parent_cls', )

    not_set_error = ValueNotSetError
    required_error = ValueRequiredError
    invalid_type_error = ValueTypeError
    invalid_error = ValueInvalidError
    locked_error = ValueLockedError

    def __init__(self, parent=None, **kwargs):
        self._assigned = False
        self._parent = None
        if parent is not None:
            self.assign_parent(parent)

        self.not_set_error = kwargs.get('not_set_error', self.not_set_error)
        self.invalid_type_error = kwargs.get(
            'invalid_type_error', self.invalid_type_error)
        self.required_error = kwargs.get('required_error', self.required_error)
        self.invalid_error = kwargs.get('invalid_error', self.invalid_error)
        self.locked_error = kwargs.get('locked_error', self.locked_error)

    def assert_set(self, *args, **kwargs):
        if not self.set:
            self.raise_not_set(*args, **kwargs)

    def raise_not_set(self, *args, **kwargs):
        kwargs.setdefault('cls', getattr(self, 'not_set_error'))
        return self.raise_with_self(*args, **kwargs)

    def raise_invalid(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is invalid.
        """
        kwargs.setdefault('cls', getattr(self, 'invalid_error'))
        return self.raise_with_self(*args, **kwargs)

    def raise_invalid_type(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is of
        invalid type.
        """
        assert 'types' in kwargs
        kwargs.setdefault('cls', getattr(self, 'invalid_type_error'))
        return self.raise_invalid(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is
        required and does not exist.
        """
        kwargs.setdefault('cls', getattr(self, 'required_error'))
        return self.raise_invalid(*args, **kwargs)

    @property
    def assigned(self):
        return self._assigned

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
        if not extends_or_instance_of(parent, self.parent_cls):
            # TODO: Come up with a better error.
            raise ValueTypeError(
                value=parent,
                message="The parent must be of type `{types}`.",
                types=self.parent_cls,
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


class Child(OnlyChild):
    abstract_properties = OnlyChild.abstract_properties + ('child_identifier',)

    @property
    def identifier(self):
        child_identifier = getattr(self, 'child_identifier')
        if six.callable(child_identifier):
            return child_identifier(self)
        return getattr(self, child_identifier)

    def raise_with_self(self, *args, **kwargs):
        kwargs.setdefault('field', self.identifier)
        super(Child, self).raise_with_self(*args, **kwargs)
