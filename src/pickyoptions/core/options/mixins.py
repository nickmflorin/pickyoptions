from pickyoptions.core.decorators import raise_with_error
from pickyoptions.core.base import BaseMixin


class PopulatingMixin(BaseMixin):
    """
    Requires that the class instance has a routine with id populating.
    """
    required_errors = (
        'not_populated_error',
        'not_populated_populating_error',
        'populated_error',
    )

    def assert_not_populated(self, *args, **kwargs):
        if self.populated:
            self.raise_populated(*args, **kwargs)

    def assert_populated(self, *args, **kwargs):
        if not self.populated:
            self.raise_not_populated(*args, **kwargs)

    def assert_populated_or_populating(self, *args, **kwargs):
        if not self.populated:
            self.raise_not_populated(*args, **kwargs)

    @raise_with_error(error='not_populated_error')
    def raise_not_populated(self, *args, **kwargs):
        assert not self.populated
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='populated_error')
    def raise_populated(self, *args, **kwargs):
        assert self.populated
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error='not_populated_populating_error')
    def raise_not_populated_or_populating(self, *args, **kwargs):
        assert not self.populated or not self.populating
        return self.raise_with_self(*args, **kwargs)

    @property
    def populated(self):
        return self.routines.populating.finished

    @property
    def populating(self):
        return self.routines.populating.in_progress
