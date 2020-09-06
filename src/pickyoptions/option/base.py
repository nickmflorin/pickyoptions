import contextlib
import logging
import six
import sys

from pickyoptions.configuration.exceptions import ConfigurationInvalidError

from .configuration import OptionConfiguration
from .exceptions import (OptionInvalidError, OptionRequiredError, OptionTypeError,
    OptionNotPopulatedError)
from .utils import requires_population


logger = logging.getLogger('pickyoptions')


class Option(OptionConfiguration):
    def __init__(self, field, **kwargs):
        self._field = field
        self._value = None

        # Provides the `obj:Option` with a reference to the group of `obj:Options` it lies in.
        self._options = None

        self._overridden = False

        self._populated = False
        self._populating = False

        super(Option, self).__init__(**kwargs)

    def __repr__(self):
        return "<{cls_name} field={field}>".format(
            cls_name=self.__class__.__name__,
            field=self.field,
        )

    @property
    def value(self):
        # TODO: Do we want this?  The option value might not be populated if it wasn't provided.
        # TOOD: Set a property that lets you know if the option will be using the default or not.
        # if not self.populated:
        #     raise OptionNotPopulatedError(field=self.field)
        # TODO: Check if the value is None and required (better yet, if the option was populated
        # and the value is None).

        # TODO: Change name to normalize if we are doing it like this.
        if self.normalizer:
            return self.normalizer(self._value, self)
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        # Only validate and post process if the option is not being populated, otherwise, the
        # routines will be called after population finishes.
        if not self.populating:
            self.validate()
            # TODO: We might not be able to do this anymore because we are not passing in the options.
            self.post_process_alone()
            # TODO: Should we also validate the normalized value and the default value?

    # TODO: Pass in the options?
    def override(self, value):
        if not self.populated:
            raise Exception()
        self.value = value
        self._overridden = True

    @property
    def populated(self):
        return self._populated

    @property
    def populating(self):
        return self._populating

    # TODO: Pass in the options?
    def populate(self, value):
        with self.populating_context():
            self.value = value
            self._populated_value = value

    # def populate_from_default(self):
    #     # If populating from t
    #     with self.populating_context():
    #         pass

    # This might not be necessary for the option case.
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
            # to run the validation and post-processing routines for all individual options as
            # well.
            self.validate_alone()
            self.post_process_alone()

    @property
    def overridden(self):
        return self._overridden

    @property
    def field(self):
        return self._field

    def raise_invalid(self, *args, **kwargs):
        cls = kwargs.pop('cls', OptionInvalidError)
        kwargs['field'] = self.field
        raise cls(*args, **kwargs)

    def raise_required(self, *args, **kwargs):
        kwargs['cls'] = OptionRequiredError
        self.raise_invalid(*args, **kwargs)

    def raise_invalid_type(self, *args, **kwargs):
        kwargs.update(
            cls=OptionTypeError,
            types=self.enforce_type
        )
        self.raise_invalid(*args, **kwargs)

    @property
    def display(self):
        if self.displayer is not None:
            return self.displayer(self)
        return "%s: %s" % (self.field, self.help_text)

    # def normalize(self):
    #     if self.normalizer:
    #         return self.normalizer(value, self)
    #     return value

    def post_process_alone(self):
        # TODO: Require that the options all be populated at this point.
        # Currently, this only gets called after all options are populated.
        # Options not necessarily all populated yet, because this post process is called
        # after each individual option is processed.
        if self.post_process is not None:
            self.post_process(self.value, self)

    # TODO: Should we just pass in the options here?
    def post_process_together(self):
        assert self._options.populated
        if self.post_process_with_siblings is not None:
            self.post_process_with_siblings(self.value, self, self._options)

    # TODO: Implement
    def validate_with_others(self, value, options):
        """
        Validates the `obj:Option` instance after all options have been set on the overall
        combined `obj:Options` instance.
        """
        if self.validator_with_others is not None:
            try:
                result = self.validator_with_others(value, self, options)
            except Exception as e:
                if isinstance(e, OptionInvalidError):
                    six.reraise(*sys.exc_info())
                else:
                    raise ConfigurationInvalidError(
                        field='validate',
                        message=(
                            "If raising an exception to indicate that the option is invalid, "
                            "the exception must be an instance of OptionInvalidError.  It is "
                            "recommended to use the `raise_invalid` method of the option instance."
                        )
                    )
            else:
                if result is not None:
                    if not isinstance(result, six.string_types):
                        raise ConfigurationInvalidError(
                            field='validate',
                            message=(
                                "The option validate method must return a string error, "
                                "a message or raise an instance of OptionInvalidError in the "
                                "case that the value is invalid.  If the value is valid, it "
                                "must return None."
                            )
                        )
                    self.raise_invalid(value=value, message=result)

    @requires_population
    def validate(self):
        # TODO: If the validator method is provided with additional arguments for the options,
        # we should not call it here.  But if it is not provided that way, we can call it here.
        # TODO: Should we also validate the normalize or the defaulted values?
        if self._value is None:
            if self.required:
                if self.default is not None:
                    logger.warn(
                        "The unspecified option %s is required but also specifies a "
                        "default - the default makes the option requirement obsolete."
                        % self.field
                    )
                    # Validate the default value.
                    if self.default is None and not self.allow_null:
                        raise Exception()
                else:
                    self.raise_required()
            else:
                if not self.allow_null:
                    pass
        else:
            # NEED TO FINISH THIS
            if self.enforce_type is not None:
                if not isinstance(self.value, self.enforce_type):
                    self.raise_invalid_type()

    def validate_on_options_populated(self):
        # TODO: IMPORTANT - This will get called when the options are still populating and
        # have not all been set yet.  We need to figure out a solution to that.
        if self.validator is not None:
            # In the case that the option is invalid, validation method either returns a
            # string method or raises an OptionInvalidError (or an extension).
            try:
                # TODO: Take into account that the value may have already been defaulted
                # or normalized.
                result = self.validator(self.value, self, self._options)
            except Exception as e:
                if isinstance(e, OptionInvalidError):
                    six.reraise(*sys.exc_info())
                else:
                    raise ConfigurationInvalidError(
                        field='validate',
                        message=(
                            "If raising an exception to indicate that the option is invalid, "
                            "the exception must be an instance of OptionInvalidError.  It is "
                            "recommended to use the `raise_invalid` method of the option "
                            "instance. "
                        )
                    )
            else:
                if isinstance(result, six.string_types):
                    self.raise_invalid(value=self.value, message=result)
                elif result is not None:
                    raise ConfigurationInvalidError(
                        field='validate',
                        message=(
                            "The option validate method must return a string error "
                            "message or raise an instance of OptionInvalidError in the "
                            "case that the value is invalid.  If the value is valid, it "
                            "must return None."
                        )
                    )
