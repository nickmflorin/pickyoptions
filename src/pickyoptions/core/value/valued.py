import logging
import six

from pickyoptions import settings, constants
from pickyoptions.lib.utils import ensure_iterable

from pickyoptions.core.base import BaseModel
from .exceptions import ValueTypeError, ValueInvalidError

from .value import Value


logger = logging.getLogger(settings.PACKAGE_NAME)


class Valued(BaseModel):
    abstract_properties = (
        'not_set_error',
        'locked_error',
        'required_error',
        'configuration_error',
        'invalid_error',
        'invalid_type_error',
        'validation_errors',
    )

    # TODO: Should we be implementing the user provided validate method in the
    # post set of this class?
    abstract_methods = ('post_set', )

    def __init__(
        self,
        field,
        default=constants.NOTSET,
        required=False,
        allow_null=True,
        locked=False,
        types=None,
        post_set=None,
        normalize=None,
        validate=None,
    ):
        self._field = field
        if not isinstance(self._field, six.string_types):
            raise ValueTypeError(
                name="field",
                types=six.string_types,
            )
        elif self._field.startswith('_'):
            raise ValueInvalidError(
                name="field",
                detail="It cannot be scoped as a private attribute."
            )

        # NOTE: The field here seems to only be needed for referencing exceptions,
        # maybe there is a better way to do this.
        self.value_instance = Value(
            self,
            field,
            not_set_error=self.not_set_error,
            locked_error=self.locked_error,
            required_error=self.required_error,
            configuration_error=self.configuration_error,
            invalid_error=self.invalid_error,
            invalid_type_error=self.invalid_type_error,
            validation_errors=self.validation_errors,
            required=required,
            allow_null=allow_null,
            types=types,
            locked=locked,
            default=default,
            normalize=normalize,
            validate=validate,
            post_set=self.post_set
        )

    @property
    def field(self):
        return self._field

    @property
    def value(self):
        # NOTE: The `obj:Configuration` may or may not be configured at this
        # point, because if the configuration is not present in the provided data
        # it is not technically considered configured.
        return self.value_instance.value

    @value.setter
    def value(self, value):
        self.value_instance.value = value

    @property
    def types(self):
        iterable = ensure_iterable(self._types)
        if len(iterable) != 0:
            return iterable
        return None

    @property
    def set(self):
        return self.value_instance.set

    @property
    def locked(self):
        return self.value_instance.locked

    @property
    def required(self):
        return self.value_instance.required

    @property
    def default(self):
        return self.value_instance.default

    @property
    def default_provided(self):
        """
        Returns whether or not the instance has been explicitly initialized
        with a default value.
        """
        return self.value_instance.default_provided

    @property
    def defaulted(self):
        """
        Returns whether or not the instance has been defaulted.
        """
        return self.value_instance.defaulted

    def set_default(self):
        self.value_instance.set_default()

    # def validate_value(self):
    #     self.value_instance.validate()
