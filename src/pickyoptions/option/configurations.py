import six

from pickyoptions.lib.utils import check_num_function_arguments
from pickyoptions.configuration import Configuration


class PostProcessConfiguration(Configuration):
    def __init__(self, field):
        super(PostProcessConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(PostProcessConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 2):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument and the option instance as it's second argument."
                )


class PostProcessWithOptionsConfiguration(Configuration):
    def __init__(self, field):
        super(PostProcessWithOptionsConfiguration, self).__init__(field, default=None)

    def validate(self):
        super(PostProcessWithOptionsConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 3):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument, the option instance as it's second argument and the overall "
                    "combined options instance as it's third argument."
                )


class ValidateConfiguration(Configuration):
    def __init__(self, field):
        super(ValidateConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(ValidateConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 2):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument and the option instance as it's second argument."
                )


class ValidateWithOptionsConfiguration(Configuration):
    def __init__(self, field):
        super(ValidateWithOptionsConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(ValidateWithOptionsConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 3):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument, the option instance as it's second argument and the overall "
                    "combined options instance as it's third argument."
                )


class NormalizeConfiguration(Configuration):
    def __init__(self, field):
        super(NormalizeConfiguration, self).__init__(field, default=None)

    def validate(self):
        super(NormalizeConfiguration, self).validate()
        if self.value is not None:
            # TODO: Should we allow normalize to have options as the third parameter?  We could
            # always introspect the function and pass in if applicable.
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 2):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument and the option instance as it's second argument."
                )


class FieldConfiguration(Configuration):
    def __init__(self, field):
        super(FieldConfiguration, self).__init__(field, required=True, updatable=False)

    def validate(self):
        super(FieldConfiguration, self).validate()
        if not isinstance(self.value, six.string_types):
            self.raise_invalid_type(types=six.string_types)
        elif self.value.startswith('_'):
            self.raise_invalid(message="Cannot be scoped as a private attribute.")
