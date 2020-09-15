from copy import deepcopy
import logging
import six
import sys

from pickyoptions import settings, constants

from pickyoptions.core.base import track_init
from pickyoptions.core.configuration import Configuration, Configurations
from pickyoptions.core.configuration.configurable import Configurable
from pickyoptions.core.configuration.configuration_lib import (
    CallableConfiguration)
from pickyoptions.core.configuration.exceptions import (
    ConfigurationDoesNotExist)
from pickyoptions.core.configuration.configuration_lib import (
    TypesConfiguration)
from pickyoptions.core.exceptions import PickyOptionsError
from pickyoptions.core.family import Child
from pickyoptions.core.value.valued import Valued

from .exceptions import (
    OptionInvalidError,
    OptionRequiredError,
    OptionTypeError,
    OptionNotSetError,
    OptionLockedError,
    OptionNotConfiguredError,
    OptionConfigurationError,
    OptionConfiguringError,
)

logger = logging.getLogger(settings.PACKAGE_NAME)


# TODO: Come up with state for the option.
class Option(Configurable, Child, Valued):
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
    (1) Should we maybe add a property that validates the type of value provided
        if it is not `None`?  This would allow us to have a non-required value
        type checked if it is provided.  This would be a useful configuration
        for the `obj:Option` and `obj:Options`.
    (2) Should we maybe add a `validate_after_normalization` boolean property?
    (3) The `allow_null` configuration might cause issues with the `default`
        property if the default value is None.  We should handle that more
        appropriately.
    """
    # SimpleConfigurable Implementation Properties
    not_configured_error = OptionNotConfiguredError
    configuring_error = OptionConfiguringError
    configuration_error = OptionConfigurationError

    # Valued Implementation Properties
    not_set_error = OptionNotSetError  # Also used by Child implementation
    locked_error = OptionLockedError  # Also used by Child implementation
    required_error = OptionRequiredError  # Also used by Child implementation
    invalid_error = OptionInvalidError  # Also used by Child implementation
    invalid_type_error = OptionTypeError  # Also used by Child implementation

    # Child Implementation Properties
    parent_cls = 'Options'
    child_identifier = "field"
    does_not_exist_error = ConfigurationDoesNotExist

    # TODO: We should consider moving this inside the instance, because it might
    # be causing code to be run unnecessarily on import.  We should at least
    # make them lazy initialized.
    configurations = Configurations(
        Configuration('default', default=constants.NOTSET),
        Configuration('required', types=(bool, ), default=False),
        Configuration('allow_null', types=(bool, ), default=True),
        Configuration('locked', types=(bool, ), default=False),
        TypesConfiguration('types'),
        # TODO: We might want to eventually move the validate and post_process
        # to the Valued instance...  But then we would have to be concerned with
        # including the instance and other arguments in the call.
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
        # Should post_process be moved to the `Value` level?
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
    )

    @track_init
    def __init__(self, field, **kwargs):
        # Initialize with all of the configurations and pass the relevant post
        # configured values to the Valued instance.
        # TODO: Ideally, we would do the separate configuration inside the Valued
        # class - but that might cause circular dependencies.
        Configurable.__init__(self, **kwargs)
        Valued.__init__(
            self,
            field,
            default=self.default,
            required=self.required,
            allow_null=self.allow_null,
            locked=self.locked,
            types=self.types,
            post_set=self.post_set,
            validate=self.do_validate,
            normalize=self.normalize,  # Will be called with this parent.
        )
        Child.__init__(self, parent=kwargs.pop('parent', None))

        # Note: Configurable implements Routined already.
        self.create_routine(id="populating")
        self.create_routine(id="overriding")
        self.create_routine(id="restoring")

        self.assert_configured()

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
        # TODO: Keep track of the state of the Option as an attribute...
        return "<{cls_name} state={state}>".format(
            cls_name=self.__class__.__name__,
            # state=constants.NOT_INITIALIZED
            state="NOT_INITIALIZED"
        )

    def __getattr__(self, k):
        configuration = getattr(self.configurations, k)
        # Wait to make the assertion down here so that __hasattr__ will return
        # False before checking if the `obj:Option` is configured.
        self.assert_configured()
        configuration.assert_set()
        return configuration.value

    @property
    def validation_errors(self):
        from pickyoptions.core.options.exceptions import OptionsInvalidError
        return (OptionsInvalidError, OptionInvalidError)

    def post_set(self, value):
        # We do this here instead of at the end of the routines so these always
        # run when the value is updated.
        # I think this might be causing the value to be validated twice?
        # Isn't the validate configuration already getting called in the routine?

        # TODO: IMPORTANT: The value instance calls the provided validation
        # in it's value setter, so this might be doing it twice?
        # self.do_validate()
        self.do_post_process()

        # TODO: Do we have to worry about other routines here?
        # If the `obj:Option` is populating, overriding or restoring,
        # validation and post processing routines with options will be run after
        # the routine finishes.
        if not self.routines.any('in_progress'):
            self.post_routine_with_options()

    def reset(self):
        self.value_instance.reset()  # Resets the values/defaults.
        # If initialized, all of the routines we want to reset will be present.
        # Otherwise, it will just be the configuration routine - which we don't
        # want to reset.  Do we have to worry about the defaulting routine?
        assert 'defaulting' not in [routine.id for routine in self.routines]
        if self.initialized:
            self.routines.subsection(
                ['populating', 'overriding', 'restoring']).reset()

    def override(self, value):
        # Once the `obj:Option` is overridden, the default is no longer set - even
        # if the default is what is used to populate the `obj:Option`.
        # TODO: If the `obj:Option` is overridden with `None`, and the `default`
        # exists, should it revert to the default?  This needs to be tested.
        with self.routines.overriding as routine:
            routine.register(value)
            self.value = value

    def populate(self, value):
        # Once the `obj:Option` is populated, the default is no longer set - even
        # if the default is what is used to populate the `obj:Option`.
        # TODO: If the `obj:Option` is overridden with `None`, and the `default`
        # exists, should it revert to the default?  This needs to be tested.
        with self.routines.populating as routine:
            routine.register(value)
            self.value = value

    def restore(self):
        with self.routines.restoring:
            if self.defaulted:
                assert len(self.routines.populating.history) == 0
                logger.debug(
                    "Not restoring option %s because it is already in its "
                    "default state." % self.identifier
                )
            else:
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
                        "back to that default." % self.identifier
                    )
                    assert not self.required
                    configuration = self.configurations['default']
                    self.value = configuration.value
                else:
                    self.value = self.routines.populating.history[0]

    def post_routine_with_options(self):
        logger.debug(
            "Performing post routine on %s, field = %s, with parent "
            "options." % (self.__class__.__name__, self.field)
        )
        self.do_validate_with_options()
        self.do_post_process_with_options()

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

    def _do_user_provided_validation(self, value, func, name, *args):
        """
        Applies the user provided validation method to the `obj:Option`.
        """
        from pickyoptions.core.options.exceptions import OptionsInvalidError

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
                six.reraise(*sys.exc_info())
            else:
                configuration.raise_invalid(
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
                self.raise_invalid(value=self.value, message=result)
            elif result is not None:
                configuration.raise_invalid(message=(
                    "The option validate method must return a string error "
                    "message or raise an instance of OptionInvalidError or "
                    "OptionsInvalidError in the case that the value is invalid. "
                    "If the value is valid, it must return None."
                ))

    def do_validate(self, value=None, sender=None):
        """
        Performs validation of the `obj:Option` immediately after the
        `obj:Option` is either populated, overridden or restored.  This
        validation is independent of the parent `obj:Options` and thus does not
        wait for the associated routine of the `obj:Options` to finish before
        being applied.

        This validation is defined by the parameter `validate` provided to the
        `obj:Option` on initialization.

        Since this validation does not reference the overall `obj:Options`
        instance (and is performed independently of the overall `obj:Options`
        instance) it does not wait for the `obj:Options` routine to finish, but
        instead is immediately called when the `obj:Option` finishes populating,
        overriding or restoring.

        Parameters:
        ----------
        value: `obj:any` (optional)
            The value to validate.  This is optionally provided because there
            are cases where we want to perform the validation preemptively
            on a default or normalized default value.

            Default: `obj:Option` instance value

        sender: `obj:type` (optional)
            The class of the instance calling the method, if applicable.

            If we call the method on the `obj:Option` externally, we want it to
            also perform the validation on the `obj:Value` instance itself.  If
            the method on the `obj:Option` is called internally by the
            `obj:Value` instance, we don't want to perform the validation
            inside the `obj:Value` instance.

            Default: None
        """
        value = value or self.value

        # TODO: IMPORTANT: The value instance calls the provided validation
        # in it's value setter, so this might be doing it twice?  It also
        # gets called by the post_set method...
        if not sender or isinstance(sender, self.__class__):
            self.value_instance.validate(sender=self)

        # Perform user provided validation.
        # TODO: Maybe we should move this logic to the Value instance.
        if self.validate is not None:
            self._do_user_provided_validation(value, self.validate, 'validate')

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
        value = value or self.value
        if self.validate_with_options is not None:
            self._do_user_provided_validation(
                value,
                self.validate_with_options,
                'validate_with_options',
                self.parent
            )

    def validate_configuration(self):
        """
        Performs validation for the `obj:Option` configuration for
        configurations that depend on one another.  This is performed after the
        entire `obj:Option` is configured.  On the other hand, individual
        configuration validation routines are performed when the `obj:Option`
        is configured with each individual configuration value.

        TODO:
        ----
        Maybe we should put this method in the context of the
        `obj:Configurations`, not the `obj:Option` - and pass it into the
        `obj:Configurations` on initialization.

        We need to validate with options against the default value and the
        default normalized value.
        """
        assert self.configured

        default_configuration = self.configurations['default']
        types_configuration = self.configurations['types']
        required_configuration = self.configurations['required']

        assert (
            types_configuration.value is None
            or type(types_configuration.value) is tuple
        )

        # If the default value is provided, ensure that the default value conforms
        # to the types specified by `types` if they are provided.
        # TODO: Should we be checking if default_configuration.set here?  This
        # will not be validating against default values for the default
        # configuration.
        # TODO: We need to check the normalized default value as well!
        # TODO: I don't think this matters whether or not it is configured, since
        #
        if default_configuration.configured:
            if not types_configuration.conforms_to(default_configuration.value):
                default_configuration.raise_invalid_type(
                    types=self.types,
                    value=default_configuration.value,
                    message=(
                        "If enforcing that the option be of type {types}, "
                        "the default value must also be of the same types."
                    )
                )

        # If the default value is not explicitly provided but the option is not
        # required, make sure that the default-default value conforms to the types
        # specified by `types` if they are provided.
        # TODO: We need to check the normalized default value as well!
        elif required_configuration.value is False:
            if not types_configuration.conforms_to(default_configuration.value):
                # TODO: We should figure out a more user-friendly way around this,
                # perhaps an additional configuration variable that only enforces
                # types if provided.
                types_configuration.raise_invalid(message=(
                    "If the option is not required but `types` is "
                    "specified, the default value, in this case None, must also "
                    "conform to the types specified by `types`.  Either "
                    "make the option required or provide a default that conforms "
                    "to the types."
                ))
