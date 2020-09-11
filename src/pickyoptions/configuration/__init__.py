import logging
import six

from pickyoptions.lib.utils import get_num_function_arguments, ensure_iterable

from pickyoptions import constants, settings
from pickyoptions.utils import accumulate_errors
from pickyoptions.child import Child
from pickyoptions.configurable import SimpleConfigurable

from .exceptions import (
    ConfigurationError,
    ConfigurationInvalidError,
    ConfigurationRequiredError,
    ConfigurationTypeError,
    ConfigurationCannotReconfigureError,
    ConfigurationNotSetError,
    ConfigurationNotConfiguredError,
    ConfigurationConfiguringError
)


logger = logging.getLogger(settings.PACKAGE_NAME)


# TODO: Consider using Configuration recursively...
class Configuration(Child, SimpleConfigurable):

    # Child Implementation Properties
    invalid_child_error = ConfigurationInvalidError
    invalid_child_type_error = ConfigurationTypeError
    required_child_error = ConfigurationRequiredError
    child_not_set_error = ConfigurationNotSetError
    parent_cls = 'Configurations'
    child_identifier = 'field'

    # SimpleConfigurable Implementation Properties
    cannot_reconfigure_error = ConfigurationCannotReconfigureError
    not_configured_error = ConfigurationNotConfiguredError
    configuring_error = ConfigurationConfiguringError

    def __init__(self, field, **kwargs):
        Child.__init__(self, parent=kwargs.get('parent'))

        # TODO: Might be able to be conglomerated into the common child class.
        self._value = constants.NOTSET
        self._set = False
        self._defaulted = constants.NOTSET

        self._field = field
        self._default = kwargs.get('default', constants.NOTSET)
        self._types = kwargs.get('types')
        self._required = kwargs.get('required', False)
        self._validate = kwargs.get('validate')
        self._normalize = kwargs.get('normalize')
        self._updatable = kwargs.get('updatable')

        SimpleConfigurable.__init__(self)
        self.validate_configuration()

    def __repr__(self):
        if self.configured:
            return "<{cls_name} field={field} value={value}>".format(
                cls_name=self.__class__.__name__,
                field=self.field,
                value=self.value,
            )
        return "<{state} {cls_name} field={field}>".format(
            cls_name=self.__class__.__name__,
            field=self.field,
            state=self.state,
        )

    @property
    def set(self):
        return self._set

    def assert_set(self, *args, **kwargs):
        if not self.set:
            raise ValueError()

    @property
    def field(self):
        return self._field

    @property
    def updatable(self):
        return self._updatable

    @property
    def required(self):
        return self._required

    @property
    def types(self):
        iterable = ensure_iterable(self._types)
        if len(iterable) != 0:
            return iterable
        return None

    # This is only applicable to the Configuration, not the Option
    # (whose default is a configuration).
    @property
    def default(self):
        self.assert_set()
        return self._default

    @property
    def default_provided(self):
        return self._default != constants.NOTSET

    # TODO: Might be able to be conglomerated into the common child class.
    @property
    def defaulted(self):
        # Are we even updating the _set value right now?
        self.assert_set()
        if self._default != constants.NOTSET:
            return self._defaulted
        else:
            assert self._defaulted is False
            return False

    @property
    def value(self):
        # NOTE: The `obj:Configuration` may or may not be configured at this
        # point, because if the configuration is not present in the provided data
        # it is not technically considered configured.
        self.assert_set()

        if self._value is None:
            assert not self.required
            # assert self.allow_null
            return self.normalize(self.default)
        return self.normalize(self._value)

    @value.setter
    def value(self, value):
        self._value = value
        self._set = True
        self.validate()  # TODO: Should we also validate the default values?

    def configure(self, value):
        # We must set the configured state before validating because validation
        # will access the `value` property.
        with self.configuration_routine():
            self.value = value

    def normalize(self, value):
        if self._normalize is not None:
            return self._normalize(value)
        return value

    def validate(self):
        """
        Validates the `obj:Configuration` after the value is supplied.

        TODO:
        ----
        (1) Should we maybe add a property that validates the type of value
            provided if it is not `None`?  This would allow us to have a
            non-required value type checked if it is provided.  This would be a
            useful configuration for the `obj:Option` and `obj:Options`.
        """
        # TODO: Should we also validate the normalize or the defaulted values?
        # TODO: If the default is specified, should we ignore the requirement?
        self.assert_set()

        # TODO: Should this be checking against `self.value`?
        if self._value is None:
            if self.required:
                assert self.default is None
                assert not self.defaulted
                self.raise_required()

        if self.types is not None:
            # It should have already been validated in the validate_configuration
            # method that the default is of the specified types.
            assert self.default is not None
            assert isinstance(self.default, self.types)
            if not isinstance(self.value, self.types):
                self.raise_invalid_type()

        if self._validate is not None:
            # The default value is already validated against the method in the
            # validate_configuration method.
            self._validate(self._value, self)

    @accumulate_errors(error_cls=ConfigurationError)
    def validate_configuration(self):
        """
        Validates the parameters of the `obj:Configuration` configuration.

        This validation is independent of any value that would be set on the
        `obj:Configuration`, so it runs after initialiation.

        This validation is primarily for internal purposes and is meant to
        ensure that the `obj:Configuration`(s) are defined properly in the
        `obj:Option` and `obj:Options`.

        TODO:
        ----
        (1) Should we maybe add a property that validates the type of value
            provided if it is not `None`?  This would allow us to have a
            non-required value type checked if it is provided.  This would be a
            useful configuration for the `obj:Option` and `obj:Options`.
        """
        # TODO: Make the use of the Configuration classes here more flexible -
        # or even recursively use Configuration.
        from pickyoptions.configuration.configurations import (
            CallableConfiguration, EnforceTypesConfiguration)

        # What about reconfiguration?
        assert self.configured is False

        if not isinstance(self._required, bool):
            yield self.raise_invalid(
                message=(
                    "The `required` parameter for configuration `{field}` "
                    "must be a boolean."
                ),
                return_exception=True
            )

        # NOTE: This is causing recusion issues... around validate_configuration,
        # we need to figure out a way to fix this so the configurations can
        # be used recursively.
        # Validate that the optionally provided `validate` method is of the
        # correct signature.
        # configuration = CallableConfiguration(
        #     'validate',
        #     num_arguments=2,
        #     error_message=(
        #         "Must be a callable that takes the value of the configuration "
        #         "as it's first and only argument"
        #     )
        # )
        # configuration.value = self._validate  # Causes validation to occur
        #
        # configuration = EnforceTypesConfiguration('types')
        # configuration.value = self._types  # Causes validation to occur

        # Validate that the default is either set or not set properly based on
        # the requirement parameter.
        # TOOD: Use the base Configuration class here and specify types.
        if self._required is True:
            # This accounts for cases when the default value is not None or is
            # explicitly set as None.
            if self.default_provided:
                yield self.raise_invalid(
                    return_exception=True,
                    message=(
                        "Cannot provide a default value for configuration "
                        "`{field}` because the configuration is required."
                    )
                )
        else:
            if not self.default_provided:
                # We don't want to raise invalid here, just indicate that the
                # default value of `None` will be used.
                logger.warning(
                    "The configuration for `%s` is not required and no default "
                    "value is specified. The default value will be `None`."
                    % self.field
                )

        # Validate that if the configuration has a default value, that the default
        # value also  passes the validation - this also applies when the default
        # value is None.
        if self._validate is not None:
            # TODO: FIX THE DEFAULT REFERENCE HERE - We have to worry about both
            # the user set default and the default default (if the user set
            # default is not provided).
            try:
                self._validate(self._default)
            # Allow other exceptions to propogate because those are either valid
            # errors or represent inproper usage of the `validate` parameter.
            except ConfigurationInvalidError:
                yield self.raise_invalid(
                    return_exception=True,
                    message="The configuration default value {value} is invalid.",
                    value=self.default
                )

        # If the types are specified and the default value is not specified, the
        # value of `None` will not be of the required types.
        # TODO: Allow a setting that validates the value only if it is not None.
        if self._types is not None:
            default = self._default if self.default_provided else None
            if default is None or not isinstance(default, self._types):
                yield self.raise_invalid(
                    return_exception=True,
                    message="The default value is not of type %s." % self.types,
                    value=self.default
                )
