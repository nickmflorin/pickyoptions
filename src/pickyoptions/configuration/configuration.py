from abc import ABCMeta
import six

from pickyoptions import constants
from pickyoptions.lib.utils import ensure_iterable

from .exceptions import (
    ConfigurationInvalidError, ConfigurationRequiredError, ConfigurationTypeError)


# TODO: Recursively make this an instance of ConfigurableModel!
class Configuration(six.with_metaclass(ABCMeta, object)):
    _default = "NOTSET"
    _types = None
    _required = False

    def __init__(self, field, **kwargs):
        self._field = field
        self._types = kwargs.get('types', self._types)
        self._required = kwargs.get('required', self._required)
        self._default = kwargs.get('default', self._default)
        self._validator = kwargs.get('validator')
        self.validate_configuration()

    @property
    def required(self):
        return self._required

    @property
    def field(self):
        return self._field

    @property
    def default(self):
        return self._default

    @property
    def validator(self):
        return self._validator

    @property
    def default_set(self):
        return self.default != constants.NOTSET

    @property
    def types(self):
        if self._types is not None:
            return ensure_iterable(self._types, cast=tuple)
        return ()

    def raise_invalid(self, *args, **kwargs):
        cls = kwargs.pop('cls', ConfigurationInvalidError)
        kwargs['field'] = self.field
        raise cls(*args, **kwargs)

    def raise_invalid_type(self, *args, **kwargs):
        kwargs['cls'] = ConfigurationTypeError
        self.raise_invalid(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        kwargs['cls'] = ConfigurationRequiredError
        self.raise_invalid(*args, **kwargs)

    def validate_configuration(self):
        """
        Validates that the `obj:Configuration` is configured properly for use.  This validation
        is for internal purposes only and is meant to ensure that the `obj:Configuration` is
        defined properly to handle user defined configuration values.
        """
        # This applies when the default value is None as well.
        if self.required and self.default_set:
            raise Exception(
                "Cannot provide a default configuration value for %s if the "
                "configuration is required." % self.field
            )
        elif not self.required and not self.default_set:
            raise Exception(
                "The configuration %s is not required, but no default is specified. "
                "The default value must be specified in the case that the configuration "
                "value is not provided." % self.field
            )
        # Validate that if the configuration has a default value, that the default value also
        # passes the validation.
        elif self.default_set:
            try:
                self.validate(self.default)
            except ConfigurationInvalidError as e:
                raise Exception("The configuration default value is invalid: %s" % str(e))

    def validate_not_provided(self):
        if self.required:
            # We should have validated whether or not the default is set for the required case
            # in the validate_configuration() method.
            assert not self.default_set
            self.raise_required()

        # We are guaranteed that the default value is set because of the validate_configuration
        # method, but we will raise Exception's for now just in case.
        if not self.default_set:
            raise Exception(
                "An earlier exception should have been raised, validate_configuration "
                "was not called properly."
            )

    def validate(self, value):
        # If the value is None, should this have already been checked?  We might have to also
        # check if the value is explicitly set as None.
        if value is None:
            self.validate_not_provided()
        else:
            # TODO: If the default is specified, should we ignore the requirement?
            if self.types and not isinstance(value, self.types):
                self.raise_invalid_type()
        if self.validator:
            self.validator(value, self)
