import logging

from pickyoptions import settings, constants
from pickyoptions.lib.utils import ensure_iterable

from pickyoptions.core.decorators import accumulate_errors, require_set_property

from .configurable import ConfigurableChild
from .exceptions import (
    ConfigurationInvalidError,
    ConfigurationRequiredError,
    ConfigurationTypeError,
    ConfigurationNotSetError,
    ConfigurationLockedError,
    NotConfiguredError,
    ConfiguringError,
    ConfigurationError,
    ConfigurationDoesNotExistError,
    ConfigurationValidationError,
    ConfigurationNullNotAllowedError,
    ConfigurationSetError,
    ConfigurationNotRequiredError
)
from .utils import require_configured_property, require_configured


logger = logging.getLogger(settings.PACKAGE_NAME)


class Configuration(ConfigurableChild):
    """
    Represents a single configurable value in a set of `obj:Configurations`
    for either a `obj:Option` or the set of `obj:Options`.

    Parameters:
    ----------
    field: `obj:str` (required)
        A string identifier for the `obj:Configuration`.  This property will
        be used to access the `obj:Configuration` from the grouped
        `obj:Configurations` instance.

    default: `obj:object` (optional)
        The default value for the `obj:Configuration` if the `obj:Configuration`
        is not required and a value is not provided.

        Default: NOTSET (or None publically)

    types: `obj:tuple` or `obj:list` (optional)
        The types that the value of the `obj:Configuration` should be forced to
        comply with.  If provided and the value provided for the
        `obj:Configuration` is not of those types, an exception will be raised.

        Default: ()

    required: `obj:bool` (optional)
        Whether or not the `obj:Configuration` is required.  If True and the
        value is not provided for the `obj:Configuration`, an exception will be
        raised.

        Default: False

    allow_null: `obj:bool` (optional)
        Whether or not the `obj:Configuration` is allowed to take on null values.

        Default: True

    validate: `obj:func` (optional)
        A validation method that determines whether or not the value provided
        for the `obj:Configuration` is valid.  The provided method must take the
        `obj:Configuration` value as it's first and only argument.

        It is important to note that the validate method will be applied to
        both the provided configuration value and it's default - so both must
        comply.

        Default: None

    normalize: `obj:func` (optional)
        A normalization method that normalizes the provided value to the
        `obj:Configuration`.

        It is important to note that the normalization method will be applied
        to the default value as well.

        Default: None

    locked: `obj:bool` (optional)
        Whether or not the `obj:Configuration` is allowed to be reconfigured
        after it was initially configured.

        Default: True
    """
    __abstract__ = False

    # Child Implementation Properties
    parent_cls = 'Configurations'
    child_identifier = 'field'

    errors = {
        # Child Implementation Errors
        'does_not_exist_error': ConfigurationDoesNotExistError,
        'not_set_error': ConfigurationNotSetError,
        'set_error': ConfigurationSetError,
        'locked_error': ConfigurationLockedError,
        'required_error': ConfigurationRequiredError,
        'not_required_error': ConfigurationNotRequiredError,
        'invalid_error': ConfigurationInvalidError,
        'invalid_type_error': ConfigurationTypeError,
        'not_null_error': ConfigurationNullNotAllowedError,
        # Configurable Implementation Errors
        'not_configured_error': NotConfiguredError,
        'configuring_error': ConfiguringError,
        'configuration_error': ConfigurationError,
        # Configuration Implementation Properties
        'validation_error': ConfigurationValidationError,
    }

    def __init__(self, field, parent=None, errors=None, **kwargs):
        """
        Initializes the `obj:Configuration` instance with the provided field,
        parent and configuration parameters.

        TODO:
        ----
        - It might be useful in the future to pass a value directly into init
          and have the `obj:Configuration` handle that.
        - Implement properties for allowing/not allowing a blank string, empty
          iterable, etc.
        """
        self._value = constants.NOTSET
        self._defaulted = False
        self._set = False

        super(Configuration, self).__init__(field, parent=parent, errors=errors,
            **kwargs)

    def __postinit__(self, field, parent=None, **kwargs):
        """
        Configures the `obj:Configuration` after initialization is complete.

        The configuration of the `obj:Configuration` instance is not lazy,
        and the configuration validation will be performed immediately after
        the configuration finishes.  For this reason, simply initializing a
        configuration causes code to run.
        """
        self.configure(**kwargs)
        self.assert_configured()

    def _configure(self, **kwargs):
        """
        Configures the `obj:Configuration` instance with the provided
        parameters.
        """
        self._default = kwargs.get('default', constants.NOTSET)
        self._required = kwargs.get('required', False)
        self._allow_null = kwargs.get('allow_null', True)
        self._locked = kwargs.get('locked', False)
        self._types = kwargs.get('types', None)
        self._normalize = kwargs.get('normalize', None)
        self._validate = kwargs.get('validate', None)

    def __repr__(self):
        # The field might not be present yet if it is not initialized.
        if self.initialized:
            if self.set:
                return super(Configuration, self).__repr__(
                    field=self.field,
                    value=self.value,
                    state=self.configuration_state,
                )
            return super(Configuration, self).__repr__(
                field=self.field,
                state=self.configuration_state,
            )
        return super(Configuration, self).__repr__(state="NOT_INITIALIZED")

    @require_configured_property
    def types(self):
        iterable = ensure_iterable(self._types)
        if len(iterable) != 0:
            return iterable
        return None

    @types.setter
    def types(self, value):
        self._types = value
        self.validate_configuration()

    @require_configured_property
    def locked(self):
        return self._locked

    @locked.setter
    def locked(self, value):
        self._locked = value
        self.validate_configuration()

    @require_configured_property
    def required(self):
        return self._required

    @required.setter
    def required(self, value):
        self._required = value
        self.validate_configuration()

    @require_configured_property
    def allow_null(self):
        return self._allow_null

    @allow_null.setter
    def allow_null(self, value):
        self._allow_null = value
        self.validate_configuration()

    @require_configured_property
    def validate(self):
        return self._validate

    @validate.setter
    def validate(self, value):
        self._validate = value
        self.validate_configuration()

    @require_configured_property
    def normalize(self):
        return self._normalize

    @normalize.setter
    def normalize(self, value):
        self._normalize = value
        self.validate_configuration()

    @require_configured_property
    def default(self):
        # We can only access the default in the case that the configuration is
        # not required.  We might want to change this.
        self.assert_not_required()
        if not self.default_provided:
            assert self._default == constants.NOTSET
            return None
        assert self._default != constants.NOTSET
        return self._default

    @require_configured_property
    def default_provided(self):
        """
        Returns whether or not the instance has been explicitly initialized
        with a default value.
        """
        return self._default != constants.NOTSET

    @require_set_property
    def defaulted(self):
        """
        Returns whether or not the instance has been defaulted.
        """
        if self._defaulted:
            assert self._default != constants.NOTSET
        else:
            assert self._default == constants.NOTSET
        return self._defaulted

    @property
    def provided(self):
        """
        The value is NOTSET when it hasn't been either defaulted or provided
        yet.  If the value is defaulted, the value will be EMPTY.  If it is
        explicitly provided, it will not be EMPTY.
        """
        self.assert_set()
        return self._value != constants.EMPTY

    @property
    def empty(self):
        return self._value == constants.EMPTY

    def set_default(self):
        self.value = constants.EMPTY
        self._defaulted = True

    @property
    def set(self):
        if self._set:
            assert self._value != constants.NOTSET
        else:
            assert self._value == constants.NOTSET
        return self._set

    @require_set_property
    def value(self):
        # There are a bunch of holes here that we need to clean up.
        # TODO: Implement allow null checks.
        # TODO: Do we return the default here if the value is not provided?

        # TODO: Should we return the default value if the value is explicitly
        # provided as null?  This is where the allow_null property comes in...
        if not self.provided:
            # If the value is None, the value must not be required.  The value
            # does not necessarily have to have been defaulted, since that only
            # applies when the default is provided.
            self.assert_not_required()
            if self.default_provided:
                # The default can still be None if it is explicitly provided.
                assert self.defaulted
                assert self._default != constants.NOTSET

            return self.do_normalize(self.default)

        elif self._value is None:
            assert self.allow_null

        # This really only counts in the `obj:Option` case.
        return self.do_normalize(self._value)

    # TODO: The logic here needs to be cleaned up.
    # TODO: Incorporate allow_null checks.
    @value.setter
    def value(self, value):
        self.assert_configured()

        # If the value was already set and the configuration is locked, it
        # cannot be changed.
        if self.set and self.locked:
            self.raise_locked()

        # TODO: What do we do if the value is being set to a default or None
        # after it has already been set?
        if self.set:
            logger.debug("Overriding already set value.")

        # Perform the validation before setting the value on the instance.
        self.do_validate(value=value)

        # If the `obj:Configuration` is required, the default is None (since
        # _default is EMPTY).  This means that if the value equals the default,
        # the value is None which is now allowed for the required case - meaning,
        # this case only counts for the non-required case.
        if not self.required and value == self.default:
            logger.warning(
                "Setting the value as %s when that is the default, "
                "this will cause the configuration to be defaulted." % value
            )
            self._value = constants.EMPTY
            self._defaulted = True
        else:
            self._value = value

        self._set = True

    def reset(self):
        # We might not need this for the configuration case...
        raise NotImplementedError()
        self.routines.defaulting.reset()
        self._value = constants.NOTSET
        self._defaulted = False
        self._set = False

    def do_normalize(self, value):
        if self.normalize is not None:
            return self.normalize(value)
        return value

    # TODO: Start using a validation error, specific to each object.  Should
    # we maybe be using a configuration error instead of a validation error?
    @accumulate_errors(error_cls='validation_error', name='field')
    def do_validate_value(self, value, detail=None):
        # TODO: Log a warning if the value is being explicitly set as the
        # default value.
        if value == constants.EMPTY:
            # This will trigger the default value to be used, and the
            # normalized default value is already validated in the validate
            # configuration method.
            if self.required:
                # If the value is None but required, an exception should have
                # already been raised in the configuration validation to
                # disallow providing the default.
                assert not self.default_provided
                assert self.default is None
                yield self.raise_required(
                    return_exception=True,
                    detail=detail,
                )
        else:
            # Here, the value is explicitly provided as None.
            if value is None:
                if not self.allow_null:
                    # TODO: Come up with a not allowed null error.
                    yield self.raise_required(
                        return_exception=True,
                        detail=detail
                    )
            else:
                if self.types is not None:
                    if not isinstance(value, self.types):
                        yield self.raise_invalid_type(
                            return_exception=True,
                            detail=detail
                        )

        # The default and normalized default are already checked in the
        # configuration validation - so we are really only concerned if the
        # value is not one of those.
        # TODO: For the above reason, should we only be performing validation
        # if the value is not EMPTY (i.e. it is not defaulting)?
        # TODO: Maybe we should allow the validate method to return error
        # messages or other things like we do for the Option case.
        if self.validate is not None:
            try:
                self.validate(value)
            # TODO: Should we be catching a different type of exception here?
            # Currently, this is not really used - so it doesn't matter, but
            # it may be used in the future.
            except ConfigurationError as e:
                # TODO: Include the detail here?
                yield e

    @accumulate_errors(error_cls='validation_error', name='field')
    def do_validate(self, detail=None, **kwargs):
        """
        Validates the value in the context of the `obj:Configuration`.  This can
        either be before the value is being set on the `obj:Configuration` or
        when default/normalized values are being validated with the
        provided configuration for the `obj:Configuration`.
        """
        if 'value' in kwargs:
            value = kwargs.pop('value')
            yield self.do_validate_value(value, return_children=True,
                detail=detail)

            # Validate the normalized value if it is applicable.
            # TODO: We only care about this in the case that the value is not
            # defaulted, and the normalized value is different from the actual
            # value.  Maybe we should account for this in the logic.
            # TODO: Should we maybe only do this if there are no errors with the
            # actual value?
            if self.normalize is not None:
                # TODO: Maybe we should wrap this in some kind of different
                # exception to make it more obvious what is going on.
                normalized_value = self.do_normalize(value)
                yield self.do_validate_value(
                    normalized_value,
                    return_children=True,
                    detail="(Normalized Value)",
                )
        else:
            # If being called externally, the value must be SET - otherwise,
            # there is no value to validate.
            self.assert_set()
            yield self.do_validate(
                value=self.value,
                return_children=True,
                detail=detail,
            )

    @accumulate_errors(error_cls='configuration_error', name='field')
    @require_configured
    def validate_configuration(self):
        """
        Validates the parameters of the `obj:Configuration` configuration.

        This validation is independent of any value that would be set on the
        `obj:Configuration`, so it runs after initialiation and after the
        configuration values are changed, but not when the actual value on the
        `obj:Configuration` changes.

        TODO:
        ----
        - Log warning or raise exception if allow_null is specified and the
          required parameter makes this misleading.
        """
        # Validate that the default is not provided in the case that the value
        # is required.
        if self.required is True:
            # This accounts for cases when the default value is not None or is
            # explicitly set as None.
            # TODO: Do we really want to raise an exception here?  Maybe we should
            # just log a warning?
            if self.default_provided:
                yield self.raise_invalid(
                    return_exception=True,
                    message=(
                        "Cannot provide a default value for configuration "
                        "{name} because the configuration is required."
                    )
                )
        else:
            # If the value is not required, issue a warning if the default is not
            # explicitly provided.
            if not self.default_provided:
                logger.warning(
                    "The configuration for `%s` is not required and no default "
                    "value is specified. The default value will be `None`."
                    % self.field
                )

            # TODO: Do we want to check against the PRIVATE default?  The
            # do_validate method checks against EMPTY values, but I'm not sure
            # if we would want that to trigger an error.
            # Note: This will also validate the default normalized value.
            errors = self.do_validate(
                value=self.default,
                return_children=True
            )
            if errors:
                yield self.raise_invalid(
                    return_exception=True,
                    message="The configuration {name} default is invalid.",
                    children=errors,
                )
