import logging
import inspect

from pickyoptions import constants, settings
from pickyoptions.lib.utils import ensure_iterable, get_class_from_frame

from pickyoptions.core.configuration.configurable import SimpleConfigurable
from pickyoptions.core.configuration.exceptions import ConfigurationError
from pickyoptions.core.family.child import Child
from pickyoptions.core.utils import accumulate_errors

from .exceptions import (
    ValueInvalidError, ValueTypeError, ValueLockedError, ValueNotSetError,
    ValueRequiredError, ValueSetError, ValueNotRequiredError)


logger = logging.getLogger(settings.PACKAGE_NAME)


class Value(Child, SimpleConfigurable):
    # Child implementation properties.
    parent_cls = ('Option', 'Configuration')

    # Note: This isn't used here because the child is not grouped into a
    # parent with multiple children, but it is necessary for ABC.  We should
    # figure out a way to fix that.
    # ---> Come up with a SingleChild class that doesn't have those reqs.
    child_identifier = "field"

    # TODO: Incorporate extensions/flexibility of ValueSetError and
    # ValueNotRequiredError.
    def __init__(
        self,
        parent,
        field,
        configuration_error=ConfigurationError,
        not_set_error=ValueNotSetError,
        required_error=ValueRequiredError,
        invalid_type_error=ValueTypeError,
        invalid_error=ValueInvalidError,
        locked_error=ValueLockedError,
        **kwargs
    ):
        self._value = constants.NOTSET
        self._defaulted = False
        self._set = False
        self._field = field
        self.configuration_error = configuration_error

        Child.__init__(
            self,
            parent=parent,
            not_set_error=not_set_error,
            required_error=required_error,
            invalid_type_error=invalid_type_error,
            invalid_error=invalid_error,
            locked_error=locked_error,
        )
        # TODO: Consider making configuration happen in SimpleConfigurable, or
        # making it lazy.
        SimpleConfigurable.__init__(self)
        # Note that SimpleConfigurable implements Routined already.
        self.create_routine(
            id="defaulting",
            post_routine=self.post_default,
            pre_routine=self.pre_default,
        )
        self.configure(**kwargs)

    def _configure(self, default=constants.NOTSET, required=False,
            allow_null=True, locked=False, types=None, normalize=None,
            post_set=None, validate=None):
        # TODO: We might want to eventually move the validate and post_process
        # to the Valued instance...  But then we would have to be concerned with
        # including the instance and other arguments in the call.
        self._default = default
        self._required = required
        self._allow_null = allow_null
        self._locked = locked
        self._types = types
        self._post_set = post_set
        self._normalize = normalize
        self._validate = validate

    @property
    def field(self):
        return self._field

    def assert_set(self, *args, **kwargs):
        if not self.set:
            self.raise_not_set(*args, **kwargs)

    def assert_not_set(self, *args, **kwargs):
        if self.set:
            self.raise_set(*args, **kwargs)

    def assert_required(self, *args, **kwargs):
        if not self.required:
            self.raise_not_required(*args, **kwargs)

    def assert_not_required(self, *args, **kwargs):
        if self.required:
            self.raise_required(*args, **kwargs)

    def raise_with_self(self, *args, **kwargs):
        # The Child class method raise_with_self is currently being called,
        # so we are duplicating the field - but this is setting it as the default
        # so I think we are okay, although the logic should be cleaned up.
        kwargs.setdefault('name', self.field)
        kwargs.setdefault('instance', self.parent)
        super(Value, self).raise_with_self(*args, **kwargs)

    def raise_not_set(self, *args, **kwargs):
        kwargs['cls'] = self.not_set_error
        return self.raise_with_self(*args, **kwargs)

    def raise_set(self, *args, **kwargs):
        # TODO: Come up with extensions for the specific object.
        kwargs['cls'] = ValueSetError
        return self.raise_with_self(*args, **kwargs)

    def raise_locked(self, *args, **kwargs):
        kwargs['cls'] = self.locked_error
        return self.raise_with_self(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        kwargs['cls'] = self.required_error
        return self.raise_with_self(*args, **kwargs)

    def raise_not_required(self, *args, **kwargs):
        # TODO: Come up with extensions for the specific object.
        kwargs['cls'] = ValueNotRequiredError
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
        # TODO: Should we return the NOTSET here?  Maybe not, if we are
        # checking that it was set.
        self.assert_configured()
        if not self.default_provided:
            self.assert_not_required()
            assert self._default == constants.NOTSET
            return None
        assert self._default != constants.NOTSET
        return self._default

    @property
    def default_provided(self):
        """
        Returns whether or not the instance has been explicitly initialized
        with a default value.
        """
        return self._default != constants.NOTSET

    def pre_default(self):
        # TODO: Should we reset _defaulted here?
        self.assert_not_required()

    def post_default(self):
        # TODO: Do we need to worry about resetting this value to False in the
        # case that a non-default argument is provided?
        self._defaulted = True

    @property
    def defaulted(self):
        """
        Returns whether or not the instance has been defaulted.
        """
        # TODO: Cleanup this logic.
        # TODO: Should we maybe disallow access of this property if the defaultign
        # routine is in progress?
        self.assert_set()
        # NOTE: This might cause hairy behavior in the case that we are
        # re-defaulting the value (or setting the value to a non-default after
        # it has been defaulted the first time).
        return self.routines.defaulting.finished

        # # ?
        # if self.default_provided:
        #     assert self._defaulted is False
        # if self.defaulting_routine.finished:
        #     assert self._defaulted is True
        # else:
        #     # This assertion fails when the defaulting routine is IN_PROGRESS,
        #     # the assertion is coming from the value setter when it is being
        #     # defaulted.
        #     assert self._defaulted is False
        # return self._defaulted

    @property
    def defaulting(self):
        return self.routines.defaulting.in_progress

    @property
    def value(self):
        # TODO: Implement allow null checks.
        # TODO: Do we return the default here if the value is not provided?
        self.assert_set()
        assert self._value != constants.NOTSET

        if self._value is None:
            try:
                assert not self.required
                assert self.default_provided
            except AssertionError:
                import ipdb; ipdb.set_trace()
            return self.normalize(self.default)

        # This really only counts in the `obj:Option` case.
        return self.normalize(self._value)

    # TODO: The logic here needs to be cleaned up.
    # TODO: Incorporate allow_null checks.
    @value.setter
    def value(self, value):
        # TODO: Consider making the setting of the value a routine itself.
        self.assert_configured()

        # TODO: What do we do if the value is being set to a default or None
        # after it has already been set?
        if self.set:
            logger.debug("Overriding already set value.")

        # The value can be being set to None even if it is not the default.
        if value is None:
            self.assert_not_required()
            # self.assert_allow_null()
            if self.defaulting:
                # The value of defaulted will be set to True when the routine
                # finishes.
                self._value = None
            else:
                # If the default is also None, but we are not defaulting, do
                # we want to set the state as having been defaulted?
                if self.default == value:
                    logger.debug(
                        "The default is None, but we are also setting to "
                        "None explicitly... We have to be careful here."
                    )
                    raise Exception()  # Temporary - for sanity.
                self._value = value
        else:
            if self.set:
                if self.defaulted:
                    # TODO: What do we do in the case that the value is being
                    # defaulted to the same value that it is already set to?
                    if self.default == value:
                        logger.debug(
                            "The default is None, but we are also setting to "
                            "None explicitly... We have to be careful here."
                        )
                        raise Exception()  # Temporary - for sanity.
                    # We now have to clear the defaulted state!
                    self.routines.defaulting.reset()
                    self._value = value
                if value != self._value:
                    logger.debug(
                        "Not changing value since it is already set with "
                        "the same value."
                    )
                else:
                    self._value = value
            else:
                if self.default == value:
                    logger.debug(
                        "The default is None, but we are also setting to "
                        "None explicitly... We have to be careful here."
                    )
                    raise Exception()  # Temporary - for sanity.
                self._value = value

        self._set = True
        self.validate()
        self.post_set(value)

    def set_default(self):
        # TODO: We should maybe lax this requirement, and figure out if it is
        # truly necessary.
        self.assert_not_set(message=(
            "Cannot set the default when it has already been set."
        ))
        with self.routines.defaulting:
            self.value = None

    def reset(self):
        self.routines.defaulting.reset()
        self._value = constants.NOTSET
        self._defaulted = False
        self._set = False

    def post_set(self, value):
        if self._post_set is not None:
            self._post_set(value)

    def normalize(self, value):
        if self._normalize is not None:
            return self._normalize(value, self.parent)
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

        # If the validate method is being called from the parent class, we don't
        # want to call the parent provided validation method since it will
        # will introduce an infinite recursion.
        frame = inspect.stack()[1][0]
        cls = get_class_from_frame(frame)
        if cls != self.parent.__class__:
            if self._validate is not None:
                self._validate()

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
        (2) Not only do we need to validate against the default value, we need
            to validate against the normalized default value!
        (3) We need to do the validation with options against the default value
            and the default normalized value.
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
