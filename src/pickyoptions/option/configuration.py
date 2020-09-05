import six

from pickyoptions.lib.utils import check_num_function_arguments
from pickyoptions.configuration.configuration import Configuration

from .exceptions import OptionConfigurationError


class OptionConfiguration(Configuration):
    exception_cls = OptionConfigurationError


class PostProcessorConfiguration(OptionConfiguration):
    def __init__(self, field):
        super(PostProcessorConfiguration, self).__init__(field, required=False, default=None)

    def validate(self, value):
        super(PostProcessorConfiguration, self).validate(value)
        if value is not None:
            if not six.callable(value) or not check_num_function_arguments(value, 3):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument, the option instance as it's second argument and the overall "
                    "combined options instance as it's third argument."
                )


class ValidateConfiguration(OptionConfiguration):
    def __init__(self, field):
        super(ValidateConfiguration, self).__init__(field, required=False, default=None)

    def validate(self, value):
        super(ValidateConfiguration, self).validate(value)
        if value is not None:
            if not six.callable(value) or not check_num_function_arguments(value, 3):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument, the option instance as it's second argument and the overall "
                    "combined options instance as it's third argument."
                )


class ValidateWithOthersConfiguration(OptionConfiguration):
    def __init__(self, field):
        super(ValidateWithOthersConfiguration, self).__init__(field, required=False, default=None)

    def validate(self, value):
        super(ValidateWithOthersConfiguration, self).validate(value)
        if value is not None:
            if not six.callable(value) or not check_num_function_arguments(value, 3):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument, the option instance as it's second argument and the overall "
                    "combined options instance as it's third argument."
                )


class NormalizeConfiguration(OptionConfiguration):
    def __init__(self, field):
        super(NormalizeConfiguration, self).__init__(field, required=False, default=None)

    def validate(self, value):
        super(NormalizeConfiguration, self).validate(value)
        if value is not None:
            # TODO: Should we allow normalize to have options as the third parameter?  We could
            # always introspect the function and pass in if applicable.
            if not six.callable(value) or not check_num_function_arguments(value, 2):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument and the option instance as it's second argument."
                )


class DisplayConfiguration(OptionConfiguration):
    exception_cls = OptionConfigurationError

    def __init__(self, field):
        super(DisplayConfiguration, self).__init__(field, required=False, default=None)

    def validate(self, value):
        super(DisplayConfiguration, self).validate(value)
        if value is not None:
            if not six.callable(value) or not check_num_function_arguments(value, 1):
                self.raise_invalid(
                    "Must be a callable that takes the option instance as it's first "
                    "and only argument."
                )
