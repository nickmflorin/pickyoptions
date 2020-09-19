import six

from pickyoptions import constants

from pickyoptions.lib.utils import get_num_function_arguments
from pickyoptions.core.decorators import accumulate_errors

from .configuration import Configuration


class CallableConfiguration(Configuration):
    def __init__(self, field, num_arguments=None, error_message=None):
        super(CallableConfiguration, self).__init__(field, required=False,
            default=None)
        self._num_arguments = num_arguments
        self._error_message = error_message or "Must be a callable."

    @property
    def num_arguments(self):
        return self._num_arguments

    @property
    def error_message(self):
        default_message = "Must be a callable."
        if self.num_arguments is not None:
            default_message = (
                "Must be a callable that takes %s arguments."
                % self.num_arguments
            )
        return self._error_message or default_message

    @accumulate_errors(error_cls='validation_error')
    def do_validate_value(self, value, **kwargs):
        yield super(CallableConfiguration, self).do_validate_value(value,
            return_children=True)
        if value is not None and value != constants.EMPTY:
            if not six.callable(value):
                yield self.raise_invalid(
                    message=self.error_message,
                    return_exception=True,
                )
            elif self.num_arguments is not None:
                num_found_arguments = get_num_function_arguments(value)
                if num_found_arguments != self.num_arguments:
                    yield self.raise_invalid(
                        message=self.error_message,
                        return_exception=True,
                    )


class TypesConfiguration(Configuration):
    def __init__(self, field):
        super(TypesConfiguration, self).__init__(field, default=None)

    def normalize(self, value):
        if hasattr(value, '__iter__') and len(value) == 0:
            return None
        return value

    @accumulate_errors(error_cls='validation_error')
    def do_validate_value(self, value, detail=None):
        yield super(TypesConfiguration, self).do_validate_value(value,
            return_children=True, detail=detail)
        if value is not None and value != constants.EMPTY:
            if (not hasattr(value, '__iter__')
                    or isinstance(value, six.string_types)):
                yield self.raise_invalid(
                    message="The configuration {name} be an iterable of types.",
                    return_exception=True,
                    detail=detail,
                    value=value,
                )
            else:
                if any([not isinstance(tp, type) for tp in value]):
                    yield self.raise_invalid(
                        message=(
                            "The configuration {name} be an iterable of types."
                        ),
                        return_exception=True,
                        detail=detail,
                        value=value,
                    )

    def conforms_to(self, value):
        """
        Checks whether or not the provided value conforms to the types
        specified by this configuration.
        """
        self.assert_set()
        if self.provided and self.value is not None:
            assert type(self.value) is tuple
            if value is None or not isinstance(value, self.value):
                return False
        return True
