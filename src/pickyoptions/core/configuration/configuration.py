import logging

from pickyoptions import settings, constants
from pickyoptions.lib.utils import ensure_iterable

from pickyoptions.core.utils import (
    accumulate_errors, require_set, require_set_property)

from .child import Child
from .configurable import Configurable
from .exceptions import (
    ConfigurationInvalidError,
    ConfigurationRequiredError,
    ConfigurationTypeError,
    ConfigurationNotSetError,
    ConfigurationLockedError,
    NotConfiguredError,
    ConfiguringError,
    ConfigurationError,
    ConfigurationDoesNotExist,
)
from .utils import require_configured_property, require_configured


logger = logging.getLogger(settings.PACKAGE_NAME)


# TODO: When the configuration values change, we need to trigger the validation
# of the configuration (now that it is not maintained by the valued class).
class Configuration(Child, Configurable):
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

    # TODO: Currently not implemented.
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

    # TODO: Currently not implemented.
    # TODO: Is this true?  Can we override if it is already locked?
    locked: `obj:bool` (optional)
        Whether or not the `obj:Configuration` is allowed to be reconfigured
        after it was initially configured.

        Default: True
    """
    ___abstract__ = False

    # Child Implementation Properties
    parent_cls = 'Configurations'
    child_identifier = 'field'
    does_not_exist_error = ConfigurationDoesNotExist
    not_set_error = ConfigurationNotSetError
    locked_error = ConfigurationLockedError
    required_error = ConfigurationRequiredError
    invalid_error = ConfigurationInvalidError
    invalid_type_error = ConfigurationTypeError

    # Configurable Implementation Properties
    not_configured_error = NotConfiguredError
    configuring_error = ConfiguringError
    configuration_error = ConfigurationError

    def __init__(self, field, validation_error=None, parent=None, **kwargs):
        self._value = constants.NOTSET
        self._defaulted = False
        self._set = False

        self._default = kwargs.get('default', constants.NOTSET)
        self._required = kwargs.get('required', False)
        # Currently not implemented.
        self._allow_null = kwargs.get('allow_null', False)
        # Currently not implemented.
        self._locked = kwargs.get('locked', False)
        self._types = kwargs.get('types', None)
        self._normalize = kwargs.get('normalize', None)
        self._validate = kwargs.get('validate', None)

        # This really shouldn't be defaulted to a ConfigurationError,
        # but for the time being we will let it be that way.
        self._validation_error = validation_error or ConfigurationError

        Child.__init__(self, field, parent=parent)
        Configurable.__init__(self)

        # Is this used?
        self.create_routine(
            id="defaulting",
            post_routine=self.post_default,
            pre_routine=self.pre_default,
        )

    def _configure(self, value):
        self.value = value

    @property
    def validation_error(self):
        return self._validation_error

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
        if not self.default_provided:
            self.assert_not_required()
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

    def set_default(self):
        with self.routines.defaulting:
            self.value = constants.EMPTY

    def __repr__(self):
        #  TODO: Clean this up!
        # We can't necessarily access configured unless it is initialized with the
        # routine.
        if self.initialized:
            if self.configured:
                return (
                    "<{cls_name} state={state} field={field} value={value}>".format(
                        cls_name=self.__class__.__name__,
                        field=self.field,
                        value=self.value,
                        state=self.configuration_state,
                    )
                )
            return "<{cls_name} state={state} field={field}>".format(
                cls_name=self.__class__.__name__,
                field=self.field,
                state=self.configuration_state,
            )
        # The field might not be present yet if it is not initialized.
        # The field attribute won't be available until the `obj:Configuration`
        # is configured - not anymore, the field is set as the first line of the
        # init.
        return "<{cls_name} state={state}>".format(
            cls_name=self.__class__.__name__,
            state="NOT_INITIALIZED"
        )

    def post_set(self, value):
        pass

    @property
    def set(self):
        if self._set:
            assert self._value != constants.NOTSET
        else:
            assert self._value == constants.NOTSET
        return self._set

    def pre_default(self):
        # TODO: Should we reset _defaulted here?
        self.assert_not_required()

    def post_default(self):
        # TODO: Do we need to worry about resetting this value to False in the
        # case that a non-default argument is provided?
        self._defaulted = True
        # We have to run the validation after the default, because it cannot
        # run inside of the `.value` setter when defaulting...
        # self.do_validate()

    @require_set_property
    def defaulted(self):
        """
        Returns whether or not the instance has been defaulted.

        TODO:
        ----
        Right now this only refers to the situation in which the default was
        provided?
        """
        # TODO: Cleanup this logic.
        # TODO: Should we maybe disallow access of this property if the defaultign
        # routine is in progress?
        if self._defaulted is True:
            # Considering removing the routines for this...
            assert self.routines.defaulting.finished
        return self._defaulted

    @property
    def defaulting(self):
        return self.routines.defaulting.in_progress

    @require_set_property
    def value(self):
        # TODO: Implement allow null checks.
        # TODO: Do we return the default here if the value is not provided?
        assert not self.routines.defaulting.in_progress

        # TODO: Should we return the default value if the value is explicitly
        # provided as null?  This is where the allow_null property comes in...
        if self._value == constants.EMPTY:
            # If the value is None, the value must not be required.  The value
            # does not necessarily have to have been defaulted, since that only
            # applies when the default is provided.
            assert not self.required
            if self.default_provided:
                assert self.defaulted is not None
                assert self.defaulted
                assert self._default != constants.NOTSET

            return self.do_normalize(self.default)

        # This really only counts in the `obj:Option` case.
        return self.do_normalize(self._value)

    # TODO: The logic here needs to be cleaned up.
    # TODO: Incorporate allow_null checks.
    @value.setter
    def value(self, value):
        # TODO: Consider making the setting of the value a routine itself.
        self.assert_configured()

        # Perform the validation before setting the value on the instance.
        self.do_validate(value=value)
        self._value = value

        # TODO: What do we do if the value is being set to a default or None
        # after it has already been set?
        if self.set:
            logger.debug("Overriding already set value.")

        # The value can be being set to None even if it is not the default.
        # if value is None:
        #     self.assert_not_required()
        #     # self.assert_allow_null()
        #     if self.defaulting:
        #         # The value of defaulted will be set to True when the routine
        #         # finishes.
        #         self._value = None
        #     else:
        #         # If the default is also None, but we are not defaulting, do
        #         # we want to set the state as having been defaulted?
        #         if self.default == value:
        #             logger.debug(
        #                 "The default is None, but we are also setting to "
        #                 "None explicitly... We have to be careful here."
        #             )
        #             raise Exception()  # Temporary - for sanity.
        #         self._value = value
        # else:
        #     if self.set:
        #         if self.defaulted:
        #             # TODO: What do we do in the case that the value is being
        #             # defaulted to the same value that it is already set to?
        #             if self.default == value:
        #                 logger.debug(
        #                     "The default is None, but we are also setting to "
        #                     "None explicitly... We have to be careful here."
        #                 )
        #                 raise Exception()  # Temporary - for sanity.
        #             # We now have to clear the defaulted state!
        #             self.routines.defaulting.reset()
        #             self._value = value
        #         if value == self._value:
        #             logger.debug(
        #                 "Not changing value since it is already set with "
        #                 "the same value."
        #             )
        #         else:
        #             self._value = value
        #     else:
        #         if not self.defaulting:
        #             if self.default == value:
        #                 logger.debug(
        #                     "The provided value %s is not required to "
        #                     "be explicitly defined because it is the "
        #                     "default." % value
        #                 )
        #             elif value is None:
        #                 assert self.default is not None
        #                 # TODO: What to do if we are setting the value to None
        #                 # when it has a default?
        #                 # This assertion should be done more generally if the
        #                 # value is None.
        #                 # assert self.allow_null
        #         self._value = value

        self._set = True
        # The validate method accesses the already set value, so we must wait
        # until after it is done defaulting (if it is defaulting) to validate.
        # TODO: We should implement a routine for setting the value as well,
        # that way the validation can be performed after the value is set.
        if not self.defaulting:
            self.validate(sender=self)

        # TODO: Should this also be done after the defaulting routine finishes?
        self.post_set(value)

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

    @accumulate_errors(error_cls="validation_error")
    def do_validate(self, value=None, sender=None):
        """
        Validates the `obj:Configuration` after the value is supplied.

        This occurs right before the value is set on the `obj:Configuration`,
        which allows us to determine the the before/after.

        The sender helps us determine if the validate method is being called
        internally in the setter or if the validate method is being called
        externally.

        TODO:
        ----
        (1) Should we maybe add a property that validates the type of value
            provided if it is not `None`?  This would allow us to have a
            non-required value type checked if it is provided.  This would be a
            useful configuration for the `obj:Option` and `obj:Options`.
        (2) See if we can break up the validation into pre-validation and
            post-validation, for validating before the value is set and after,
            to make it easier to deal with the default logic...
        """
        # TODO: This logic needs to be cleaned up quite a bit.

        # TODO: We have to validate against the normalized value as well!

        # TODO: There might be a cleaner way to do this.
        if sender and isinstance(sender, self.__class__):
            assert value is not None
            value_to_validate = value

            # If the value was already set and the configuration is locked, it
            # cannot be changed.
            if self.set and self.locked:
                self.raise_locked()

            if value_to_validate is None:
                if self.required:
                    # If the value is None but required, an exception should have
                    # already been raised in the configuration validation to
                    # disallow providing the default.
                    assert not self.default_provided
                    assert self.default is None
                    yield self.raise_required(return_exception=True)

        else:
            # If being called externally, the value must be SET - otherwise,
            # there is no value to validate.
            self.assert_set()
            value_to_validate = self.value
            assert value_to_validate != constants.EMPTY

            # Here, the value is explicitly provided as None.
            # TODO: Log a warning if the value is being explicitly set as the
            # default value.
            if value_to_validate is None:
                if self.required:
                    # If the value is None but required, an exception should have
                    # already been raised in the configuration validation to
                    # disallow providing the default.
                    assert not self.default_provided
                    assert self.default is None
                    yield self.raise_required(return_exception=True)

                if self.types is not None:
                    yield self.raise_invalid_type(return_exception=True)

            elif value_to_validate == constants.EMPTY:
                assert self.defaulting
                # If the sender is provided, `self.value` is used - which cannot
                # be empty.
                assert sender is not None

                if self.required:
                    # If the value is None but required, an exception should have
                    # already been raised in the configuration validation to
                    # disallow providing the default.
                    assert not self.default_provided
                    assert self.default is None
                    yield self.raise_required(return_exception=True)

                # If the value is being defaulted and the types are provided, the
                # default should align with those types due to validation in the
                # configuration validation method.
                if self.types is not None:
                    assert self.default is not None
                    assert isinstance(self.default, self.types)

            else:
                if self.types is not None:
                    if not isinstance(value, self.types):
                        yield self.raise_invalid_type(return_exception=True)

        # The default and normalized default are already checked in the
        # configuration validation - so we are really only concerned if the value
        # is not one of those.
        # TODO: Maybe we should allow the validate method to return error messages
        # or other things like we do for the Option case.
        if self.validate is not None:
            try:
                self.validate(value)
            except ConfigurationError as e:
                yield e

    @accumulate_errors(error_cls=ConfigurationError)
    @require_configured
    def validate_configuration(self):
        """
        Validates the parameters of the `obj:Configuration` configuration.

        This validation is independent of any value that would be set on the
        `obj:Configuration`, so it runs after initialiation and after the
        configuration values are changed.
        """
        # Validate that the default is not provided in the case that the value
        # is required.
        if self.required is True:
            # This accounts for cases when the default value is not None or is
            # explicitly set as None.
            if self.default_provided:
                yield self.raise_invalid(
                    return_exception=True,
                    message=(
                        "Cannot provide a default value for configuration "
                        "`{name}` because the configuration is required."
                    )
                )
        # If the value is not required, issue a warning if the default is not
        # explicitly provided.
        else:
            if not self.default_provided:
                logger.warning(
                    "The configuration for `%s` is not required and no default "
                    "value is specified. The default value will be `None`."
                    % self.field
                )
            # If the value is not required (the default is applicable) we need
            # to make sure that the default and the normalized default pass the
            # user provided validation.
            try:
                self.do_validate(value=self.default, sender=self)
            # Catching the configuration error should catch all the possible
            # errors that would be in there, right?
            except ConfigurationError as e:
                # TODO: Add more user detail to the error message.
                # TODO: Make sure this doesn't cause bizarre nesting.
                yield self.raise_invalid(
                    return_exception=True,
                    message=(
                        "The provided validation deems the default value "
                        "`{value}` invalid. The validation method must work "
                        "for both the default and the populated values."
                    ),
                    value=self.default,
                    children=[e],
                )
            if self.normalize:
                normalized_default_value = self.normalize(self.default)
                try:
                    self.do_validate(
                        value=normalized_default_value,
                        sender=self
                    )
                # Catching the configuration error should catch all the possible
                # errors that would be in there, right?
                except ConfigurationError as e:
                    # TODO: Add more user detail to the error message.
                    # TODO: Make sure this doesn't cause bizarre nesting.
                    yield self.raise_invalid(
                        return_exception=True,
                        message=(
                            "The provided validation deems the normalized "
                            "default value `{value}` invalid. The validation "
                            "method must work for the default value, the "
                            "normalized default value and the populated "
                            "values."
                        ),
                        value=self.default,
                        children=[e],
                    )

            # If the types are specified and the default value is not specified,
            # the default value must also be of those types - even if it is None.
            # TODO: Allow a setting that validates the value only if it is not
            # None.
            if self.types is not None:
                if (
                    self.default is None
                    or not isinstance(self.default, self.types)
                ):
                    # TODO: Add more user detail to the error message.
                    yield self.raise_invalid(
                        return_exception=True,
                        value=self.default,
                        types=self.types,
                        message=(
                            "The default value `{value}` is not of the "
                            "provided types, `{types}`."
                        )
                    )
