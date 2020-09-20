import logging

from pickyoptions import settings
from pickyoptions.lib.utils import extends_or_instance_of

from pickyoptions.core.base import Base, BaseMixin
from pickyoptions.core.decorators import raise_with_error
from pickyoptions.core.exceptions import (
    PickyOptionsError,
    ValueTypeError,
)


logger = logging.getLogger(settings.PACKAGE_NAME)


class ChildMixin(BaseMixin):
    abstract_properties = ('parent_cls', )
    required_errors = (
        'set_error',
        'not_set_error',
        'required_error',
        'not_required_error',
        'invalid_type_error',
        'invalid_error',
        'locked_error',
        'not_null_error',
    )

    def _init(self, parent=None, error_map=None):
        self._assigned = False
        self._parent = None
        if parent is not None:
            self.assign_parent(parent)

    @property
    def field(self):
        return self._field

    def raise_with_self(self, *args, **kwargs):
        kwargs['name'] = self.field
        return super(ChildMixin, self).raise_with_self(*args, **kwargs)

    def assert_set(self, *args, **kwargs):
        if not self.set:
            self.raise_not_set(*args, **kwargs)

    def assert_not_set(self, *args, **kwargs):
        if self.set:
            self.raise_set(*args, **kwargs)

    def assert_required(self, *args, **kwargs):
        if not self.required:
            self.raise_not_required(*args, **kwargs)

    def assert_not_required(self, *args, **kwargs):
        if self.required:
            self.raise_required(*args, **kwargs)

    @raise_with_error(error='set_error')
    def raise_set(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is set
        when it is not expected to be set.
        """
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='not_set_error')
    def raise_not_set(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is not
        set when it is expected to be set.
        """
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='locked_error')
    def raise_locked(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is
        locked and cannot be altered.
        """
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='required_error')
    def raise_required(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is
        required and does not exist.
        """
        return self.raise_with_self(*args, **kwargs)

    # TODO: Come up with extensions for the specific object.
    # TODO: Is this even being used anymore?
    @raise_with_error(error='not_required_error')
    def raise_not_required(self, *args, **kwargs):
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='not_null_error')
    def raise_null_not_allowed(self, *args, **kwargs):
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='invalid_error')
    def raise_invalid(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is invalid.
        """
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='invalid_type_error')
    def raise_invalid_type(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is of
        invalid type.
        """
        assert 'types' in kwargs
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


class Child(ChildMixin, Base):
    __abstract__ = True

    def __init__(self, parent=None, **kwargs):
        super(Child, self).__init__()
        ChildMixin._init(parent=parent, **kwargs)
