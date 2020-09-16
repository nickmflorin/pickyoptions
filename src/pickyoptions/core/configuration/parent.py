import logging
import six

from pickyoptions import settings
from pickyoptions.lib.utils import extends_or_instance_of

from pickyoptions.core.base import Base
from pickyoptions.core.exceptions import DoesNotExistError, ValueTypeError

from .child import Child
from .exceptions import ParentHasChildError


logger = logging.getLogger(settings.PACKAGE_NAME)


class Parent(Base):
    __abstract__ = True

    does_not_exist_error = DoesNotExistError
    abstract_properties = ('child_cls', )

    def __init__(self, children=None, child_value=None):
        super(Parent, self).__init__()

        self._children = []
        self._child_value = child_value

        children = children or []
        for child in children:
            self.assign_child(child)

    def __getattr__(self, k):
        child = self.get_child(k)
        return self.child_value(child)

    def __getitem__(self, k):
        return self.__getattr__(k)

    @property
    def children(self):
        return self._children

    def has_child(self, child):
        # TODO: Should we maybe check if the entire object is in the children,
        # instead of just checking against an identifier value?
        field = child
        if not isinstance(child, six.string_types):
            self.validate_child(child)
            field = child.field
        return field in self.fields

    def raise_if_child_missing(self, child):
        if not self.has_child(child):
            self.raise_no_child(name=(
                child if isinstance(child, six.string_types)
                else child.field
            ))

    # TODO: Maybe we want to prevent this, or only allow it in certain
    # circumstances.  Either way, it shouldn't be blanket allowed for the
    # ParentModel...  We should add some restriction to how children are added/set
    # For the `obj:Options` case, this is very important.
    @children.setter
    def children(self, children):
        logger.debug("Replace n children")
        self.remove_children()
        self.add_children(children)

    def validate_child(self, child):
        assert isinstance(child, Child)
        if not extends_or_instance_of(child, self.child_cls):
            # TODO: Come up with a better error.
            raise ValueTypeError(
                value=child,
                message="The child must be of type `{types}`.",
                types=self.child_cls,
            )

    def child_value(self, child):
        if self._child_value is None:
            return child
        return self._child_value(child)

    @property
    def fields(self):
        return [child.field for child in self.children]

    def keys(self):
        return self.fields

    def values(self):
        return [self.child_value(child) for child in self.children]

    def __iter__(self):
        for child in self.children:
            yield child.field, self.child_value(child)

    def __len__(self):
        return len(self.children)

    @property
    def zipped(self):
        return [(field, value) for field, value in self]

    def raise_child_does_not_exist(self, *args, **kwargs):
        kwargs['cls'] = self.does_not_exist_error
        super(Parent, self).raise_with_self(self, *args, **kwargs)

    def get_child(self, field):
        try:
            return [
                child for child in self.children
                if child.field == field
            ][0]
        except IndexError:
            self.raise_child_does_not_exist(name=field)

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
            raise ParentHasChildError()

        # This must come first to prevent a recursion error between parent/child.
        self._children.append(child)
        if not child.assigned:
            child.assign_parent(self)
        else:
            pass
            # TODO: Cleanup with more detailed exception.
            # TODO: Not sure if we want to keep this check or not, but right now
            # it is causing problems...
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
