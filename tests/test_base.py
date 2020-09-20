import pytest

from pickyoptions.core.base import Base
from pickyoptions.core.exceptions import PickyOptionsError


def test_abstract_properties_inherit():
    class TestGrandParent(Base):
        __abstract__ = True
        abstract_properties = ('foo', 'bar')

    class TestParent(TestGrandParent):
        __abstract__ = True
        abstract_properties = ('fooey', 'barrey')

    class TestChild(TestParent):
        __abstract__ = False

    assert TestChild.abstract_properties == ('foo', 'bar', 'fooey', 'barrey')

    # We shouldn't be able to initialize an instance because it is missing
    # required properties.
    with pytest.raises(TypeError):
        TestChild()

    class TestChild(TestParent):
        __abstract__ = False
        foo = 'foo'
        bar = 'bar'
        fooey = 'fooey'
        barrey = 'barrey'

    # Now that required properties are present, we should be able to instantiate.
    TestChild()


def test_error_mappings_merge():
    class Parent1(Base):
        errors = {
            'foo_error': AttributeError,
            'bar_error': ValueError
        }

    class Parent2(Base):
        errors = {}

    class Parent3(Base):
        errors = {
            'fooey_error': PickyOptionsError,
            'bar_error': TypeError
        }

    class Parent4(Base):
        pass

    class Child(Parent1, Parent2, Parent3, Parent4):
        errors = {
            'child_error': KeyError
        }

    assert Child.errors == {
        'child_error': KeyError,
        'foo_error': AttributeError,
        'bar_error': TypeError,
        'fooey_error': PickyOptionsError
    }
    child = Child()
    assert child.errors == {
        'child_error': KeyError,
        'foo_error': AttributeError,
        'bar_error': TypeError,
        'fooey_error': PickyOptionsError
    }


def test_required_errors_merge():
    class Parent1(Base):
        required_errors = ('foo', 'bar')
        errors = {'foo': ValueError, 'bar': AssertionError}

    class Parent2(Parent1):
        pass

    class Parent3(Parent1):
        required_errors = ('apple', 'banana', 'bar')
        errors = {'apple': TypeError, 'banana': AttributeError}

    class Parent4(Parent3):
        required_errors = ('apple', )

    class Child1(Parent2):
        pass

    class Child2(Parent2, Parent4):
        pass

    assert Child1.required_errors == Parent2.required_errors == ('foo', 'bar')
    assert set(Child2.required_errors) == set(('apple', 'banana', 'bar', 'foo'))
