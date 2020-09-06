from copy import deepcopy
import contextlib
import functools
import logging
import six
import sys

from pickyoptions import settings
from pickyoptions.exceptions import PickyOptionsError


from pickyoptions.configuration.exceptions import ConfigurationInvalidError

from pickyoptions.option.exceptions import (
    OptionUnrecognizedError, OptionInvalidError, OptionRequiredError)

from .configuration import OptionsConfiguration
from .exceptions import OptionsInvalidError, OptionsNotPopulatedError
from .utils import requires_population


logger = logging.getLogger("pickyoptions")


class Options(OptionsConfiguration):
    """
    The entry point for using pickyoptions in a project.

    Represents a series of configurable `obj:Option`(s) that define the framework for which
    package users can specify and override options in the package.

    Configuring your package with options can be done either by a direct import from pickyoptions
    or by explicitly instantiating the `obj:Options` itself:

    ~~~ my_package.__init__

    >>> from pickyoptions import options
    >>> options.configure(
    >>>     Option(field="foo", type=(str, int)),
    >>>     Option(field="bar", type=(str, int))
    >>> )
    >>> options.populate(foo="fooey")

    or

    >>> from pickyoptions import Options
    >>> options = Options(
    >>>     Option(field="foo", type=(str, int)),
    >>>     Option(field="bar", type=(str, int))
    >>> )
    >>> options.populate(foo="fooey")

    ~~~ my_package.file

    >>> from pickyoptions import options
    >>> assert options.foo = "fooey"

    or

    ~~~ my_package.file

    >>> from my_package import options
    >>> assert options.foo = "fooey"
    """
    def __init__(self, *args, **kwargs):
        # Keeps track of the options that were set on population so the state of the
        # `obj:Options` instance can be restored after overrides are applied.
        # self._populated_options = {}

        # Keeps track of whether or not the `obj:Options` instance has already been populated
        # and whether or not it is actively being populated.
        self._populated = False
        self._populating = False

        self._overridden = False

        # Keeps track of the option values that are overridden after population.
        # self._overrides = {}
        # self._mapping = {}

        # TODO: Do we have to worry about the mutability/inmutability of the options?  Since
        # we are setting the values on the options.
        # TODO: We also need to do this if the options are set at a later point in time.
        # Why aren't we setting self.options instead of self._options?
        self._options = list(args)
        for option in self._options:
            option._options = self

        super(Options, self).__init__(**kwargs)

    def __repr__(self):
        if self.populated:
            return "<{cls_name} {params}>".format(
                cls_name=self.__class__.__name__,
                params=", ".join(["{k}={v}".format(k=k, v=v) for k, v in self.zipped])
            )
        # Note: This causes problems if the options are not set as the private variable yet.
        return "<{cls_name} UNPOPULATED [{options}]>".format(
            cls_name=self.__class__.__name__,
            options=", ".join([option.field for option in self.options])
        )

    def __call__(self, *args, **kwargs):
        self.populate(*args, **kwargs)

    def __getitem__(self, k):
        return getattr(self, k)

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def __iter__(self):
        for option in self.options:
            if option.field not in self._mapping:
                assert option.default is not None or not option.required
            # This will include the defaulted and normalized values.
            yield option.field, getattr(self, option.field)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    # TODO: Implement __delattr__ method and __delitem__ method.
    def __getattr__(self, k):
        # If the options are not yet populated, we only allow the retrieval of a configuration
        # value, not the option values themselves.
        if not self.populated:
            if settings.DEBUG:
                raise PickyOptionsError(
                    "Operation %s not permitted if the options are not "
                    "yet populated." % self.__getattr__.__name__,
                )
            raise PickyOptionsError(
                "The attribute %s does not exist in the options configuration and the "
                "options have not been populated yet.  If accessing a specific option, the "
                "options must be populated."
            )
        # TODO: Do we really want this to raise an error indicating that the option is not
        # recognized instead of an actual attribute error?
        option = self.option(k)

        # Is this safe?  What about the case where the option value is not provided but has a
        # default?
        # The option may not be populated yet if it is not required and has a default.  We should
        # close out the loose ends in this logic more, maybe by having a property that lets you
        # know if it is going to use it's default value.
        # assert option.populated
        return option.value
        #
        # try:
        #     # value = self._mapping[option.field]
        #     value = option.value
        # # except OptionUnrecognizedError:
        # #     if settings.DEBUG:
        # #         raise AttributeError("The attribute %s does not exist." % k)
        # #     six.reraise(*sys.exc_info())
        # except KeyError:
        #     # I think the option is already guaranteed to not be required since an error would
        #     # have been raised previously when populating or setting?
        #     if option.required:
        #         if option.default:
        #             # TODO: We might wind up logging this warning in multiple locations,
        #             # we should prune those loggings.  We should log this when the option
        #             # is configured.
        #             logger.warn(
        #                 "The unspecified option %s is required but also specifies a "
        #                 "default - the default makes the option requirement obsolete."
        #                 % option.field
        #             )
        #         else:
        #             # TODO: This might already be guaranteed to not happen based on the
        #             # logic in the populate/__setattr__ method.
        #             option.raise_required()

        #     # assert not option.required
        #     return option.normalize(option.default)
        # else:
        #     return option.normalize(value)

    def __setattr__(self, k, v):
        if k.startswith('_'):
            super(Options, self).__setattr__(k, v)
        else:
            # TODO: Do we want to allow the setting of new options that are not already set?
            option = self.option(k)

            # Only validate if we are not actively populating the options, otherwise they will
            # all be validated afterwards.
            # TODO: This is not the same as what happens when the individual options are validated
            # in the validate() method - there it validates the default/normalized value.
            if self.populating:
                option.populate(v)
                # option.validate_with_options(self)
                # option.validate(v, self)
            else:
                option.value = v
                # We do not need to perform validation and post processing routines with the
                # siblings for all children.
                self.do_validate(children=[option])
                self.do_post_process(children=[option])
                # option.validate_with_options(self)
                # option.validate(v, self)

            # option.populate(v)
            # self._mapping[option.field] = v

            # If all the options have been set, validate the `obj:Options` instance as a whole and
            # perform the post processing routines on the individual options as well.
            # if not self.populating:
            #     self.validate()
            #     option.validate_on_options_populated()
                # option.post_process()
                # option.validate()
                # Only do this if we are only setting one at a time, otherwise all of the
                # options wil not have been set yet.
                # option.validate_with_options(self)

    @property
    def zipped(self):
        return [(field, value) for field, value in self]

    def keys(self):
        keys = []
        for option in self.options:
            if option.field not in self._mapping:
                # TODO: Clean up this logic
                assert option.default is not None or not option.required
            # This will include defaulted options.
            keys.append(option.field)
        return keys

    def values(self):
        values = []
        for option in self.options:
            if option.field not in self._mapping:
                # TODO: Clean up this logic
                assert option.default is not None or not option.required
            # This will include the defaulted and normalized values.
            values.append(getattr(self, option.field))
        return values

    def configure(self, *args, **kwargs):
        self.reset()
        super(Options, self).configure(*args, **kwargs)

    @property
    def populated(self):
        """
        Returns whether or not the `obj:Options` have been populated.

        This value will only be False before the first population, afterwards it will remain
        True unless the options are reset - which would require another population afterwards.
        """
        return self._populated

    @property
    def populating(self):
        """
        Returns whether or not the `obj:Options` are in the process of populating the children
        `obj:Option`(s) with values.
        """
        return self._populating

    @property
    def option_fields(self):
        """
        Returns the fields associated with the `obj:Option`(s) configured in the `obj:Options`
        instance.
        """
        return [opt.field for opt in self.options]

    def has_option(self, k):
        try:
            self.option(k)
        except OptionUnrecognizedError:
            return False
        else:
            return True

    def option(self, k):
        """
        Returns the `obj:Option` associated with the provided field.
        """
        # Considering the fact that the configuration happens on __init__, do we really need
        # this?
        if not self.configured:
            raise OptionsNotPopulatedError()
        try:
            return [opt for opt in self.options if opt.field == k][0]
        except IndexError:
            raise OptionUnrecognizedError(k)

    def raise_invalid_option(self, field, **kwargs):
        """
        Raises an OptionInvalidError (or an extension) for the `obj:Option` associated with
        the provided field.
        """
        option = self.option(field)
        option.raise_invalid(**kwargs)

    def raise_invalid(self, *args, **kwargs):
        """
        Raises an OptionsInvalidError (or an extension) for the overall `obj:Options`.
        """
        raise OptionsInvalidError(*args, **kwargs)

    def _handle_exception(self, e, level=logging.ERROR):
        if self.strict:
            raise e
        logger.log(level, "%s" % e)

    def populate(self, *args, **kwargs):
        """
        Populates the configured `obj:Options` instance with values for each defined
        `obj:Option`.
        """
        self.reset()

        with self.populating_context():
            data = dict(*args, **kwargs)
            for option in self.options:
                if option.field not in data:
                    # TODO: This might already be being done in the __setattr__ method?  Or
                    #       is the __setattr__ method is only checking if the value is None and
                    #       the option is required, not if the option is not included.
                    # TODO: This check/logging might be being performed in the option configuration
                    #       validation.
                    if option.required:
                        if option.default:
                            logger.warn(
                                "The unspecified option %s is required but also specifies a "
                                "default - the default makes the option requirement obsolete."
                                % option.field
                            )
                        else:
                            option.raise_invalid(cls=OptionRequiredError)

                else:
                    # Keep track of the fields that were explicitly set so that they can be
                    # reset to the originals at a later point in time.  When overriding, the
                    # mapping will be updated with the overrides but the populated options will
                    # remain in tact.
                    self._populated_options[option.field] = data[option.field]
                    setattr(self, option.field, data[option.field])

            # Make sure that no invalid options provided.
            for k, _ in data.items():
                if k not in self.option_fields:
                    raise OptionUnrecognizedError(k)

    @contextlib.contextmanager
    def populating_context(self):
        self._populating = True
        try:
            yield self
        except Exception:
            six.reraise(*sys.exc_info())
        else:
            self._populating = False
            # Populated will only be False before the first population, afterwards it will always
            # be True, until the options are reset.
            self._populated = True
            # The options are still `populating` at the time the last option is set, so we need
            # to run the validation and post-processing routines for all child options as
            # well.
            self.do_validate()
            self.do_post_process()

    def reset(self):
        """
        Resets the `obj:Options` state back to the post configuration state before any options
        were populated.

        Note that after the `obj:Options` have been reset, the `obj:Options` require
        re-population of the options before any option values can be accessed on the `obj:Options`
        instance.  This is because potentially required options will not be set anymore, so
        we cannot access their values until they are set.
        """
        self._mapping = {}
        self._populated_options = {}
        self._overrides = {}
        self._populated = False

    @requires_population
    def override(self, *args, **kwargs):
        """
        Overrides certain populated option values in the existing `obj:Options` with new option
        values.

        A running history of the applied overrides is maintained in memory until the options are
        either reset or restored.  The applied overrides are used to determine how to restore the
        `obj:Options` back to it's previous state.
        """
        data = dict(*args, **kwargs)
        with self.populating_context():
            for k, v in data.items():
                setattr(self, k, v)
                self._overrides[k] = v

    @requires_population
    def restore(self):
        """
        Resets the `obj:Options` instance to it's state immediately after it was last populated.
        Any overrides applied since the last population will be removed and the `obj:Options`
        values will correspond to their values from the last population of the `obj:Options`
        instance.
        """
        with self.populating_context():
            for option in self.options:
                # Note:  We can't simply reset the options and reapply the last populated
                # options because the reset removes the populated options.  This is why we should
                # keep a queue of the populated options in memory.
                if option.field in self._overrides:
                    # The option need not be in the populated options, since the override
                    # could have been applied to a default value.  In this case, we have to
                    # remove from the mapping.
                    if option.field not in self._populated_options:
                        assert option.required is False
                        # TODO: Implement __delattr__ method and __delitem__ method?
                        del self._mapping[option.field]
                    else:
                        setattr(self, option.field, self._populated_options[option.field])
        self._overrides = {}

    @classmethod
    def display(self):
        """
        Displays the options to the user.
        """
        sys.stdout.write("\n\n".join(opt.display for opt in self.__options__))

    @requires_population
    def do_validate(self, children=None):
        """
        Validates the overall `obj:Options` instance, based on the provided `validate` argument
        on initialization, after the options have been initialized, configured or overidden.

        Unlike the individual `obj:Option` validation routines, this has a chance to perform
        validation after all of the individual `obj:Option`(s) have been set on the `obj:Options`.

        The provided `validate` method must be a callable that takes the `obj:Options` as it's
        first and only argument.  To indicate that the `obj:Options` as a whole are invalid,
        it can either raise `obj:OptionsInvalidError`, `obj:OptionInvalidError`, call the
        `raise_invalid` method on the `obj:Options` or one of the children `obj:Option`(s) or
        it can return a string message.  If the `obj:Options` are valid, it must return `None`.
        """
        children = children or self.options
        logger.debug("Validating %s children options." % len(children))
        for option in children:
            # TODO:  The option need not be populated yet, because non-required options that have a
            #        default value will not be populated if they are not in the population data.
            #        However, we should add a property to the `obj:Option` to indicate that it is
            #        not populated but will return a default value.
            option.validate_with_siblings()

        # Validate the overall options set if the validator is provided.
        if self.validate is not None:
            logger.debug("Validating overall options.")
            # In the case that the options are invalid, validation method either returns a
            # string method or raises one of OptionInvalidError or OptionsInvalidError (or an
            # extension of).
            # TODO: Should we maybe lax the restriction of what exception the valiation routines
            #       should throw?  To make the package more user friendly?
            try:
                result = self.validate(self)
            except Exception as e:
                if isinstance(e, (OptionsInvalidError, OptionInvalidError)):
                    six.reraise(*sys.exc_info())
                else:
                    # TODO: Should we maybe lax this assumption?
                    exc = ConfigurationInvalidError(
                        field='validate',
                        message=(
                            "If raising an exception to indicate that the options are invalid, "
                            "the exception must be an instance of OptionsInvalidError or "
                            "OptionInvalidError.  It is recommended to use the `raise_invalid` "
                            "method on the options instance or on the specific option."
                        )
                    )
                    self._handle_exception(exc)
            else:
                if result is not None:
                    if not isinstance(result, six.string_types):
                        exc = ConfigurationInvalidError(
                            field='validate',
                            message=(
                                "The option validate method must return a string error "
                                "message, raise an instance of OptionInvalidError or raise an "
                                "instance of OptionsInvalidError in the case that the value or "
                                "values are invalid.  If the value is valid, it must return None."
                            )
                        )
                        self._handle_exception(exc)
                    else:
                        self.raise_invalid(message=result)

    @requires_population
    def do_post_process(self, children=None):
        """
        Performs the post-processing routines associated with the overall `obj:Options` and
        all of the individual `obj:Option`(s) after the options have been initialized, configured
        or overridden.

        The `post_process` method of the overall `obj:Options` must be a callable that takes the
        `obj:Options` instance as it's only argument.  The individual `obj:Option` `post_process`
        methods must be callables that take the set value as it's first argument and the
        overall `obj:Options` instance as it's second argument.
        """
        children = children or self.options
        logger.debug("Post processing individual options.")
        for option in children:
            # TODO:  The option need not be populated yet, because non-required options that have a
            #        default value will not be populated if they are not in the population data.
            #        However, we should add a property to the `obj:Option` to indicate that it is
            #        not populated but will return a default value.
            option.post_process_with_siblings()

        if self.post_process is not None:
            logger.debug("Post processing options")
            self.post_process(self)

    @requires_population
    def local_override(self, func):
        """
        Decorator for functions that allows the global options to be temporarily overridden while
        inside the context of the decorated method.  The decorated method can be provided
        additional keyword arguments to specify the values of the options to be overridden.

        Example:
        -------
        from my_package import options

        options.configure(HOST_NAME="0.0.0.0")

        @options.local_override
        def get_host_name(port):
            if options.HOST_NAME == "0.0.0.0":
                return "localhost:port"
            return "%s:%s" % (options.HOST_NAME, port)

        >>> get_host_name(8000)
        >>> "localhost:8000"

        >>> get_host_name(8000, HOST_NAME="123.123.123.123")
        >>> "123.123.123.123:8000"
        """
        @functools.wraps(func)
        def inner(*args, **kwargs):
            local_options = {}
            option_overrides = kwargs.get('options', kwargs)
            for k, v in option_overrides.items():
                if k in self.option_fields:
                    local_options[k] = kwargs.pop(k)

            # Store current options before the local override in memory, so they can be used
            # after the function returns to reset the `obj:Options` instance.
            current_options = deepcopy(self.__dict__)

            # Apply overrides and allow the method to run with the overrides applied.
            self.override(local_options)
            result = func(*args, **kwargs)

            # Wipe out the locally scoped overrides and reset the state back to what it was
            # before the method was called.
            self.populate(current_options)
            return result

        return inner


options = Options()
