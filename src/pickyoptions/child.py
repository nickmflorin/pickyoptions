import logging
import six

from pickyoptions import settings
from pickyoptions.base import BaseModel
from pickyoptions.exceptions import PickyOptionsError, ObjectTypeError


logger = logging.getLogger(settings.PACKAGE_NAME)


class Child(BaseModel):
    def __init__(self, parent=None):
        self._assigned = False
        self._parent = None
        if parent is not None:
            self.assign_parent(parent)

    @property
    def identifier(self):
        if not hasattr(self, 'child_identifier'):
            raise PickyOptionsError(
                "The child identifier must be specified on %s." % self.__class__.__name__)
        child_identifier = getattr(self, 'child_identifier')
        if six.callable(child_identifier):
            return child_identifier(self)
        return getattr(self, child_identifier)

    def raise_with_self(self, *args, **kwargs):
        kwargs.setdefault('field', self.identifier)
        super(Child, self).raise_with_self(*args, **kwargs)

    def raise_invalid(self, *args, **kwargs):
        # ABCMeta is causing some problems, so instead we will (at least temporarily) assert that
        # the methods/properties are defined.
        assert hasattr(self, 'invalid_child_error')
        kwargs.setdefault('cls', self.invalid_child_error)
        return self.raise_with_self(*args, **kwargs)

    def raise_invalid_type(self, *args, **kwargs):
        # ABCMeta is causing some problems, so instead we will (at least temporarily) assert that
        # the methods/properties are defined.
        assert hasattr(self, 'invalid_child_type_error')
        kwargs.setdefault('cls', self.invalid_child_type_error)
        return self.raise_invalid(*args, **kwargs)

    # def raise_cannot_reconfigure(self, *args, **kwargs):
    #     kwargs['cls'] = self.cannot_reconfigure_error
    #     kwargs.setdefault('field', self.field)
    #     return self.raise_invalid(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        # ABCMeta is causing some problems, so instead we will (at least temporarily) assert that
        # the methods/properties are defined.
        assert hasattr(self, 'required_child_error')
        kwargs.setdefault('cls', self.required_child_error)
        return self.raise_invalid(*args, **kwargs)

    @property
    def parent(self):
        # TODO: What should we do if the parent is changed (i.e. the parent is set)?  Do we have
        # to trigger some sort of reconfiguration?  Right now we don't allow it, but we might...
        if self._parent is None:
            raise PickyOptionsError(
                "The %s instance has not been assigned a parent yet." % self.__class__.__name__)
        return self._parent

    def validate_parent(self, parent):
        # ABCMeta is causing some problems, so instead we will (at least temporarily) assert that
        # the methods/properties are defined.
        assert hasattr(self, 'parent_cls')
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
            raise ValueError("Invalid parent")

    def remove_parent(self):
        if not self.assigned:
            # TODO: Cleanup with more detailed exception.
            raise PickyOptionsError()
        self._parent = None
        self._assigned = False

    def assign_parent(self, parent):
        from .parent import Parent
        # assert self.initialized

        # The parent can be arbitrary, but it will only assign self as a child of the parent
        # if the parent is an instance of Parent.
        self.validate_parent(parent)

        # TODO: Cleanup with more detailed exception.
        # TODO: Do we even want to raise this?
        if self.assigned:
            raise PickyOptionsError("The child already has a parent.")

        self._parent = parent

        # The parent can be arbitrary, but it will only assign self as a child of the parent
        # if the parent is an instance of Parent.
        # If the child is not of the parent's child class type, we don't add as a child - but the
        # child still receives the parent as a parent.
        if isinstance(parent, Parent) and isinstance(self, parent.child_cls):
            if not parent.has_child(self):
                parent.assign_child(self)
            else:
                logger.debug("Already has child.")

        self._assigned = True

    @property
    def assigned(self):
        return self._assigned
