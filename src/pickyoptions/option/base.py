import six
import sys

from pickyoptions.exceptions import PickyOptionsError
from pickyoptions.configuration.base import (
    ConfigurableModel, configurable_property, configurable_property_setter)

from .configuration import (
    OptionConfiguration, ValidateConfiguration, PostProcessorConfiguration,
    ValidateWithOthersConfiguration, NormalizeConfiguration, DisplayConfiguration)
from .exceptions import (OptionInvalidError, OptionConfigurationError, OptionRequiredError,
    OptionInstanceOfError)


class OptionConfiguration(ConfigurableModel):
    configurations = (
        OptionConfiguration('default'),
        OptionConfiguration('required', types=(bool, )),
        OptionConfiguration('required_not_null', types=(bool, )),
        OptionConfiguration('allow_null', types=(bool, )),
        OptionConfiguration('enforce_type'),  # TODO: Add restriction
        ValidateConfiguration('validate'),
        ValidateWithOthersConfiguration('validate_with_others'),
        NormalizeConfiguration('normalize'),
        PostProcessorConfiguration('post_process'),
        DisplayConfiguration('display'),
        OptionConfiguration("help_text", default="", types=six.string_types)
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
    def validate(self):
        pass

    @configurable_property_setter(validate)
    def validate(self, value):
        pass

    @configurable_property
    def validate_with_others(self):
        pass

    @configurable_property_setter(validate_with_others)
    def validate_with_others(self, value):
        pass

    @configurable_property
    def post_process(self):
        pass

    @configurable_property_setter(post_process)
    def post_process(self, value):
        pass

    @configurable_property
    def normalize(self):
        pass

    @configurable_property_setter(normalize)
    def normalize(self, value):
        pass

    @configurable_property
    def display(self):
        pass

    @configurable_property_setter(display)
    def display(self, value):
        pass

    @configurable_property
    def help_text(self):
        pass

    @configurable_property_setter(help_text)
    def help_text(self, value):
        pass


class Option(OptionConfiguration):
    def __init__(self, field, **kwargs):
        self._field = field
        if not isinstance(self.field, six.string_types):
            raise ValueError()
        super(Option, self).__init__(**kwargs)

    def __repr__(self):
        return "<{cls_name} field={field}>".format(
            cls_name=self.__class__.__name__,
            field=self.field,
        )

    def raise_invalid(self, *args, **kwargs):
        cls = kwargs.pop('cls', OptionInvalidError)
        kwargs['param'] = self.field
        raise cls(*args, **kwargs)

    @property
    def field(self):
        return self._field

    @property
    def display(self):
        if self._display:
            return self._display(self)
        return "%s: %s" % (self.field, self.help_text)

    def normalize_option(self, value):
        if self.normalize:
            return self.normalize(value, self)
        return value

    def post_process_option(self, value, options):
        if self.post_process:
            self.post_process(value, self, options)
        return value

    def validate_option_with_others(self, value, options):
        """
        Validates the `obj:Option` instance after all options have been set on the overall
        combined `obj:Options` instance.
        """
        if self.validate_with_others is not None:
            try:
                result = self._validate_with_others(value, self, options)
            except Exception as e:
                if isinstance(e, OptionInvalidError):
                    six.reraise(*sys.exc_info())
                else:
                    raise OptionConfigurationError(
                        field='validate',
                        message=(
                            "If raising an exception to indicate that the option is invalid, "
                            "the exception must be an instance of OptionInvalidError.  It is "
                            "recommended to use the `raise_invalid` method of the option instance."
                        )
                    )
            else:
                if result is not None:
                    if not isinstance(result, six.string_types):
                        raise OptionConfigurationError(
                            field='validate',
                            message=(
                                "The option validate method must return a string error "
                                "message or raise an instance of OptionInvalidError in the "
                                "case that the value is invalid.  If the value is valid, it "
                                "must return None."
                            )
                        )
                    self.raise_invalid(value=value, message=result)

    def validate_option(self, value, options):
        """
        Validates the `obj:Option` instance when it's corresponding value is being set on the
        `obj:Options`.
        """
        # TODO: Cleanup this required logic - there is also a required check in the parent options
        # that checks if the value was explicitly provided.
        if value is None:
            if self.required and not self.default:
                self.raise_invalid(cls=OptionRequiredError)
        else:
            if self.enforce_type is not None:
                if not isinstance(value, self.enforce_type):
                    self.raise_invalid(cls=OptionInstanceOfError, types=self.enforce_type)
            if self.validate is not None:
                # In the case that the option is invalid, validation method either returns a
                # string method or raises an OptionInvalidError (or an extension).
                try:
                    result = self._validate(value, self, options)
                except Exception as e:
                    if isinstance(e, OptionInvalidError):
                        six.reraise(*sys.exc_info())
                    else:
                        raise OptionConfigurationError(
                            field='validate',
                            message=(
                                "If raising an exception to indicate that the option is invalid, "
                                "the exception must be an instance of OptionInvalidError.  It is "
                                "recommended to use the `raise_invalid` method of the option "
                                "instance. "
                            )
                        )
                else:
                    if result is not None:
                        if not isinstance(result, six.string_types):
                            raise OptionConfigurationError(
                                field='validate',
                                message=(
                                    "The option validate method must return a string error "
                                    "message or raise an instance of OptionInvalidError in the "
                                    "case that the value is invalid.  If the value is valid, it "
                                    "must return None."
                                )
                            )
                        self.raise_invalid(value=value, message=result)

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
