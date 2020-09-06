import six

from pickyoptions.configuration import ConfigurableModel, Configuration
from pickyoptions.configuration.exceptions import ConfigurationTypeError, ConfigurationInvalidError
from pickyoptions.configuration.utils import configurable_property, configurable_property_setter

from .configurations import (
    ValidateConfiguration, ValidateWithOthersConfiguration,
    NormalizeConfiguration, DisplayConfiguration,
    PostProcessConfiguration, PostProcessWithSiblingsConfiguration)


class OptionConfiguration(ConfigurableModel):
    configurations = (
        Configuration('default', default=None),
        Configuration('required', types=(bool, ), default=False),
        Configuration('required_not_null', types=(bool, ), default=False),
        # TODO: The allow_null property might cause issues with the default value if the default
        # is None.  We should handle that more appropriately, or make the default value conditional
        # on the other configurations.
        Configuration('allow_null', types=(bool, ), default=True),
        Configuration('enforce_type', default=None),  # TODO: Add restriction
        ValidateConfiguration('validator'),
        ValidateWithOthersConfiguration('validator_with_others'),
        # TODO: validate_after_normalization
        NormalizeConfiguration('normalizer'),
        PostProcessConfiguration('post_process'),
        PostProcessWithSiblingsConfiguration('post_process_with_siblings'),
        DisplayConfiguration('displayer'),
        Configuration("help_text", default="", types=six.string_types)
    )

    def validate_configuration(self):
        super(OptionConfiguration, self).validate_configuration()

        # We cannot use a validator for the field configuration since it is treated differently
        # from the other configuration parameters, since it is provided in the *args.
        if not isinstance(self.field, six.string_types):
            raise ConfigurationTypeError(
                field="field",
                types=six.string_types
            )
        elif self.field.startswith('_'):
            raise ConfigurationInvalidError(
                field="field",
                message="The configuration `{field}` cannot be scoped as a private attribute."
            )
        elif self.default is not None and self.enforce_type is not None:
            if not isinstance(self.default, self.enforce_type):
                raise ConfigurationTypeError(
                    field='default',
                    types=self.enforce_type,
                    message=(
                        "If enforcing that the option be of type {types}, the default value "
                        "must also be of type {types}."
                    )
                )
        # Do we have to worry about this anymore?
        # if self.default is not None and self.required:
        #     # This should not happen, as a required option should not have a default.  We will
        #     # either raise an exception or log a warning.
        #     raise ValueError()

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
    def post_process(self):
        pass

    @configurable_property_setter(post_process)
    def post_process(self, value):
        pass

    @configurable_property
    def post_process_with_siblings(self):
        pass

    @configurable_property_setter(post_process_with_siblings)
    def post_process_with_siblings(self, value):
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
