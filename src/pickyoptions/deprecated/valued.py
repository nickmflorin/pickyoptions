import six

from pickyoptions.core.base import BaseModel
from .exceptions import ValueTypeError, ValueInvalidError


class AbstractValued(BaseModel):
    __abstract__ = True
    abstract_properties = ('value_cls', )

    def __init__(self, field, **kwargs):
        # TODO: The field can be referenced from the Value instance.
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
        self.value_instance = self.value_cls(
            self,
            field,
            not_set_error=self.not_set_error,
            locked_error=self.locked_error,
            required_error=self.required_error,
            configuration_error=self.configuration_error,
            invalid_error=self.invalid_error,
            invalid_type_error=self.invalid_type_error,
            validation_errors=self.validation_errors,
            post_set=self.post_set,
            **kwargs
        )

    @property
    def field(self):
        return self.value_instance.field

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
        return self.value_instance.types

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

    def raise_not_set(self, *args, **kwargs):
        return self.value_instance.raise_not_set(*args, **kwargs)

    def raise_set(self, *args, **kwargs):
        return self.value_instance.raise_set(*args, **kwargs)

    def raise_locked(self, *args, **kwargs):
        return self.value_instance.raise_locked(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        return self.value_instance.raise_required(*args, **kwargs)

    def raise_not_required(self, *args, **kwargs):
        return self.value_instance.raise_not_required(*args, **kwargs)

    def raise_invalid(self, *args, **kwargs):
        return self.value_instance.raise_invalid(*args, **kwargs)

    def raise_invalid_type(self, *args, **kwargs):
        return self.value_instance.raise_invalid_type(*args, **kwargs)


class SimpleValued(AbstractValued):
    __abstract__ = True
    abstract_properties = (
        'not_set_error',
        'locked_error',
        'required_error',
        'configuration_error',
        'invalid_error',
        'invalid_type_error',
        'validation_errors',
    )
    abstract_methods = ('post_set', )

    @property
    def value_cls(self):
        # Define as a property so the import can be dynamic and we don't run
        # into circular imports between Configuration and Value.
        from pickyoptions.core.value.value import SimpleValue
        return SimpleValue


class Valued(AbstractValued):
    __abstract__ = True
    abstract_properties = (
        'not_set_error',
        'locked_error',
        'required_error',
        'configuration_error',
        'invalid_error',
        'invalid_type_error',
        'validation_errors',
    )
    abstract_methods = ('post_set', )

    @property
    def value_cls(self):
        # Define as a property so the import can be dynamic and we don't run
        # into circular imports between Configuration and Value.
        from pickyoptions.core.value.value import Value
        return Value
