import logging

from pickyoptions import settings

from pickyoptions.core.base import track_init
from pickyoptions.core.child import Child
from pickyoptions.core.valued import Valued

from .configurable import SimpleConfigurable
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


logger = logging.getLogger(settings.PACKAGE_NAME)


class Configuration(Child, SimpleConfigurable, Valued):
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

    TODO:
    ----
    - Eventually, we should consider trying to use Configuration recursively and
      give the Configuration configurations.
    - Parameter for whether or not the normalization method should be applied
      to the default.
    - Parameter for whether or not the validation method should be applied to
      the default.
    """
    # Valued Implementation Properties
    not_set_error = ConfigurationNotSetError  # Also used by Child impl.
    locked_error = ConfigurationLockedError  # Also used by Child impl.
    required_error = ConfigurationRequiredError  # Also used by Child impl.
    invalid_error = ConfigurationInvalidError  # Also used by Child impl.
    invalid_type_error = ConfigurationTypeError  # Also used by Child impl.

    # Child Implementation Properties
    parent_cls = 'Configurations'
    child_identifier = 'field'
    does_not_exist_error = ConfigurationDoesNotExist

    # SimpleConfigurable Implementation Properties
    not_configured_error = NotConfiguredError
    configuring_error = ConfiguringError
    configuration_error = ConfigurationError

    @track_init
    def __init__(self, field, parent=None, **kwargs):
        Child.__init__(self, parent=parent)
        SimpleConfigurable.__init__(self)
        Valued.__init__(self, field, **kwargs)

    def _configure(self, value):
        self.value = value

    def __repr__(self):
        # TODO: I don't think we have a state on the Configuration anymore?
        if self.configured:
            return (
                "<{cls_name} state={state} field={field} value={value}>".format(
                    cls_name=self.__class__.__name__,
                    field=self.field,
                    value=self.value,
                    state=self.state,
                )
            )
        # The field attribute won't be available until the `obj:Configuration`
        # is configured - not anymore, the field is set as the first line of the
        # init.
        return "<{cls_name} state={state} field={field}>".format(
            cls_name=self.__class__.__name__,
            state=self.state,
            field=self.field,
        )

    def post_set(self, value):
        pass
