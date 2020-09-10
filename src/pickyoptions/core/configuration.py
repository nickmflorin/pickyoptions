import logging
import six

from pickyoptions import constants, settings
from pickyoptions.lib.utils import check_num_function_arguments, ensure_iterable

from pickyoptions.exceptions import (
    ConfigurationInvalidError,
    ConfigurationRequiredError,
    ConfigurationTypeError,
    ConfigurationCannotReconfigureError
)
from .child import Child


logger = logging.getLogger(settings.PACKAGE_NAME)


class Configuration(Child):

    invalid_child_error = ConfigurationInvalidError
    invalid_child_type_error = ConfigurationTypeError
    child_required_error = ConfigurationRequiredError

    # TODO: Should we move this to the Child model?  As a cannot_update_error?
    cannot_reconfigure_error = ConfigurationCannotReconfigureError

    parent_cls = 'Configurations'
    child_identifier = 'field'

    def __init__(self, field, **kwargs):
        Child.__init__(self, parent=kwargs.get('parent'))

        self._value = None
        self._configured = False

        self._field = field
        self._default = kwargs.get('default', constants.NOTSET)
        self._types = kwargs.get('types')
        self._required = kwargs.get('required', False)
        self._validate = kwargs.get('validate')
        self._normalize = kwargs.get('normalize')
        self._updatable = kwargs.get('updatable')

        self.validate_configuration()

    def __repr__(self):
        if self.configured:
            return "<{cls_name} field={field} value={value}>".format(
                cls_name=self.__class__.__name__,
                field=self.field,
                value=self.value,
            )
        return "<{cls_name} field={field} value={value}>".format(
            cls_name=self.__class__.__name__,
            field=self.field,
            value="NOT_CONFIGURED",
        )

    @property
    def field(self):
        return self._field

    @property
    def updatable(self):
        return self._updatable

    @property
    def configured(self):
        return self._configured

    @property
    def default(self):
        if self._default == constants.NOTSET:
            return None
        return self._default

    @property
    def required(self):
        return self._required

    @property
    def types(self):
        iterable = ensure_iterable(self._types)
        if len(iterable) != 0:
            return iterable
        return None

    @property
    def default_set(self):
        return self._default != constants.NOTSET

    # def raise_cannot_reconfigure(self, *args, **kwargs):
    #     kwargs['cls'] = self.cannot_reconfigure_error
    #     kwargs.setdefault('field', self.field)
    #     return self.raise_invalid(*args, **kwargs)

    @property
    def value(self):
        # NOTE: The `obj:Configuration` may or may not be configured at this point, because if the
        # configuration is not present in the provided data it is not technically considered
        # configured.
        if self._value is None:
            assert not self.required
            # assert self.allow_null
            return self.normalize(self.default)
        return self.normalize(self._value)

    @value.setter
    def value(self, value):
        self._value = value
        self.validate()  # TODO: Should we also validate the default values?

    def configure(self, value):
        # We must set the configured state before validating because validation will access
        # the `value` property.
        self._configured = True
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
        (1) Should we maybe add a property that validates the type of value provided if it is
            not `None`?  This would allow us to have a non-required value type checked if it is
            provided.  This would be a useful configuration for the `obj:Option` and `obj:Options`.
        """
        # TODO: Should we also validate the normalize or the defaulted values?
        # TODO: If the default is specified, should we ignore the requirement?

        # TODO: Should this be checking against `self.value`?
        if self._value is None:
            if self.required:
                assert self.default is None
                assert not self.default_set
                self.raise_required()

        if self.types is not None:
            # It should have already been validated in the validate_configuration method that the
            # default is of the specified types.
            assert self.default is not None
            assert isinstance(self.default, self.types)
            if not isinstance(self.value, self.types):
                self.raise_invalid_type()

        if self._validate is not None:
            # The default value is already validated against the method in the
            # validate_configuration method.
            self._validate(self._value, self)

    def validate_configuration(self):
        """
        Validates the parameters of the `obj:Configuration` configuration.  This validation is
        independent of any value that would be set on the `obj:Configuration`, so it runs after
        initialiation.

        This validation is primarily for internal purposes and is meant to ensure that the
        `obj:Configuration`(s) are defined properly in the `obj:Option` and `obj:Options`.

        TODO:
        ----
        (1) Allow nesting of children exceptions in a parent exception class in a clean way to
            allow us to show the underlying reasons why something occured easily.
        (2) Should we maybe add a property that validates the type of value provided if it is
            not `None`?  This would allow us to have a non-required value type checked if it is
            provided.  This would be a useful configuration for the `obj:Option` and `obj:Options`.
        """
        if not isinstance(self.required, bool):
            self.raise_invalid(message=(
                "The `required` parameter for configuration `{field}` must be a boolean."
            ))

        # Validate that the optionally provided `validate` method is of the correct signature.
        if self._validate is not None:
            if (not six.callable(self._validate)
                    or not check_num_function_arguments(self._validate, 1)):
                self.raise_invalid(message=(
                    "The `validate` parameter for configuration `{field}` must be a callable "
                    "that takes the value of the configuration as it's first and only argument."
                ))

        # Validate that the optionally provided `types` parameter is valid.
        if self.types is not None:
            for tp in self.types:
                if not isinstance(tp, type):
                    self.raise_invalid(message=(
                        "If specified, `types` parameter must be an iterable of types."
                    ))

        # Validate that the default is either set or not set properly based on the requirement
        # parameter.
        if self.required is True:
            # This accounts for cases when the default value is not None or is explicitly set as
            # None.
            if self.default_set:
                self.raise_invalid(message=(
                    "Cannot provide a default value for configuration `{field}` "
                    "because the configuration is required."
                ))
        else:
            if not self.default_set:
                # We don't want to raise invalid here, just indicate that the default value of
                # `None` will be used.
                logger.warning(
                    "The configuration for `%s` is not required and no default value is specified. "
                    "The default value will be `None`." % self.field
                )

        # Validate that if the configuration has a default value, that the default value also
        # passes the validation - this also applies when the default value is None.
        if self._validate is not None:
            try:
                self._validate(self.default)
            # Allow other exceptions to propogate because those are either valid errors or
            # represent inproper usage of the `validate` parameter.
            except ConfigurationInvalidError:
                # TODO: Should we call self.raise_invalid() instead?
                self.raise_invalid(
                    message="The configuration default value is invalid.",
                    value=self.default
                )

        # If the types are specified and the default value is not specified, the value of
        # `None` will not be of the required types.
        if self.types is not None and (
                self.default is None or not isinstance(self.default, self.types)):
            self.raise_invalid(
                message="The default value is not of type %s." % self.types,
                value=self.default
            )
