from copy import deepcopy
import logging
import six
import sys

from pickyoptions import constants, settings
from pickyoptions.exceptions import (
    OptionInvalidError,
    OptionRequiredError,
    OptionTypeError,
    OptionsInvalidError,
    OptionNotPopulatedError,
    OptionNotSetError,
    OptionPopulatingError,
    OptionNotConfiguredError,
    ConfigurationDoesNotExist,
)
from pickyoptions.lib.utils import check_num_function_arguments

from .base import track_init
from .child import Child
from .configurable import Configurable, requires_configured
from .configuration import Configuration
from .configurations import Configurations, EnforceTypesConfiguration
from .populating import Populating, requires_not_populating, requires_value_set


logger = logging.getLogger(settings.PACKAGE_NAME)


class PostProcessConfiguration(Configuration):
    # TODO: Maybe we should allow the default to be `None` (by default), not NOTSET.
    def __init__(self, field):
        super(PostProcessConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(PostProcessConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 2):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument and the option instance as it's second argument."
                )


class PostProcessWithOptionsConfiguration(Configuration):
    # TODO: Maybe we should allow the default to be `None` (by default), not NOTSET.
    def __init__(self, field):
        super(PostProcessWithOptionsConfiguration, self).__init__(field, default=None)

    def validate(self):
        super(PostProcessWithOptionsConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 3):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument, the option instance as it's second argument and the overall "
                    "combined options instance as it's third argument."
                )


class ValidateConfiguration(Configuration):
    # TODO: Maybe we should allow the default to be `None` (by default), not NOTSET.
    def __init__(self, field):
        super(ValidateConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(ValidateConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 2):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument and the option instance as it's second argument."
                )


class ValidateWithOptionsConfiguration(Configuration):
    # TODO: Maybe we should allow the default to be `None` (by default), not NOTSET.
    def __init__(self, field):
        super(ValidateWithOptionsConfiguration, self).__init__(field, required=False, default=None)

    def validate(self):
        super(ValidateWithOptionsConfiguration, self).validate()
        if self.value is not None:
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 3):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument, the option instance as it's second argument and the overall "
                    "combined options instance as it's third argument."
                )


class NormalizeConfiguration(Configuration):
    # TODO: Maybe we should allow the default to be `None` (by default), not NOTSET.
    def __init__(self, field):
        super(NormalizeConfiguration, self).__init__(field, default=None)

    def validate(self):
        super(NormalizeConfiguration, self).validate()
        if self.value is not None:
            # TODO: Should we allow normalize to have options as the third parameter?  We could
            # always introspect the function and pass in if applicable.
            if not six.callable(self.value) or not check_num_function_arguments(self.value, 2):
                self.raise_invalid(
                    "Must be a callable that takes the option value as it's first "
                    "argument and the option instance as it's second argument."
                )


class FieldConfiguration(Configuration):
    def __init__(self, field):
        super(FieldConfiguration, self).__init__(field, required=True, updatable=False)

    def validate(self):
        super(FieldConfiguration, self).validate()
        if not isinstance(self.value, six.string_types):
            self.raise_invalid_type(types=six.string_types)
        elif self.value.startswith('_'):
            self.raise_invalid(message="Cannot be scoped as a private attribute.")


class Option(Configurable, Populating, Child):
    """
    The `obj:Options` are a parent to the configuration `obj:Configuration`(s), but the
    `obj:Option` is a child to the `obj:Options`.
    ^^^ Note that this will make Option iterable by iterating over the configurations - not sure
    if we want that, but we can come up with a better solution..
    Actually, on second though, this will make the Options iterable over Configurations!  Not the
    individual configurations...  We should probably have a subclass of ParentModel for that.

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
    not_populated_error = OptionNotPopulatedError
    not_set_error = OptionNotSetError

    # Populating Implementation Properties
    populating_error = OptionPopulatingError

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

        # Include the `field` from the arguments as a configuration.  We could of course just
        # include in the static attribute configurations, but then it would have to be provided
        # as a **kwarg - which is slightly less user friendly.
        kwargs.update(
            extra_configurations=[FieldConfiguration('field')],
            field=field
        )

        Populating.__init__(self)
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
        # TODO: Should this part be moved to configurable?
        # WARNING: This might break if there is a configuration that is named the same as an
        # option - we should prevent that.
        assert self.configured
        configuration = getattr(self.configurations, k)
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

        # Do we have to do anything fancy if the options are overridding?

        # If the option is populating, the validation and post process will run after the
        # population finishes.
        if not self.populating and not self.overriding:
            logger.debug(
                "Applying post routine on option since it is not populating, "
                "overriding or restoring."
            )
            self.post_routine()

            # I think this block should be indented, but not sure yet...
            # If the parent `obj:Options` are not populating, we want to perform the validation/
            # post-processing routines with the populated `obj:Options`.  If the parent
            # `obj:Options` are still populating, the routines will be called after the parent
            # population finishes.
            if not self.parent.populating and not self.parent.overriding:
                logger.debug(
                    "Applying post routine with options on option since it is not populating, "
                    "overriding or restoring."
                )
                self.post_routine_with_options()

    def override(self, value):
        with self.overriding_routine():
            self._overridden_value = self._value
            self.value = value

    def reset(self):
        super(Option, self).reset()
        self._value = None

    def populate(self, value):
        with self.population_routine():
            self.value = value
            self._populated_value = value

    # In the case of the options, post population requires the values are populated.  In the case
    # of the option, post population requires that they are set.
    # @requires_not_overriding
    @requires_not_populating
    @requires_value_set
    def post_routine(self):
        logger.debug('Performing post-routine on option %s, field = %s.' % (
            self.__class__.__name__, self.field))
        self.do_validate()
        self.do_post_process()

    def post_routine_with_options(self):
        # TODO: There is currently no post_population_with_options super().
        # super(Option, self).post_population_with_options()
        logger.debug("Performing post routine on %s, field = %s, with parent options." % (
            self.__class__.__name__, self.field))
        self.do_validate_with_options()
        self.do_post_process_with_options()

    def do_post_process(self):
        if self.post_process is not None:
            self.post_process(self.value, self)

    def do_post_process_with_options(self):
        # TODO: Asserting that the parent is populated here causes issues when we want to
        # populate the option individually.  We should figure out a way to make the following
        # possible:
        # >>> options = Options()
        # >>> option = Option(..., parent=options)
        # >>> option.populate(...)
        assert self.parent.populated
        assert not self.parent.populating
        if self.post_process_with_options is not None:
            self.post_process_with_options(self.value, self, self.parent)

    def do_user_provided_validation(self, func, name, *args):
        configuration = self.configuration(name)
        try:
            # NOTE: This passes in the defaulted value or the normalized value if either are
            # applicable.
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
        # TODO: Should we also validate the normalize or the defaulted values?
        # TODO: Checking/validating the default values should be performed in the option
        # configuration `validate_configuration` method.
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
            self.do_user_provided_validation(self.validate, 'validate')

    def do_validate_with_options(self):
        # TODO: Asserting that the parent is populated here causes issues when we want to
        # populate the option individually.  We should figure out a way to make the following
        # possible:
        # >>> options = Options()
        # >>> option = Option(..., parent=options)
        # >>> option.populate(...)
        assert self.parent.populated
        assert not self.parent.populating

        if self.validate_with_options is not None:
            self.do_user_provided_validation(
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
        # super(Option, self).validate_configuration()

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
