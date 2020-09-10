from copy import deepcopy
import logging
import six
import sys

from pickyoptions import constants, settings

from pickyoptions.base import track_init
from pickyoptions.child import Child
from pickyoptions.configuration import Configuration, Configurable, Configurations
from pickyoptions.configuration.configurations import EnforceTypesConfiguration
from pickyoptions.configuration.exceptions import ConfigurationDoesNotExist
from pickyoptions.configuration.utils import requires_configured
from pickyoptions.routine import Routine, Routines

from .configurations import (
    ValidateConfiguration, ValidateWithOptionsConfiguration, NormalizeConfiguration,
    PostProcessConfiguration, PostProcessWithOptionsConfiguration, FieldConfiguration)
from .exceptions import (
    OptionInvalidError,
    OptionRequiredError,
    OptionTypeError,
    # OptionNotSetError,
    OptionNotConfiguredError,
)

logger = logging.getLogger(settings.PACKAGE_NAME)


class Option(Configurable, Child):
    """
    TODO:
    ----
    (1) Should we maybe add a property that validates the type of value provided if it is
        not `None`?  This would allow us to have a non-required value type checked if it is
        provided.  This would be a useful configuration for the `obj:Option` and `obj:Options`.
    (2) Should we maybe add a `validate_after_normalization` boolean property?
    (3) The `allow_null` configuration might cause issues with the `default` property if the
        default value is None.  We should handle that more appropriately.
    (4) Figure out how to add the NOTSET as a default for `default` and make it publically
        accessible as .default with the NOTSET value pruned.
    """
    # Configurable Implementation Properties
    not_configured_error = OptionNotConfiguredError
    # not_set_error = OptionNotSetError

    # Child Implementation Properties
    parent_cls = 'Options'
    child_identifier = "field"
    unrecognized_child_error = ConfigurationDoesNotExist
    invalid_child_error = OptionInvalidError
    invalid_child_type_error = OptionTypeError
    required_child_error = OptionRequiredError

    configurations = Configurations(
        Configuration('default', default=constants.NOTSET),
        Configuration('required', types=(bool, ), default=False),
        Configuration('allow_null', types=(bool, ), default=True),
        EnforceTypesConfiguration('enforce_types'),
        ValidateConfiguration('validate'),
        ValidateWithOptionsConfiguration('validate_with_options'),
        NormalizeConfiguration('normalize'),
        PostProcessConfiguration('post_process'),
        PostProcessWithOptionsConfiguration('post_process_with_options'),
        Configuration("help_text", default="", types=six.string_types)
    )

    @track_init
    def __init__(self, field, **kwargs):
        self._value = None
        self._populated_value = constants.NOTSET
        self._set = False  # This is only applicable for the `obj:Option` right now...

        # Include the `field` from the arguments as a configuration.  We could of course just
        # include in the static attribute configurations, but then it would have to be provided
        # as a **kwarg - which is slightly less user friendly.
        kwargs.update(
            extra_configurations=[FieldConfiguration('field')],
            field=field
        )

        self.routines = Routines(
            Routine(id='populating'),
            Routine(id='overriding'),
            Routine(id='restoring')
        )

        Configurable.__init__(self, **kwargs)
        # The child needs to be initialized after the option is configured, because the child will
        # use the `field` value (which is configured) to uniquely identify the child.
        Child.__init__(self, parent=kwargs.pop('parent', None))

    def __deepcopy__(self, memo):
        cls = self.__class__
        explicit_configuration = deepcopy(self.configurations.configured_configurations, memo)
        del explicit_configuration['field']
        result = cls.__new__(cls, self.field, **explicit_configuration)
        result.__init__(self.field, **explicit_configuration)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            object.__setattr__(result, k, deepcopy(v, memo))
        return result

    def __repr__(self):
        if self.initialized:
            return "<{cls_name} field={field}>".format(
                cls_name=self.__class__.__name__,
                field=self.field,
            )
        return "<{cls_name} {state}>".format(
            cls_name=self.__class__.__name__,
            state=constants.State.NOT_INITIALIZED
        )

    def __getattr__(self, k):
        assert self.configured
        try:
            configuration = getattr(self.configurations, k)
        except AttributeError:
            assert settings.DEBUG is True
            raise AttributeError("The attribute %s does not exist on the Option instance." % k)
        else:
            return configuration.value

    def raise_invalid(self, *args, **kwargs):
        kwargs.setdefault('cls', OptionInvalidError)
        return self.raise_with_self(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        kwargs['cls'] = OptionRequiredError
        return self.raise_invalid(*args, **kwargs)

    def raise_invalid_type(self, *args, **kwargs):
        kwargs.update(
            cls=OptionTypeError,
            types=self.enforce_type
        )
        return self.raise_invalid(*args, **kwargs)

    @property
    def default_set(self):
        """
        Returns whether or not the `obj:Option` default was configured with an explicitly provided
        value.
        """
        configuration = self.configurations['default']
        if configuration.configured:
            return True
        return False

    @property
    def value(self):
        # This might cause issues now, since we switched the population in the parent to only
        # call populated if the value exists (and not if it is set to None).
        # TODO: Come up with a property that indicates the option has been set, not populated
        # per say, but set.
        # if not self.populated:
        #     raise OptionNotPopulatedError(field=self.field)

        value = self._value
        if self._value is None:
            assert not self.required
            # TODO: Do we want to enforce that the default was set?  This would prevent users
            # from being able to set required = False without having to explicitly set None as a
            # default.
            if self.default is None:
                # TODO: This still has to be validated.s
                assert self.allow_null is True
            value = self.default

        if self.normalize:
            return self.normalize(value, self)
        return value

    @value.setter
    def value(self, value):
        self._value = value
        self._set = True

        # We do this here instead of at the end of the routines so these always run when the value
        # is updated.
        self.do_validate()
        self.do_post_process()

        # If the `obj:Option` is populating or overriding, the validation and post processing
        # routines with options will be run after the routine finishes.
        if self.routines.populating.in_progress:
            assert self.routines.subsection(['restoring', 'overriding']).none_in_progress
            assert self.parent.routines.populating.in_progress
            self.routines.populating.store(value)
        elif self.routines.overriding.in_progress:
            assert self.routines.subsection(['restoring', 'populating']).none_in_progress
            assert self.parent.routines.overriding.in_progress
            self.routines.overriding.store(value)
        elif self.routines.restoring.in_progress:
            assert self.routines.subsection(['overriding', 'populating']).none_in_progress
            assert self.parent.routines.restoring.in_progress
            self.routines.restoring.store(value)
        else:
            # If the parent `obj:Options` are not populating, we want to perform the validation/
            # post-processing routines with the populated `obj:Options`.  If the parent
            # `obj:Options` are still populating, the routines will be called after the parent
            # population finishes.
            assert not self.routines.any_in_progress
            logger.debug(
                "Applying post routine with options on option %s since it is not in the "
                "middle of a routine." % self.identifier
            )
            self.post_routine_with_options()

    def reset(self):
        super(Option, self).reset()
        self._value = None

    def override(self, value):
        with self.routines.overriding(self):
            self.value = value

    def populate(self, value):
        with self.routines.populating(self):
            self.value = value

    def restore(self):
        with self.routines.restoring(self):
            assert len(self.routines.populating.history) == 1
            self.value = self.routines.populating.history[0]

    def post_routine_with_options(self):
        logger.debug("Performing post routine on %s, field = %s, with parent options." % (
            self.__class__.__name__, self.field))
        self.do_validate_with_options()
        self.do_post_process_with_options()

    def do_post_process(self):
        """
        Performs post-processing of the `obj:Option` immediately after the `obj:Option` is either
        populated, overridden or restored.  This post-processing is independent of the parent
        `obj:Options` and thus does not wait for the associated routine of the `obj:Options` to
        finish before being applied.

        This post-processing is defined by the parameter `post_process` provided to the `obj:Option`
        on initialization.

        Since this post-processing does not reference the overall `obj:Options` instance (and is
        performed independently of the overall `obj:Options` instance) it does not wait for the
        `obj:Options` routine to finish, but instead is immediately called when the `obj:Option`
        finishes populating, overriding or restoring.
        """
        if self.post_process is not None:
            self.post_process(self.value, self)

    def do_post_process_with_options(self):
        """
        Performs post-processing of the `obj:Option` with a reference to the parent `obj:Options`
        after the `obj:Option` has either been populated, overridden or restored AND after
        the parent `obj:Options` have left the context of a routine.  This post-processing is
        defined by the parameter `post_process_with_options` provided to the `obj:Option` on
        initialization.

        The routine performs operations on a group of `obj:Option`(s) simultaneously, so it is
        necessary to  wait for the routine to finish before applying this logic so that the
        `obj:Options` being used reflect the newest values after all the operations on the
        individual `obj:Option`(s) finished.

        TODO:
        ----
        - Asserting that the parent routine has finished here causes issues when we want to either
          populate, restore or override the option individually.  We should figure out a way the
          following possible:

          >>> options = Options()
          >>> option = Option(..., parent=options)
          >>> option.populate(...)

          In the above, the parent `obj:Options` routine will not have been triggered like it would
          be in the case that we called options.populate().

        - We used to assert that the parent population routine had finished, but this method now
          applies to more than one routine.  We  don't know what routine is being referenced
          for any given call, so we cannot assert that a specific routine has finished.  We should
          build this capability in, so the methods have more context about what routine they are
          being called in association with.
        """
        if self.post_process_with_options is not None:
            self.post_process_with_options(self.value, self, self.parent)

    def _do_user_provided_validation(self, func, name, *args):
        """
        Applies the user provided validation method to the `obj:Option`.
        """
        from pickyoptions.options.exceptions import OptionsInvalidError

        configuration = self.configuration(name)
        try:
            # NOTE: This accounts for the default value and the value after normalization.
            result = func(self.value, self, *args)
        except Exception as e:
            # TODO: Maybe we should lax this requirement.  The caveat is that other exceptions
            # could be swallowed and a misleading configuration related exception would disguise
            # them.
            if isinstance(e, (OptionsInvalidError, OptionInvalidError)):
                six.reraise(*sys.exc_info())
            else:
                configuration.raise_invalid(message=(
                    "If raising an exception to indicate that the option is invalid, "
                    "the exception must be an instance of OptionInvalidError or "
                    "OptionsInvalidError.  It is recommended to use the `raise_invalid` method "
                    "of the passed in option or options instance."
                ))
        else:
            if isinstance(result, six.string_types):
                self.raise_invalid(value=self.value, message=result)
            elif result is not None:
                configuration.raise_invalid(message=(
                    "The option validate method must return a string error "
                    "message or raise an instance of OptionInvalidError or OptionsInvalidError in "
                    "the case that the value is invalid.  If the value is valid, it must return "
                    "None."
                ))

    def do_validate(self):
        """
        Performs validation of the `obj:Option` immediately after the `obj:Option` is either
        populated, overridden or restored.  This validation is independent of the parent
        `obj:Options` and thus does not wait for the associated routine of the `obj:Options` to
        finish before being applied.

        This validation is defined by the parameter `validate` provided to the `obj:Option`
        on initialization.

        Since this validation does not reference the overall `obj:Options` instance (and is
        performed independently of the overall `obj:Options` instance) it does not wait for the
        `obj:Options` routine to finish, but instead is immediately called when the `obj:Option`
        finishes populating, overriding or restoring.

        TODO:
        ----
        - Should we also validate the normalized and defaulted values?
        - Checking/validating the default values should be performed in the option configuration
          `validate_configuration` method.
        """
        if self._value is None:
            if self.required:
                if self.default is not None:
                    logger.warn(
                        "The unspecified option %s is required but also specifies a "
                        "default - the default makes the option requirement obsolete."
                        % self.field
                    )
                    # Validate the default value - this should be being done in the
                    # validate_configuration method of the OptionConfiguration class.
                    if self.default is None and not self.allow_null:
                        raise Exception()
                else:
                    self.raise_required()
            else:
                if not self.allow_null:
                    pass
        else:
            # NEED TO FINISH THIS
            if self.enforce_types is not None:
                if not isinstance(self.value, self.enforce_types):
                    self.raise_invalid_type()

        if self.validate is not None:
            self._do_user_provided_validation(self.validate, 'validate')

    def do_validate_with_options(self):
        """
        Performs validation of the `obj:Option` with a reference to the parent `obj:Options`
        after the `obj:Option` has either been populated, overridden or restored AND after
        the parent `obj:Options` have left the context of a routine.  This validation is defined
        by the parameter `validate_with_options` provided to the `obj:Option` on initialization.

        The routine performs operations on a group of `obj:Option`(s) simultaneously, so it is
        necessary to  wait for the routine to finish before applying this logic so that the
        `obj:Options` being used reflect the newest values after all the operations on the
        individual `obj:Option`(s) finished.

        TODO:
        ----
        - Asserting that the parent routine has finished here causes issues when we want to either
          populate, restore or override the option individually.  We should figure out a way the
          following possible:

          >>> options = Options()
          >>> option = Option(..., parent=options)
          >>> option.populate(...)

          In the above, the parent `obj:Options` routine will not have been triggered like it would
          be in the case that we called options.populate().

        - We used to assert that the parent population routine had finished, but this method now
          applies to more than one routine.  We  don't know what routine is being referenced
          for any given call, so we cannot assert that a specific routine has finished.  We should
          build this capability in, so the methods have more context about what routine they are
          being called in association with.
        """
        if self.validate_with_options is not None:
            self._do_user_provided_validation(
                self.validate_with_options,
                'validate_with_options',
                self.parent
            )

    @requires_configured
    def validate_configuration(self):
        """
        Performs validation for the `obj:Option` configuration for configurations that depend on
        one another.  This is performed after the entire `obj:Option` is configured.  On the other
        hand, individual configuration validation routines are performed when the `obj:Option`
        is configured with each individual configuration value.
        """
        default_configuration = self.configurations['default']
        types_configuration = self.configurations['enforce_types']
        required_configuration = self.configurations['required']

        assert types_configuration.value is None or type(types_configuration.value) is tuple

        # If the default value is provided, ensure that the default value conforms to the types
        # specified by `enforce_types` if they are provided.
        if default_configuration.configured:
            if not types_configuration.conforms_to(default_configuration.value):
                default_configuration.raise_invalid_type(
                    types=self.enforce_types,
                    message=(
                        "If enforcing that the option be of type {types}, the default value "
                        "must also be of the same types."
                    )
                )
        # If the default value is not explicitly provided but the option is not required, make
        # sure that the default-default value conforms to the types specified by `enforce_types`
        # if they are provided.
        elif required_configuration.value is False:
            if not types_configuration.conforms_to(default_configuration.value):
                # TODO: We should figure out a more user-friendly way around this, perhaps an
                # additional configuration variable that only enforces types if provided.
                types_configuration.raise_invalid(message=(
                    "If the option is not required but `enforce_types` is specified, the default "
                    "value, in this case None, must also conform to the types specified by "
                    "`enforce_types`.  Either make the option required or provide a default that "
                    "conforms to the types."
                ))
