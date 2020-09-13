from pickyoptions.lib.utils import extends_or_instance_of


class TestUncle(object):
    pass


class TestMother(object):
    pass


class TestFather(object):
    pass


class TestChild(TestMother, TestFather):
    pass


def test_instance_of_class_as_class():
    extends = extends_or_instance_of(TestChild, TestChild)
    assert extends is True

    child = TestChild()
    extends = extends_or_instance_of(child, TestChild)
    assert extends is True


def test_instance_of_class_as_string():
    extends = extends_or_instance_of(TestChild, "TestChild")
    assert extends is True

    child = TestChild()
    extends = extends_or_instance_of(child, "TestChild")
    assert extends is True


def test_instance_of_class_as_instance():
    child = TestChild()
    extends = extends_or_instance_of(TestChild, child)
    assert extends is True

    extends = extends_or_instance_of(child, child)
    assert extends is True


def test_extends_class_as_class():
    extends = extends_or_instance_of(TestChild, TestMother)
    assert extends is True

    child = TestChild()
    extends = extends_or_instance_of(child, TestFather)
    assert extends is True

    extends = extends_or_instance_of(TestChild, TestUncle)
    assert extends is False


def test_extends_class_as_string():
    extends = extends_or_instance_of(TestChild, "TestMother")
    assert extends is True

    child = TestChild()
    extends = extends_or_instance_of(child, "TestFather")
    assert extends is True

    extends = extends_or_instance_of(child, 'TestUncle')
    assert extends is False


def test_extends_class_as_instance():
    mother = TestMother()
    extends = extends_or_instance_of(TestChild, mother)
    assert extends is True

    child = TestChild()
    extends = extends_or_instance_of(child, mother)
    assert extends is True

    father = TestFather()
    extends = extends_or_instance_of(TestChild, father)
    assert extends is True

    child = TestChild()
    extends = extends_or_instance_of(child, father)
    assert extends is True

    uncle = TestUncle()
    extends = extends_or_instance_of(TestChild, uncle)
    assert extends is False

    child = TestChild()
    extends = extends_or_instance_of(child, uncle)
    assert extends is False


# TODO: Parameterize this test!
def test_extends_class_iterable():
    mother = TestMother()
    child = TestChild()
    father = TestFather()
    uncle = TestUncle()

    extends = extends_or_instance_of(child, (mother, father))
    assert extends is True

    extends = extends_or_instance_of(child, (mother, uncle))
    assert extends is True

    extends = extends_or_instance_of(child, (uncle,))
    assert extends is False

    extends = extends_or_instance_of(child, ("TestMother", father))
    assert extends is True

    extends = extends_or_instance_of(child, (TestMother, uncle))
    assert extends is True

    extends = extends_or_instance_of(child, (TestUncle,))
    assert extends is False
