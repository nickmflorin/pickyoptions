import logging

from pickyoptions.lib.utils import ensure_iterable

from pickyoptions import constants, settings

from .base import BaseModel
from .child import Child
from .configuration import SimpleConfigurable
from .exceptions import (
    ValueNotSetError, ValueRequiredError, ValueLockedError,
    ValueInvalidError, ValueTypeError)
from .routine import Routine
from .utils import accumulate_errors


logger = logging.getLogger(settings.PACKAGE_NAME)


class Value(Child, SimpleConfigurable):
    parent_cls = ('Option', 'Configuration')

    # Note: This isn't used here because the child is not grouped into a
    # parent with multiple children, but it is necessary for ABC.  We should
    # figure out a way to fix that.
    child_identifier = "field"

    def __init__(self, field, parent, **kwargs):
        self._value = constants.NOTSET
        self._defaulted = constants.NOTSET
        self._set = False
        self._field = field

        Child.__init__(self, parent=parent)
        kwargs['configure_on_init'] = True
        SimpleConfigurable.__init__(self, **kwargs)

        self.defaulting_routine = Routine(id="defaulting")

    def _configure(
        self,
        validate=None,
        normalize=None,
        required=False,
        default=constants.NOTSET,
        locked=False,
        post_set=None,
        types=None,
        allow_null=False,
        not_set_error=None,
        required_error=None,
        locked_error=None,
        invalid_error=None,
        invalid_type_error=None,
        configuration_error=None,
    ):
        self._default = default
        self._required = required
        self._locked = locked
        self._validate = validate
        self._normalize = normalize
        self._post_set = post_set
        self._types = types
        self._allow_null = allow_null

        self.not_set_error = not_set_error or ValueNotSetError
        self.required_error = required_error or ValueRequiredError
        self.locked_error = locked_error or ValueLockedError
        self.invalid_type_error = invalid_type_error or ValueTypeError
        self.invalid_error = invalid_error or ValueInvalidError

        self.configuration_error = configuration_error
        assert self.configuration_error is not None

    @property
    def field(self):
        return self._field

    def assert_set(self, *args, **kwargs):
        if not self.set:
            self.raise_not_set(*args, **kwargs)

    def raise_with_self(self, *args, **kwargs):
        # The Child class method raise_with_self is currently being called,
        # so we are duplicating the field - but this is setting it as the default
        # so I think we are okay, although the logic should be cleaned up.
        kwargs.setdefault('field', self.field)
        kwargs.setdefault('instance', self.parent)
        super(Value, self).raise_with_self(*args, **kwargs)

    def raise_not_set(self, *args, **kwargs):
        kwargs['cls'] = self.not_set_error
        return self.raise_with_self(*args, **kwargs)

    def raise_locked(self, *args, **kwargs):
        kwargs['cls'] = self.locked_error
        return self.raise_with_self(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        kwargs['cls'] = self.required_error
        return self.raise_with_self(*args, **kwargs)

    def raise_invalid(self, *args, **kwargs):
        kwargs.setdefault('cls', self.invalid_error)
        return self.raise_with_self(*args, **kwargs)

    def raise_invalid_type(self, *args, **kwargs):
        kwargs['cls'] = self.invalid_type_error
        return self.raise_with_self(*args, **kwargs)

    @property
    def types(self):
        iterable = ensure_iterable(self._types)
        if len(iterable) != 0:
            return iterable
        return None

    # TODO: Might be able to be conglomerated into the common child class.
    @property
    def set(self):
        if self._set:
            assert self._value != constants.NOTSET
        else:
            assert self._value == constants.NOTSET
        return self._set

    @property
    def locked(self):
        return self._locked

    @property
    def required(self):
        return self._required

    @property
    def default(self):
        # TODO: Should we return the NOTSET here?
        self.assert_set()
        return self._default

    @property
    def default_provided(self):
        """
        Returns whether or not the instance has been explicitly initialized
        with a default value.
        """
        return self._default != constants.NOTSET

    @property
    def defaulted(self):
        """
        Returns whether or not the instance has been defaulted.
        """
        # TODO: Cleanup this logic.
        self.assert_set()
        if self._default == constants.NOTSET:
            assert self._defaulted is False
        return self._defaulted

    def set_default(self):
        if self.set:
            # TODO: Update the exception.
            # TODO: Do we want to keep this check?
            raise ValueError(
                "Cannot set default on option when it has already been set.")
        with self.defaulting_routine(self):
            self.value = None

    def reset(self):
        self._value = constants.NOTSET
        self._defaulted = constants.NOTSET
        self._set = False

    def post_set(self, value):
        if self._post_set is not None:
            self._post_set(value)

    def normalize(self, value):
        if self._normalize is not None:
            return self._normalize(value, self.parent)
        return value

    @property
    def value(self):
        # TODO: Implement allow null checks.
        # TODO: Do we return the default here if the value is not provided?
        self.assert_set()
        assert self._value != constants.NOTSET

        if self._value is None:
            assert not self.required
            assert self.default_provided
            return self.normalize(self.default)

        # This really only counts in the `obj:Option` case.
        return self.normalize(self._value)
        # if self._value is None:
        #     assert not self.required
        #     # assert self.allow_null
        #     return self.normalize(self.default)
        # return self.normalize(self._value)

    @value.setter
    def value(self, value):
        self.assert_configured()

        self._defaulted = False
        if self.defaulting_routine.in_progress:
            self._defaulted = True
            assert not self.required

        if value is None:
            assert not self.required
            # The value may or may not have been set yet at this point.
            if self.set:
                assert self.defaulted is True

        self._value = value
        self._set = True
        self.validate()
        self.post_set(value)

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
        if self.value is None:
            if self.required:
                assert self.default is None
                assert not self.defaulted
                self.raise_required()
            else:
                if self.types is not None:
                    self.raise_invalid_type()

        if self.types is not None:
            # It should have already been validated in the validate_configuration
            # method that the default is of the specified types.
            if self.defaulted:
                assert self.default is not None
                assert isinstance(self.default, self.types)
            if not isinstance(self.value, self.types):
                self.raise_invalid_type()

        # if self._validate is not None:
        #
        #     # The default value is already validated against the method in the
        #     # validate_configuration method.
        #     self._validate(self._value, self)

    @accumulate_errors(error_cls='configuration_error')
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
            except self.configuration_error:
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


class Valued(BaseModel):
    abstract_properties = (
        'not_set_error',
        'locked_error',
        'required_error',
        'configuration_error',
        'invalid_error'
    )
    abstract_methods = ('post_set', )

    def __init__(self, field, **kwargs):
        # NOTE: The field here seems to only be needed for referencing exceptions,
        # maybe there is a better way to do this.
        self.value_instance = Value(
            field,
            self,
            not_set_error=self.not_set_error,
            locked_error=self.locked_error,
            required_error=self.required_error,
            configuration_error=self.configuration_error,
            invalid_error=self.invalid_error,
            required=kwargs.get('required'),
            allow_null=kwargs.get('allow_null'),
            types=kwargs.get('types'),
            locked=kwargs.get('locked'),
            default=kwargs.get('default'),
            validate=kwargs.get('validate'),
            normalize=kwargs.get('normalize'),
            post_set=self.post_set
        )

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

    def validate_value(self):
        self.value_instance.validate()
