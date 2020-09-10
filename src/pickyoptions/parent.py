from abc import ABCMeta, abstractproperty
import logging
import six
import sys

from pickyoptions import settings
from pickyoptions.base import BaseModel
from pickyoptions.child import Child
from pickyoptions.exceptions import PickyOptionsError, ObjectTypeError


logger = logging.getLogger(settings.PACKAGE_NAME)


class Parent(six.with_metaclass(ABCMeta, BaseModel)):
    """
    Mapping model.
    """
    def __init__(self, children=None, child_value=None):
        self._children = []
        self._child_value = child_value

        children = children or []
        for child in children:
            self.assign_child(child)

    @abstractproperty
    def child_cls(self):
        pass

    @abstractproperty
    def unrecognized_child_error(self):
        pass

    def __getattr__(self, k):
        # TODO: Do we really want this to raise an error indicating that the option is not
        # recognized instead of an actual attribute error?
        try:
            child = self.get_child(k)
        except self.unrecognized_child_error:
            if settings.DEBUG:
                # TODO: Set the original traceback if we can.
                raise AttributeError("The attribute %s does not exist." % k)
            six.reraise(*sys.exc_info())
        # We cannot decorate this with requires_populated because it will disguise
        # actual attribute errors.  Instead, we raise the populating error only if the option
        # exists.
        return self.child_value(child)

    def __getitem__(self, k):
        return self.__getattr__(k)

    def get(self, k):
        try:
            return getattr(self, k)
        # Attribute error gets raised in DEBUG mode.
        except (self.unrecognized_child_error, AttributeError):
            return None

    @property
    def children(self):
        return self._children

    def has_child(self, child):
        # TODO: Should we maybe check if the entire object is in the children, instead of just
        # checking against an identifier value?
        identifier = child
        if not isinstance(child, six.string_types):
            self.validate_child(child)
            identifier = getattr(child, self.child_identifier)
        return identifier in self.identifiers

    def raise_if_child_missing(self, child):
        if not self.has_child(child):
            self.raise_no_child(field=(
                child if isinstance(child, six.string_types)
                else getattr(child, self.child_identifier)
            ))

    # TODO: Maybe we want to prevent this, or only allow it in certain circumstances.  Either way,
    # it shouldn't be blanket allowed for the ParentModel...  We should add some restriction to how
    # children are added/set.  For the `obj:Options` case, this is very important.
    @children.setter
    def children(self, children):
        logger.debug("Replace n children")
        self.remove_children()
        self.add_children(children)

    def validate_child(self, child):
        # ABCMeta is causing some problems, so instead we will (at least temporarily) assert that
        # the methods/properties are defined.
        assert hasattr(self, 'child_cls')
        if not isinstance(child, Child):
            raise ObjectTypeError(
                value=child,
                message="The child must be an extension of %s." % Child.__class__.__name__,
                types=Child
            )
        elif isinstance(self.child_cls, six.string_types):
            if child.__class__.__name__ != self.child_cls:
                raise ObjectTypeError(
                    value=child,
                    message="The child must be of type `{types}`.",
                    types=self.child_cls,
                )
        elif hasattr(self.child_cls, '__iter__'):
            assert all([isinstance(v, six.string_types) for v in self.child_cls])
            if child.__class__.__name__ not in self.child_cls:
                raise ObjectTypeError(
                    value=child,
                    message="The child must be of type `{types}`.",
                    types=self.child_cls
                )
        elif isinstance(self.child_cls, type):
            if not isinstance(child, self.child_cls):
                raise ObjectTypeError(
                    value=child,
                    message="The child must be of type `{types}`.",
                    types=type(self.child_cls),
                )
        else:
            raise ValueError("Invalid Child")

    def child_value(self, child):
        if self._child_value is None:
            return child
        return self._child_value(child)

    @property
    def identifiers(self):
        return [getattr(child, self.child_identifier) for child in self.children]

    def keys(self):
        return self.identifiers

    def values(self):
        return [self.child_value(child) for child in self.children]

    def __iter__(self):
        for child in self.children:
            yield child.identifier, self.child_value(child)

    def __len__(self):
        return len(self.children)

    @property
    def zipped(self):
        return [(field, value) for field, value in self]

    def raise_no_child(self, *args, **kwargs):
        assert hasattr(self, 'unrecognized_child_error')
        kwargs.setdefault('cls', self.unrecognized_child_error)
        self.raise_with_self(*args, **kwargs)

    def get_child(self, identifier):
        try:
            return [child for child in self.children if child.identifier == identifier][0]
        except IndexError:
            if settings.DEBUG:
                # TODO: Set the original traceback if we can.
                raise AttributeError("The attribute `%s` does not exist on the %s instance." % (
                    identifier, self.__class__.__name__))
            self.raise_no_child(field=identifier)

    def new_children(self, children):
        self.remove_children()
        assert len(self.children) == 0
        self.add_children(children)

    def remove_child(self, child):
        if child.parent != self:
            raise ValueError()
        if not self.has_child(child):
            raise ValueError()
        self._children.remove(child)

    def assign_child(self, child):
        # TODO: Should we deepcopy the child?
        self.validate_child(child)
        if self.has_child(child):
            # TODO: Cleanup with more detailed exception.
            raise PickyOptionsError("The parent already has the child.")

        # This must come first to prevent a recursion error between parent/child.
        self._children.append(child)
        if not child.assigned:
            child.assign_parent(self)
        else:
            pass
            # TODO: Cleanup with more detailed exception.
            # TODO: Not sure if we want to keep this check or not, but right now it is causing
            # problems...
            # if child.parent != self:
            #     logger.warning("SHOULD THIS BE HAPPENING?")
            #     import ipdb; ipdb.set_trace()
            #     raise PickyOptionsError()

    def remove_children(self, children=None):
        children = children or self.children
        for child in children:
            self.remove_child(child)

    def add_children(self, children):
        for child in children:
            self.assign_child(child)
