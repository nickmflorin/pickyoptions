import logging
import six

from pickyoptions import settings
from pickyoptions.lib.utils import extends_or_instance_of

from pickyoptions.core.base import Base
from pickyoptions.core.exceptions import (
    PickyOptionsError,
    ValueTypeError,
    ValueNotSetError,
    ValueRequiredError,
    ValueInvalidError,
    ValueLockedError,
    ValueNotRequiredError,
    ValueSetError
)


logger = logging.getLogger(settings.PACKAGE_NAME)


class Child(Base):
    __abstract__ = True
    abstract_properties = ('parent_cls', )

    # TODO: Move logic to the base model to apply in more than one circumstance.
    errors = (
        # TODO: Make extensions for the specific object.
        ('set_error', ValueSetError),
        ('not_set_error', ValueNotSetError),
        ('required_error', ValueRequiredError),
        # TODO: Make extensions for the specific object.
        ('not_required_error', ValueNotRequiredError),
        ('invalid_type_error', ValueTypeError),
        ('invalid_error', ValueInvalidError),
        ('locked_error', ValueLockedError),
    )

    def __init__(self, field, parent=None, **kwargs):
        super(Child, self).__init__()

        self._assigned = False
        self._field = field
        if not isinstance(self._field, six.string_types):
            # Use self.raise_invalid_type?
            raise ValueTypeError(
                name="field",
                types=six.string_types,
            )
        elif self._field.startswith('_'):
            # Use self.raise_invalid?
            raise ValueInvalidError(
                name="field",
                detail="It cannot be scoped as a private attribute."
            )

        self._parent = None
        if parent is not None:
            self.assign_parent(parent)

        # TODO: Move logic to the base model to apply in more than one
        # circumstance.
        for error_tuple in self.errors:
            # This hasattr might cause problems!
            if not hasattr(self, error_tuple[0]):
                object.__setattr__(
                    self,
                    error_tuple[0],
                    kwargs.get(error_tuple[0], error_tuple[1])
                )
            else:
                object.__setattr__(
                    self,
                    error_tuple[0],
                    kwargs.get(error_tuple[0], getattr(self, error_tuple[0]))
                )

    @property
    def field(self):
        return self._field

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

    def raise_with_self(self, *args, **kwargs):
        kwargs.setdefault('name', self.field)
        super(Child, self).raise_with_self(*args, **kwargs)

    def raise_set(self, *args, **kwargs):
        # TODO: Come up with extensions for the specific object.
        kwargs['cls'] = ValueSetError
        return self.raise_with_self(*args, **kwargs)

    def raise_not_set(self, *args, **kwargs):
        kwargs.setdefault('cls', getattr(self, 'not_set_error'))
        return self.raise_with_self(*args, **kwargs)

    def raise_locked(self, *args, **kwargs):
        kwargs['cls'] = self.locked_error
        return self.raise_with_self(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        """
        Raises an exception to indicate that the `obj:Child` instance is
        required and does not exist.
        """
        kwargs['cls'] = self.required_error
        return self.raise_with_self(*args, **kwargs)

    def raise_not_required(self, *args, **kwargs):
        # TODO: Come up with extensions for the specific object.
        kwargs['cls'] = self.not_required_error
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
        kwargs['cls'] = self.invalid_type_error
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
