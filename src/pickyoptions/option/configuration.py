import six

from pickyoptions.configuration import ConfigurableModel
from pickyoptions.configuration.utils import configurable_property, configurable_property_setter
from pickyoptions.exceptions import PickyOptionsError

from .configurations import (
    OptionConfiguration, ValidateConfiguration, PostProcessorConfiguration,
    ValidateWithOthersConfiguration, NormalizeConfiguration, DisplayConfiguration)
from .exceptions import OptionConfigurationError


class OptionConfiguration(ConfigurableModel):
    configurations = (
        OptionConfiguration('default'),
        OptionConfiguration('required', types=(bool, )),
        OptionConfiguration('required_not_null', types=(bool, )),
        OptionConfiguration('allow_null', types=(bool, )),
        OptionConfiguration('enforce_type'),  # TODO: Add restriction
        ValidateConfiguration('validator'),
        ValidateWithOthersConfiguration('validator_with_others'),
        NormalizeConfiguration('normalizer'),
        PostProcessorConfiguration('post_processor'),
        DisplayConfiguration('displayer'),
        OptionConfiguration("help_text", default="", types=six.string_types)
    )

    def validate_configuration(self):
        if not self.configured:
            raise PickyOptionsError("Must be configured.")

        if not isinstance(self.field, six.string_types):
            raise OptionConfigurationError(
                field="field",
                message="Must be of type %s." % type(str)
            )

        if self.default is not None and self.required:
            # This should not happen, as a required option should not have a default.  We will
            # either raise an exception or log a warning.
            raise ValueError()

        if self.default is not None and self.enforce_type is not None:
            if not isinstance(self.default, self.enforce_type):
                raise OptionConfigurationError(
                    field='default',
                    message=(
                        "If enforcing that the option be of a certain type, the default value "
                        "must also be of that type."
                    )
                )

    @configurable_property
    def default(self):
        pass

    @configurable_property_setter(default)
    def default(self, value):
        pass

    @configurable_property
    def required(self):
        pass

    @configurable_property_setter(required)
    def required(self, value):
        pass

    @configurable_property
    def required_not_null(self):
        pass

    @configurable_property_setter(required_not_null)
    def required_not_null(self, value):
        pass

    @configurable_property
    def allow_null(self):
        pass

    @configurable_property_setter(allow_null)
    def allow_null(self, value):
        pass

    @configurable_property
    def enforce_type(self):
        pass

    @configurable_property_setter(enforce_type)
    def enforce_type(self, value):
        pass

    @configurable_property
    def validator(self):
        pass

    @configurable_property_setter(validator)
    def validator(self, value):
        pass

    @configurable_property
    def validator_with_others(self):
        pass

    @configurable_property_setter(validator_with_others)
    def validator_with_others(self, value):
        pass

    @configurable_property
    def post_processor(self):
        pass

    @configurable_property_setter(post_processor)
    def post_processor(self, value):
        pass

    @configurable_property
    def normalizer(self):
        pass

    @configurable_property_setter(normalizer)
    def normalizer(self, value):
        pass

    @configurable_property
    def displayer(self):
        pass

    @configurable_property_setter(displayer)
    def displayer(self, value):
        pass

    @configurable_property
    def help_text(self):
        pass

    @configurable_property_setter(help_text)
    def help_text(self, value):
        pass
