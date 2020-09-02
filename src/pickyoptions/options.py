# This is annoying, but required so long as pylint still gets confused with Metaclasses.
# pylint: disable=E1123,E1101,E1120,E0213
from copy import deepcopy
import contextlib
import functools
import logging
import pandas
import six
import sys

from ..exceptions import UnrecognizedOption
from ..utils.html import classnames_iterable

from .stylesheet import default_stylesheet
from .option import Option


logger = logging.getLogger("options")


def post_process_pandas_options(value, options):
    for k, v in value.items():
        pandas.set_option(k, v)


def post_process_strict_option(value, options):
    if value is False:
        logger.warning("DiffEngine operating in non-strict mode.")


class StyleOption(Option):
    def __init__(self, field):
        super(StyleOption, self).__init__(field, default={}, type=(dict, str), mergable=True)

    def normalize(self, value, options):
        # TODO: Convert style CSS string into a style dict object.
        return value


class ClassNameOption(Option):
    def __init__(self, field):
        super(ClassNameOption, self).__init__(field, default=(), allow_null=True, type=(str, list, tuple))

    def normalize(self, value, options):
        if value is None:
            return ()
        return classnames_iterable(value)


# TODO: Investigate CSS Parsing Library Package
class Options(object):
    """
    Options for the `sdiff` package.  These options are configured globally either/or by the `obj:DiffEngine`
    instance instantiation or by explicitly configuring the package.  Options can be overridden on a temporary
    local basis.
    """
    __options__ = (
        Option("pandas_options", default={}, type=dict, post_process=post_process_pandas_options),
        Option("old_color", default="#f5c6cb", type=str),  # salmon
        Option("new_color", default="#d4edda", type=str),  # lightgreen
        Option("fill_na", default="", type=(str, int, float, bool)),
        Option("highlight", default=False, type=bool),
        # Use a post process for this and log a warning.
        Option("strict", default=True, type=[Option], post_process=post_process_strict_option, children=[
            Option("split_added_dimensions", default=False, type=bool),
            Option("split_modified_dimensions", default=True, type=bool),
            Option("split_removed_dimensions", default=False, type=bool),
        ]),
        Option(
            "sort_rows_by",
            validator=lambda value, options: (
                "Must either be a callable taking the row as it's only argument or a string attribute on the row."
                if not callable(value) and not isinstance(value, six.string_types) else None
            ),
            allow_null=True
        ),
        Option(
            "filter_results_by",
            validator=lambda value, options: "Must be a callable." if not callable(value) else None,
            allow_null=True
        ),
        Option(
            "filter_rows_by",
            validator=lambda value, options: "Must be a callable." if not callable(value) else None,
            allow_null=True
        ),
        Option("split_added_dimensions", default=False, type=bool),
        Option("split_modified_dimensions", default=True, type=bool),
        Option("split_removed_dimensions", default=False, type=bool),
        Option("dimension_header", default="TYPE", type=str),
        Option("include_unique_identifiers", default=True, type=bool),
        Option("include_table_header", default=True, type=bool),
        Option("ignore_table_if_empty", default=True, type=bool),
        Option("display_index", default=True, type=bool),
        # TODO: Use a post process for this and log a warning if both are set.
        Option(
            "sort_index",
            default=True,
            type=bool,
            validator=lambda value, options: (
                "Sorting the index will override the sorting of rows. "
                "Must provide EITHER the sort_index or sort_rows_by options, not both."
                if options.sort_rows_by and value is True else None)
        ),
        StyleOption("table_header_style"),
        ClassNameOption("table_header_class_name"),
        Option("table_header_element", default="h6", type=str),

        ClassNameOption("table_class_name"),
        ClassNameOption("table_row_class_name"),
        ClassNameOption("table_new_row_class_name"),
        ClassNameOption("table_old_row_class_name"),
        ClassNameOption("table_modified_row_class_name"),
        ClassNameOption("table_cell_class_name"),
        ClassNameOption("table_new_cell_class_name"),
        ClassNameOption("table_old_cell_class_name"),
        ClassNameOption("table_index_cell_class_name"),
        ClassNameOption("table_header_cell_class_name"),
        ClassNameOption("table_header_row_class_name"),

        # TODO: Allow the style to be specified as a style string.
        StyleOption("table_style"),
        StyleOption("table_row_style"),
        StyleOption("table_new_row_style"),  # Need to implement.
        StyleOption("table_old_row_style"),  # Need to implement.
        StyleOption("table_modified_style"),  # Need to implement.
        StyleOption("table_cell_style"),
        StyleOption("table_new_cell_style"),
        StyleOption("table_old_cell_style"),
        StyleOption("table_index_cell_style"),  # Need to implement.
        StyleOption("table_header_cell_style"),  # Need to implement.
        StyleOption("table_header_row_style"),  # Need to implement.

        Option(
            "stylesheet",
            default=default_stylesheet,
            type=(str, dict),
            allow_null=True,
            mergable=True
        ),
    )

    def __init__(self, *args, **kwargs):
        # Keeps track of the options that were set on initialization so the state of the `obj:Options` instance
        # can be restored after overrides.
        self._originally_set_options = {}

        # Keeps track of whether or not options are currently being set or have already been set, which allows
        # for the overall validation and post processing routines to take place once all the options have been set.
        self._settings_options = False

        # Set the options provided on initialization and run the post processing routines and validation routines
        # after all of the options have been set.
        with self.settings_options():
            data = dict(*args, **kwargs)
            for opt in self.__options__:
                if opt.field in data:
                    # Keep track of the fields that were explicitly set so that they can be reset to the
                    # originals at a later point in time.
                    self._originally_set_options[opt.field] = data[opt.field]
                setattr(self, opt.field, data.get(opt.field, opt.default))

        # Make sure that no invalid options provided.
        for k, _ in data.items():
            if k not in [opt.field for opt in self.__options__]:
                raise UnrecognizedOption(k)

    def __repr__(self):
        return "<Options {params}>".format(
            params=", ".join(["{k}={v}".format(k=k, v=v) for k, v in self.__dict__.items()])
        )

    @contextlib.contextmanager
    def settings_options(self):
        self._settings_options = True
        try:
            yield self
        finally:
            self._settings_options = False
            self.validate()
            self.post_process()

    @property
    def __dict__(self):
        data = {}
        for option in self.__options__:
            data[option.field] = getattr(self, option.field)
        return data

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        result._originally_set_options = self._originally_set_options
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, deepcopy(v, memo))
        return result

    def __setattr__(self, k, v):
        if k.startswith('_'):
            super(Options, self).__setattr__(k, v)
        else:
            option = self.option(k)
            option.validate(v, self)
            value_to_set = option.normalize(v, self)

            # If the option is mergable and the current/new value are both `obj:dict` instances,
            # the existing value of the option will be updated with the new value for the option,
            # not replaced.

            # TODO: Should we only do this if the option is defaulted?  We might want to override user specific
            # options.

            # TODO: For the stylesheet case, we are normalizing it to a string when it is set.  We should probably
            # keep storing this as a dict, and just convert it to a string when we need it.
            if option.mergable:
                current_value = getattr(self, option.field, None)
                if current_value is not None and isinstance(value_to_set, dict) and isinstance(current_value, dict):
                    current_value = deepcopy(current_value)
                    current_value.update(value_to_set)
                    value_to_set = deepcopy(current_value)

            super(Options, self).__setattr__(option.field, value_to_set)

            # Validate the `obj:Options` as a whole if all of the options are set.
            # Do post process as well.
            # Note that this will only happen if a specific option on the Options instance if set, since
            # it otherwise waits for all options to be set before performing these operations.
            if not self._settings_options:
                self.validate()
                if option.post_process:
                    option.post_process(value_to_set, self)

    def option(self, k):
        """
        Returns the `obj:Option` associated with the provided field.
        """
        try:
            return [opt for opt in self.__options__ if opt.field == k][0]
        except IndexError:
            raise UnrecognizedOption(k)

    def raise_invalid(self, field, message=None):
        """
        Raises an InvalidOptionError for the option associated with the provided field.
        """
        option = self._option_for_field(field)
        option.raise_invalid(message=message)

    @classmethod
    def display(self):
        """
        Displays the options to the user.
        """
        sys.stdout.write("\n\n".join(opt.display for opt in self.__options__))

    def validate(self):
        """
        Validates the overall `obj:Options` instance after the options have been initialized, configured or
        overidden.  Unlike the individual `obj:Option` instance validation routines, this has a chance to perform
        validation after all of the options have been set on the `obj:Options` instance.
        """
        pass

    def post_process(self):
        """
        Performs the post-processing routines associated with all of the `obj:Option`(s) after the options have
        been initialized, configured or overridden.
        """
        for opt in self.__options__:
            if opt.post_process:
                opt.post_process(getattr(self, opt.field), self)

    def override(self, *args, **kwargs):
        """
        Overrides certain options in the existing `obj:Options` instance with new options.
        """
        with self.settings_options():
            data = dict(*args, **kwargs)
            with self.settings_options():
                for k, v in data.items():
                    setattr(self, k, v)

    def reset(self):
        """
        Resets the `obj:Options` instance to it's state immediately after it was first initialized.
        Any overrides or post-init configurations since that first initialization will be wiped.
        """
        with self.settings_options():
            for opt in self.__options__:
                if opt.field in self._originally_set_options:
                    super(Options, self).__setattr__(opt.field, self._originally_set_options[opt.field])
                else:
                    super(Options, self).__setattr__(opt.field, opt.default)

    def configure(self, *args, **kwargs):
        """
        Configures the `obj:Options` instance by resetting to it's original state before any overrides were applied
        and applying a new set of overrides.
        """
        # Note that this will call the validation and post processing routines in between the reset and override,
        # which is not ideal but there is likely not a way around that.
        self.reset()
        self.override(*args, **kwargs)

    def local_override(self, func):
        """
        Decorator for functions that allows the global options to be temporarily overridden while inside the context
        of the decorated method.  The decorated method can be provided additional keyword arguments to specify the
        values of the options to be overridden.
        """
        @functools.wraps(func)
        def inner(*args, **kwargs):
            local_options = {}
            for k, v in kwargs.items():
                if k in [option.field for option in self.__options__]:
                    local_options[k] = kwargs.pop(k)

            # Store current options before the local override in memory, so they can be used after the
            # function returns to reset the `obj:Options` instance.
            current_options = deepcopy(self.__dict__)

            # Apply overrides and allow the method to run with the overrides applied.
            self.override(local_options)
            result = func(*args, **kwargs)

            # Wipe out the locally scoped overrides and reset the state back to what it was before the
            # method was called.
            self.configure(current_options)
            return result

        return inner


options = Options()
