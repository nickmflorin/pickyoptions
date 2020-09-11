import six

from pickyoptions.lib.utils import get_num_function_arguments
from . import Configuration


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

    def validate(self):
        super(CallableConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value):
                self.raise_invalid(self.error_message)
            elif self.num_arguments is not None:
                num_found_arguments = get_num_function_arguments(self.value)
                if num_found_arguments != self.num_arguments:
                    self.raise_invalid(self.error_message)


class FieldConfiguration(Configuration):
    def __init__(self, field):
        super(FieldConfiguration, self).__init__(field, required=True,
            updatable=False)

    def validate(self):
        super(FieldConfiguration, self).validate()
        if not isinstance(self.value, six.string_types):
            self.raise_invalid_type(types=six.string_types)
        elif self.value.startswith('_'):
            self.raise_invalid(
                message="Cannot be scoped as a private attribute.")


class EnforceTypesConfiguration(Configuration):
    def __init__(self, field):
        super(EnforceTypesConfiguration, self).__init__(field, default=None)

    def normalize(self, value):
        if hasattr(value, '__iter__') and len(value) == 0:
            return None
        return value

    def validate(self):
        super(EnforceTypesConfiguration, self).validate()
        if self.value is not None:
            if not hasattr(self.value, '__iter__'):
                self.raise_invalid(message="Must be an iterable of types.")
            for tp in self.value:
                if not isinstance(tp, type):
                    self.raise_invalid(message="Must be an iterable of types.")

    def conforms_to(self, value):
        """
        Checks whether or not the provided value conforms to the types
        specified by this configuration.
        """
        if self.value is not None:
            assert type(self.value) is tuple
            if value is None or not isinstance(value, self.value):
                return False
        return True
