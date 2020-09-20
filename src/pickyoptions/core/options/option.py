from copy import deepcopy
import logging
import six
import sys

from pickyoptions import settings, constants

from pickyoptions.core.base import lazy
from pickyoptions.core.exceptions import PickyOptionsError
from pickyoptions.core.decorators import require_set, accumulate_errors

from pickyoptions.core.configuration import (
    Configuration, Configurations, ConfigurationsConfigurableChild)
from pickyoptions.core.configuration.configuration_lib import (
    CallableConfiguration, TypesConfiguration)
from pickyoptions.core.configuration.exceptions import (
    ConfigurationDoesNotExistError)
from pickyoptions.core.configuration.utils import (
    require_configured, require_configured_property)

from .exceptions import (
    OptionInvalidError,
    OptionRequiredError,
    OptionTypeError,
    OptionNotSetError,
    OptionLockedError,
    OptionNotConfiguredError,
    OptionConfigurationError,
    OptionConfiguringError,
    OptionNotPopulatedError,
    OptionsInvalidError,
    OptionNotPopulatedPopulatingError,
    OptionPopulatedError,
    OptionNullNotAllowedError,
    OptionDoesNotExistError,
    OptionSetError,
    OptionNotRequiredError
)
from .mixins import PopulatingMixin


logger = logging.getLogger(settings.PACKAGE_NAME)


# TODO: Eventually we might want to move these to some sort of settings setup.
VALIDATE_NORMALIZED_VALUE_IF_SAME = False
VALIDATE_NORMALIZED_VALUE_IF_ORIGINAL_INVALID = True


class Option(ConfigurationsConfigurableChild, PopulatingMixin):
    """
    Represents a single configurable option in the `obj:Options` parent.

    Parameters:
    ----------
    field: `obj:str`
        The field that the value is associated with.

    required: `obj:bool` (optional)
        Whether or not the `obj:Option` value is required.  When the
        `obj:Options` are populated, if the value for a required `obj:Option`
        is not supplied an exception will be raised.

        Default: False

    default: `obj:object` (optional)
        The default value for the `obj:Option` if the `obj:Option`
        is not required and a value is not provided.

        Note that this is only applicable in the case that the `obj:Option`
        is not required.

        Default: None

    # TODO: Currently not implemented.
    allow_null: `obj:bool` (optional)
        Whether or not the `obj:Option` is allowed to take on null values.

        Default: True

    # TODO: Currently not implemented.
    # TODO: Is this true?  Can we override if it is already locked?
    locked: `obj:bool` (optional)
        Whether or not the `obj:Option` value is allowed to be overridden.

        Default: False

    types: `obj:type` or `obj:list` or `obj:tuple` (optional)
        Either a single `obj:type` or an iterable of `obj:type`(s) that the
        `obj:Option` value must adhere to.  If the types are specified and a
        value provided for the `obj:Option` is not of those types, an
        exception will be raised.

        It is important to note that the types are also used to check against
        the default.

        Default: None

    validate: `obj:func` (optional)
        A validation method that determines whether or not the value provided
        for the `obj:Option` is valid.  The provided method must take the
        raw value as it's first argumentt and the `obj:Option` as it's second
        argument.

        It is important to note that the validate method will be applied to
        both the provided `obj:Option` value and the `obj:Option`'s - so both
        must comply.

        Default: None

    normalize: `obj:func` (optional)
        A normalization method that normalizes the provided value to the
        `obj:Option`.

        It is important to note that the normalization method will be applied to
        both the provided `obj:Option` value and the `obj:Option`'s - so both
        must comply.

        Default: None

    help_text: `obj:str` (optional)
        Default: ""

    TODO:
    ----
    - Should we maybe add a property that validates the type of value provided
      if it is not `None`?  This would allow us to have a non-required value
      type checked if it is provided.  This would be a useful configuration
      for the `obj:Option` and `obj:Options`.
    - Implement on validation error hook.
    - Come up with state for the Option.
    """
    __abstract__ = False

    errors = {
        # Child Implementation Properties
        'does_not_exist_error': OptionDoesNotExistError,
        'not_set_error': OptionNotSetError,
        'set_error': OptionSetError,
        'locked_error': OptionLockedError,
        'required_error': OptionRequiredError,
        'not_required_error': OptionNotRequiredError,
        'invalid_error': OptionInvalidError,
        'invalid_type_error': OptionTypeError,
        'not_null_error': OptionNullNotAllowedError,
        # Configurable Implementation Properties
        'not_configured_error': OptionNotConfiguredError,
        'configuring_error': OptionConfiguringError,
        'configuration_error': OptionConfigurationError,
        # Populated Implementation Properties
        'not_populated_error': OptionNotPopulatedError,
        'not_populated_populating_error': OptionNotPopulatedPopulatingError,
        'populated_error': OptionPopulatedError,
    }

    # Child Implementation Properties
    parent_cls = 'Options'

    configurations = Configurations(
        Configuration('default', default=constants.EMPTY),
        Configuration('required', types=(bool, ), default=False),
        Configuration('allow_null', types=(bool, ), default=False),
        Configuration('locked', types=(bool, ), default=False),
        Configuration('post_process_on_default', types=(bool, ), default=False),
        # TODO: Consider allowing types to take on None as a value.
        Configuration('enforce_types_on_null', types=(bool, ), default=True),
        TypesConfiguration('types'),
        CallableConfiguration(
            'validate',
            num_arguments=2,
            error_message=(
                "Must be a callable that takes the option value as it's "
                "first argument and the option instance as it's second "
                "argument."
            )
        ),
        CallableConfiguration(
            'validate_with_options',
            num_arguments=3,
            error_message=(
                "Must be a callable that takes the option value as it's "
                "first argument, the option instance as it's second argument "
                "and the overall combined options instance as it's third "
                "argument."
            )
        ),
        CallableConfiguration(
            'normalize',
            num_arguments=2,
            error_message=(
                "Must be a callable that takes the option value as it's "
                "first argument and the option instance as it's second "
                "argument."
            )
        ),
        CallableConfiguration(
            'post_process',
            num_arguments=2,
            error_message=(
                "Must be a callable that takes the option value as it's "
                "first argument and the option instance as it's second "
                "argument."
            )
        ),
        CallableConfiguration(
            'post_process_with_options',
            num_arguments=3,
            error_message=(
                "Must be a callable that takes the option value as it's "
                "first argument, the option instance as it's second argument "
                "and the overall combined options instance as it's third "
                "argument."
            )
        ),
        Configuration("help_text", default="", types=six.string_types),
        validation_error=OptionInvalidError,
    )

    def __init__(self, field, **kwargs):
        super(Option, self).__init__(field, **kwargs)
        self.save_initialization_state(**kwargs)

        self._value = constants.NOTSET
        self._defaulted = False
        self._set = False

        self.create_routine(id="populating")
        self.create_routine(id="overriding")
        self.create_routine(id="restoring")

    def __lazyinit__(self, **kwargs):
        # Do we really want to do this lazily?  It might hide bugs that are
        # internal due to internal configurations set on the Option...
        super(Option, self).__lazyinit__(**kwargs)
        self.assert_configured()

    @lazy
    def __deepcopy__(self, memo):
        cls = self.__class__
        explicit_configuration = deepcopy(
            self.configurations.explicitly_set_configurations, memo)
        result = cls.__new__(cls, self.field, **explicit_configuration)
        result.__init__(self.field, **explicit_configuration)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            object.__setattr__(result, k, deepcopy(v, memo))
        return result

    def __repr__(self):
        # TODO: Come up with state for the option.
        if self.initialized:
            return "<{cls_name} field={field}>".format(
                cls_name=self.__class__.__name__,
                field=self.field,
            )
        return "<{cls_name}>".format(cls_name=self.__class__.__name__)

    def __getattr__(self, k):
        # We cannot decorate with lazy_init right now - we should find a better
        # way of doing that.  It causes infinite recursion.

        # NOTE: It is important to prevent the `obj:Option` from trying to get
        # privately scoped variables from the `obj:Configurations` object.  It
        # can lead to bugs in the case that the attribute does not exist on the
        # `obj:Option` but does exist on the `obj:Configurations`.
        if k.startswith('_'):
            raise AttributeError("The attribute %s does not exist." % k)

        # We want to use the explicit .get_configuration() method because there
        # are cases where an attribute might exist on the `obj:Configurations`
        # but is not a `obj:Configuration`.  We want to restrict the __getattr__
        # for public use only.
        try:
            configuration = self.configurations.get_configuration(k)
        except ConfigurationDoesNotExistError:
            if settings.DEBUG:
                raise AttributeError("The attribute %s does not exist." % k)
            six.reraise(*sys.exc_info())
        else:
            # This will only ever be True if we are entering a recursion, which
            # this check blocks.
            # if not self.__lazy_initializing__:
            #     self.perform_lazy_init()

            # Wait to make the assertion down here so that __hasattr__ will return
            # False before checking if the `obj:Option` is configured.v
            self.assert_configured()
            configuration.assert_set()
            return configuration.value

    @property
    def field(self):
        return self._field

    @require_configured_property
    def types(self):
        # TODO: Should we allow this to be setable?  What about the other
        # configurations?
        configuration = self.configurations['types']
        assert configuration.set
        return configuration.value

    @require_configured_property
    def locked(self):
        """
        Returns whether or not the `obj:Option` is locked.  In the case that the
        `obj:Option` is locked, it cannot be overridden.
        """
        # TODO: Should we allow this to be setable?  What about the other
        # configurations?
        configuration = self.configurations['locked']
        assert configuration.set
        return configuration.value

    @require_configured_property
    def enforce_types_on_null(self):
        """
        Returns whether or not to enforce the `types` configuration parameter
        when the `obj:Option` supplied value is None.
        """
        configuration = self.configurations['enforce_types_on_null']
        assert configuration.set
        return configuration.value

    @require_configured_property
    def required(self):
        """
        Returns whether or not the `obj:Option` is required.  If the `obj:Option`
        is required, an explicit value is required to be supplied during
        population.
        """
        # TODO: Should we allow this to be setable?  What about the other
        # configurations?
        configuration = self.configurations['required']
        assert configuration.set
        return configuration.value

    @require_configured_property
    def post_process_on_default(self):
        # TODO: Should we allow this to be setable?  What about the other
        # configurations?
        configuration = self.configurations['required']
        assert configuration.set
        return configuration.value

    @require_configured_property
    def default_provided(self):
        """
        Returns whether or not the instance has been explicitly initialized
        with a default value.
        """
        configuration = self.configurations['default']
        configuration.assert_configured()
        configuration.assert_set()
        return configuration.provided

    @property
    def set(self):
        if self._set:
            assert self._value != constants.NOTSET
        else:
            assert self._value == constants.NOTSET
        return self._set

    @property
    def provided(self):
        # What about the case when the default is explicitly provided?
        return self._value != constants.EMPTY

    @property
    def empty(self):
        return self._value == constants.EMPTY

    @property
    def defaulted(self):
        self.assert_set()
        return self._defaulted

    @property
    def value(self):
        # TODO: Implement allow null checks.
        # TODO: Do we return the default here if the value is not provided?
        self.assert_set()
        if self.empty:
            assert not self.required
            assert self.default != constants.NOTSET
            assert self.default != constants.EMPTY
            # Note: This will allow None values to go through.
            return self.do_normalize(self.default)
        return self.do_normalize(self._value)

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
        # TODO: Do we want to only validate the value if the value is not EMPTY?
        self.do_validate(value=value)

        # TODO: Double check this logic here.
        # If the `obj:Option` is required, the default is None (since
        # _default is EMPTY).  This means that if the value equals the default,
        # the value is None which is now allowed for the required case - meaning,
        # this case only counts for the non-required case.
        if value == self.default:
            # I don't think this assertion is okay, because the value might be
            # explicitly provided as the default?  What about when it is required,
            # the default is None?
            assert not self.required  # Is this okay?
            logger.warning(
                "Setting the value as %s when that is the default, "
                "this will cause the configuration to be defaulted." % value
            )
            self._defaulted = True
            self._value = constants.EMPTY
        # The value will be EMPTY if and only if we are defaulting.
        elif value == constants.EMPTY:
            assert not self.required
            self._defaulted = True
            self._value = constants.EMPTY
        else:
            self._defaulted = False
            self._value = value

        self._set = True

        # TODO: We should only trigger this logic if the value has been changed.
        # This requires keeping track of the previous value.

        # Note: We also have to check for cases where the default value is
        # explicitly provided!
        if ((value == constants.EMPTY and self.post_process_on_default is True)
                or value != constants.EMPTY):
            self.do_post_process()
            if not self.routines.subsection(
                    ['populating', 'overriding', 'restoring']).any('in_progress'):
                self.do_post_process_with_options()

        # If the `obj:Option` is populating, overriding or restoring,
        # validation and post processing routines with options will be run after
        # the routine finishes.
        if not self.routines.subsection(
                ['populating', 'overriding', 'restoring']).any('in_progress'):
            self.do_validate_with_options()

    def post_routine_with_options(self):
        # TODO: Right now, there is no way for us to tell the difference between
        # an option that was populated or defaulted - this is called from the
        # `obj:Options` routine.  For that reason, it will post_process options
        # that are defaulted - but we're not sure if we want that.
        if ((self.defaulted and self.post_process_on_default is True)
                or not self.defaulted):
            self.do_post_process_with_options()
        self.do_validate_with_options()

    def set_default(self, sender=None):
        """
        Sets the state of the `obj:Option` to it's configured default.
        """
        # When setting the default internally, we allow the default to be set
        # when the `obj:Option` has already been set.
        if not (sender and isinstance(sender, self.__class__)):
            # TODO: We should consider laxing this requirement.
            self.assert_not_set(message=(
                "Cannot set the default when it has already been set."
            ))
        # The value of _defaulted is set in the value setter.
        self.value = constants.EMPTY
        assert self.defaulted is True

    def do_normalize(self, value):
        assert value != constants.EMPTY and value != constants.NOTSET
        if self.normalize is not None:
            return self.normalize(value, self.parent)
        return value

    @lazy
    def reset(self):
        """
        Resets the `obj:Option` back to it's pre-populated state.

        This occurs whenever the `obj:Option` is populated, but not when the
        `obj:Option` is overridden or restored.
        """
        self._value = constants.NOTSET
        self._defaulted = False
        self._set = False
        self._history = []

        # If initialized, all of the routines we want to reset will be present.
        assert self.initialized

        # We cannot reset the configuration routine because then the option
        # will not be configured anymore.
        self.routines.subsection(
            ['populating', 'restoring', 'overriding']).reset()

    @property
    def overridden(self):
        return self.routines.overriding.finished

    @require_set
    def override(self, value):
        """
        Overrides the populated or defaulted `obj:Option` with the provided
        value.  The override will be cleared in the event that the `obj:Option`
        is restored.

        Note that this does not trigger lazy initialization, since it requires
        that the `obj:Option` was already set.

        TODO:
        ----
        - What to do if the `obj:Option` is overridden explicitly with None
          or it's default?
        """
        # This check is also done in the value setter, but is it more appropriate
        # here?  What about external sets?
        if self.set and self.locked:
            self.raise_locked()

        with self.routines.overriding as routine:
            routine.register(value)
            self.value = value

    @lazy
    def populate(self, value, sender=None):
        # Note: The individual `obj:Option` is reset by the parent `obj:Options`
        # on population - so we don't need to do it manually here...
        from .options import Options
        if not sender or not isinstance(sender, Options):
            self.reset()
        # I don't think this assertion is okay, since it means that the default
        # cannot be explicitly provided.
        assert value != self.default  # Is this okay?
        with self.routines.populating as routine:
            routine.register(value)
            self.value = value

    @require_set
    def restore(self):
        """
        Restores the `obj:Option` back to it's state immediately after it was
        populated by wiping any applied overrides.

        Note that this does not trigger lazy initialization, since it requires
        that the `obj:Option` was already set.

        Note that we cannot require that the `obj:Option` is populated, since
        defaulted `obj:Option`(s) can be overridden, and thus should be
        restored.
        """
        # If the `obj:Option` is not overridden, it is already in it's populated
        # or originally defaulted state, so there is no need to restore.
        if not self.overridden:
            logger.debug(
                "The option %s has not been overridden and thus cannot be "
                "restored." % self.field
            )

        with self.routines.restoring:
            # The populating history can still be 0 if the default was
            # originally set when  populating but the default value was
            # overridden - hence no populated value.
            # To restore, we have to set back to it's default...
            # TODO: There should be a better way of doing this, we should
            # just keep track of the  value it was initially set to.
            assert len(self.routines.populating.history) in (0, 1)
            if len(self.routines.populating.history) == 0:
                logger.debug(
                    "The option %s was overridden but never populated - "
                    "it's default value was used.  Restoring it's value "
                    "back to that default." % self.field
                )
                assert not self.required
                self.set_default(sender=self)
            else:
                # Note: This is going to trigger redundant validation of the
                # value, but that is not a big deal.
                self.value = self.routines.populating.history[0]

    # We cannot require populated or populating because this will be applied
    # in some cases for defaulted options.
    # Really?  We might want to rethink that.
    @require_set
    def do_post_process(self):
        """
        Performs post-processing of the `obj:Option` immediately after the "
        "`obj:Option` is either populated, overridden or restored.  This "
        "post-processing is independent of the parent `obj:Options` and thus "
        "does not wait for the associated routine of the `obj:Options` to
        finish before being applied.

        This post-processing is defined by the parameter `post_process` "
        "provided to the `obj:Option` on initialization.

        Since this post-processing does not reference the overall `obj:Options`
        instance (and is performed independently of the overall `obj:Options` "
        "instance) it does not wait for the `obj:Options` routine to finish,
        but instead is immediately called when the `obj:Option` finishes
        populating, overriding or restoring.
        """
        if self.post_process is not None:
            self.post_process(self.value, self)

    # We cannot require populated or populating because this will be applied
    # in some cases for defaulted options.
    # Really?  We might want to rethink that.
    @require_set
    def do_post_process_with_options(self):
        """
        Performs post-processing of the `obj:Option` with a reference to the
        parent `obj:Options` after the `obj:Option` has either been populated,
        overridden or restored AND after the parent `obj:Options` have left the
        context of a routine.  This post-processing is defined by the parameter
        `post_process_with_options` provided to the `obj:Option` on
        initialization.

        The routine performs operations on a group of `obj:Option`(s)
        simultaneously, so it is necessary to  wait for the routine to finish
        before applying this logic so that the `obj:Options` being used reflect
        the newest values after all the operations on the individual
        `obj:Option`(s) finished.

        TODO:
        ----
        - Asserting that the parent routine has finished here causes issues
          when we want to either populate, restore or override the option
          individually.  We should figure out a way the following possible:

          >>> options = Options()
          >>> option = Option(..., parent=options)
          >>> option.populate(...)

          In the above, the parent `obj:Options` routine will not have been
          triggered like it would be in the case that we called
          options.populate().

        - We used to assert that the parent population routine had finished,
          but this method now applies to more than one routine.  We  don't know
          what routine is being referenced for any given call, so we cannot
          assert that a specific routine has finished.  We should build this
          capability in, so the methods have more context about what routine they
          are being called in association with.
        """
        if self.post_process_with_options is not None:
            self.post_process_with_options(self.value, self, self.parent)

    # NOTE: Here we can probably get away with not accumulating the errors but
    # just raising them, since only one error will ever accumulate.
    @require_configured
    @accumulate_errors(error_cls='invalid_error', name='field')
    def _do_user_provided_validation(self, value, func, name, *args):
        """
        Applies the user provided validation method to the `obj:Option`.
        """
        configuration = self.configurations[name]
        try:
            # NOTE: This accounts for the default value and the value after
            # normalization.  This might be overkill if the value was defaulted,
            # since there is an earlier check that the validation passes for the
            # default value... nonetheless it is more complete this way.
            result = func(value, self, *args)
        except Exception as e:
            # TODO: Maybe we should lax this requirement.  The caveat is that
            # other exceptions could be swallowed and a misleading configuration
            # related exception would disguise them.
            if isinstance(e, (OptionsInvalidError, OptionInvalidError)):
                # NOTE: This logic breaks apart if the default value was altered
                # by the normalization.  We should also check the normalized
                # default value in the configuration validation.
                if self.value_instance.defaulted:
                    raise PickyOptionsError(
                        "The value is defaulted and the default does not "
                        "pass validation.  The default value should have been "
                        "validated before hand."
                    )
                e.value = value
                yield e
            else:
                yield configuration.raise_invalid(
                    return_exception=True,
                    children=[e],
                    message=(
                        "If raising an exception to indicate that the option is "
                        "invalid, the exception must be an instance of "
                        "OptionInvalidError or OptionsInvalidError."
                        "\nIt is recommended to use the `raise_invalid` method "
                        "of the passed in option or options instance."
                    )
                )
        else:
            if isinstance(result, six.string_types):
                yield self.raise_invalid(
                    return_exception=True,
                    value=value,
                    message=result
                )
            elif result is not None:
                yield configuration.raise_invalid(
                    return_exception=True,
                    message=(
                        "The option validate method must return a string error "
                        "message or raise an instance of OptionInvalidError or "
                        "OptionsInvalidError in the case that the value is "
                        "invalid. If the value is valid, it must return None."
                    )
                )

    @require_configured
    def do_validate_with_options(self, value=None):
        """
        Performs validation of the `obj:Option` with a reference to the parent
        `obj:Options` after the `obj:Option` has either been populated,
        overridden or restored AND after the parent `obj:Options` have left the
        context of a routine.  This validation is defined by the parameter
        `validate_with_options` provided to the `obj:Option` on initialization.

        The routine performs operations on a group of `obj:Option`(s)
        simultaneously, so it is necessary to  wait for the routine to finish
        before applying this logic so that the `obj:Options` being used reflect
        the newest values after all the operations on the individual
        `obj:Option`(s) finished.

        Parameters:
        ----------
        value: `obj:any` (optional)
            The value to validate.  This is optionally provided because there
            are cases where we want to perform the validation preemptively
            on a default or normalized default value.

            Default: `obj:Option` instance value

        TODO:
        ----
        - Asserting that the parent routine has finished here causes issues
          when we want to either populate, restore or override the option
          individually.  We should figure out a way the following possible:

          >>> options = Options()
          >>> option = Option(..., parent=options)
          >>> option.populate(...)

          In the above, the parent `obj:Options` routine will not have been
          triggered like it would be in the case that we called
          options.populate().

        - We used to assert that the parent population routine had finished,
          but this method now applies to more than one routine.  We  don't know
          what routine is being referenced for any given call, so we cannot
          assert that a specific routine has finished.  We should build this
          capability in, so the methods have more context about what routine they
          are being called in association with.
        """
        # TODO: Should we call the `obj:Options` parent validation routine?
        # In the case that the `obj:Option` is instantiated individually?
        value = value or self.value
        if self.validate_with_options is not None:
            self._do_user_provided_validation(
                value,
                self.validate_with_options,
                'validate_with_options',
                self.parent
            )

    @require_configured
    @accumulate_errors(error_cls='invalid_error', name='field')
    def do_validate_value(self, value, detail=None, **kwargs):
        """
        Validates the provided value based on the configuration specifications
        of the `obj:Option`.  When the value is deemed invalid, the errors are
        accumulated together into an overall error.

        Parameters:
        ----------
        value: `obj:any`
            The value to validate based on the configuration parameters of the
            `obj:Option`.

        detail: `obj:str` (optional)
            Additional detail to include in the errors if the value is deemed
            invalid for any reason.

            Default: None

        TODO:
        ----
        - Start using a validation error specific to each object?
        - Log a warning if the value is being explicitly set as the default
          value.
        """
        # If the value is EMPTY, it will trigger the default value to be used.
        # The default value and normalized default value should have already
        # been validated.
        if value == constants.EMPTY:
            # If the `obj:Option` is required, an exception should have already
            # been raised to disallow providing the default.
            if self.required:
                # Sanity checks - leave for time being.
                assert not self.default_provided
                assert self.default is None
                yield self.raise_required(
                    return_exception=True,
                    detail=detail,
                )
        else:
            # Here, the value is explicitly provided as None.
            if value is None:
                # If the `obj:Option` is required and we do not allow null
                # values, raise the Exception as a required error.
                if self.required and not self.allow_null:
                    yield self.raise_required(
                        return_exception=True,
                        detail=detail
                    )
                # If the `obj:Option` does not allow null but is not required,
                # raise to indicate that the `obj:Option` does not allow null.
                elif not self.allow_null:
                    yield self.raise_null_not_allowed(
                        return_exception=True,
                        detail=detail
                    )
                # If the `obj:Option` value is null, it does not conform to the
                # types (if specified).
                elif self.enforce_types_on_null and self.types is not None:
                    yield self.raise_invalid_type(
                        return_exception=True,
                        detail=detail,
                        types=self.types
                    )
            else:
                if self.types is not None:
                    configuration = self.configurations['types']
                    if not configuration.conforms_to(value):
                        yield self.raise_invalid_type(
                            return_exception=True,
                            detail=detail,
                            types=self.types
                        )

        # TODO: Since the default and normalized default are already checked in
        # the configuration validation, should we only perform validation here
        # if the value is not EMPTY?
        if self.validate is not None:
            # TODO: Should we be transforming this in some way instead of just
            # appending the children?
            yield self._do_user_provided_validation(
                value, self.validate, 'validate', return_children=True)

    @require_configured
    @accumulate_errors(error_cls='invalid_error', name='field')
    def do_validate(self, **kwargs):
        """
        Performs validation of the `obj:Option` immediately after the
        `obj:Option` is either populated, overridden or restored.  This
        validation is independent of the parent `obj:Options` and thus does not
        wait for the associated routine of the `obj:Options` to finish before
        being applied.

        This validation is defined by the parameter `validate` provided to the
        `obj:Option` on initialization.

        Parameters:
        ----------
        value: `obj:any` (optional)
            The value to validate.  This is optionally provided so that this
            method can be called externally to validate the existing value on
            the `obj:Option`.

            Default: `obj:Option` instance value
        """
        if 'value' in kwargs:
            value = kwargs.pop('value')
            errors = self.do_validate_value(value, return_children=True)
            yield errors

            # If the original value was not valid and the settings indicate
            # we should not validate the normalized value in this case, do not
            # validate the normalizd value.
            if (len(errors) != 0
                    and not VALIDATE_NORMALIZED_VALUE_IF_ORIGINAL_INVALID):
                return

            # Validate the normalized value if it is applicable.
            if self.normalize is not None:
                # TODO: In the case that the value is defaulted, the normalized
                # default will have already been validated in the configuration
                # validation, so maybe we should skip that condition?
                normalized_value = self.do_normalize(value)
                if normalized_value != value or VALIDATE_NORMALIZED_VALUE_IF_SAME:
                    # TODO: Maybe we should wrap this in some kind of different
                    # exception to make it more obvious what is going on.
                    yield self.do_validate_value(
                        normalized_value,
                        return_children=True,
                        detail="(Normalized Value)"
                    )
        else:
            # If being called externally, the value must be SET - otherwise,
            # there is no value to validate.
            self.assert_set()
            yield self.do_validate(value=self.value, return_children=True)

    @accumulate_errors(error_cls='configuration_error', name='field')
    @require_configured
    def validate_configuration(self):
        """
        Validates the parameters of the `obj:Option` configuration after it
        is configured.

        This validation is independent of any value that would be set on the
        `obj:Option`, so it runs lazily after initialization and when
        individual configuration values are altered, but not when the\
        `obj:Option` value is changed..
        """
        # Validate that the default is not provided in the case that the value
        # is required.
        if self.required is True:
            # TODO: Do we really want to raise an exception here?  Maybe we should
            # just log a warning?
            if self.default_provided:
                configuration = self.configurations['default']
                yield configuration.raise_invalid(
                    return_exception=True,
                    message=(
                        "Cannot provide a default value for option "
                        "{name} because the option is required."
                    )
                )
        else:
            # If the value is not required, issue a warning if the default is not
            # explicitly provided.
            if not self.default_provided:
                logger.warning(
                    "The option for `%s` is not required and no default "
                    "value is specified. The default value will be `None`."
                    % self.field
                )

            # Note: This will also validate the default normalized value.
            errors = self.do_validate(
                value=self.default,
                return_children=True
            )
            if errors:
                # TODO: Right now this will display the error as an Invalid Option
                # nested under an Invalid Configuration Error.  The Invalid Option
                # is slightly misleading because it indicates that the option
                # value is invalid, instead of the fact that that the
                # configuration value does not conform to the option specs.
                configuration = self.configurations['default']
                yield configuration.raise_invalid(
                    return_exception=True,
                    children=errors,
                    value=self.default,
                    detail=(
                        "If providing a default value, the default value must "
                        "also conform to the configuration specifications on "
                        "the option."
                    )
                )
