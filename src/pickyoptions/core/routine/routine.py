import functools
import logging

from pickyoptions import settings
from pickyoptions.lib.utils import optional_parameter_decorator

from pickyoptions.core.base import BaseModel

from .constants import RoutineState
from .exceptions import (
    RoutineNotFinishedError, RoutineInProgressError, RoutineNotInProgressError)


logger = logging.getLogger(settings.PACKAGE_NAME)


@optional_parameter_decorator
def require_not_in_progress(func, id=None):
    """
    Decorator to decorate routine related methods that require that the
    specified routine's state is not IN_PROGRESS.

    The decorator can be applied to a `obj:Routine` itself or a class that
    extends `obj:Routined`.  In the latter case, the `id` needs to be supplied
    so that the specific `obj:Routine` can be found.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from .routined import Routined

        if isinstance(instance, Routined):
            routine = getattr(instance.routines, id)
        else:
            assert isinstance(instance, Routine)
            routine = instance
        if routine.in_progress:
            routine.raise_in_progress()
        return func(instance, *args, **kwargs)
    return inner


@optional_parameter_decorator
def require_finished(func, id=None):
    """
    Decorator to decorate routine related methods that require that the
    specified routine's state is FINISHED.

    The decorator can be applied to a `obj:Routine` itself or a class that
    extends `obj:Routined`.  In the latter case, the `id` needs to be supplied
    so that the specific `obj:Routine` can be found.
    """
    @functools.wraps(func)
    def inner(instance, *args, **kwargs):
        from .routined import Routined

        if isinstance(instance, Routined):
            routine = getattr(instance.routines, id)
        else:
            assert isinstance(instance, Routine)
            routine = instance
        if not routine.finished:
            routine.raise_not_finished()
        return func(instance, *args, **kwargs)
    return inner


class Routine(BaseModel):
    require_not_in_progress = require_not_in_progress
    require_finished = require_finished

    def __init__(self, instance, id, pre_routine=None, post_routine=None):
        super(Routine, self).__init__()
        self._instance = instance
        self._id = id
        self._state = RoutineState.NOT_STARTED
        self._history = []
        self._queue = []
        self._pre_routine = pre_routine
        self._post_routine = post_routine

    def __enter__(self):
        logger.debug("Entering routine %s context." % self.id)
        assert len(self._queue) == 0
        self.pre_routine(self._instance)
        self._state = RoutineState.IN_PROGRESS
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Exiting routine %s context." % self.id)
        self._state = RoutineState.FINISHED
        if exc_type:
            return False
        self.post_routine(self._instance)
        return False

    @property
    def id(self):
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def queue(self):
        return self._queue

    @property
    def history(self):
        return self._history

    @property
    def finished(self):
        return self.state == RoutineState.FINISHED

    @property
    def not_finished(self):
        return not self.finished

    @property
    def in_progress(self):
        return self.state == RoutineState.IN_PROGRESS

    @property
    def not_started(self):
        return self.state == RoutineState.NOT_STARTED

    @property
    def started(self):
        return not self.not_started

    @property
    def did_run(self):
        return self.in_progress or self.finished

    @require_finished
    def post_routine(self, instance):
        """
        Performs operations that are meant to occur just after the
        `obj:Routine` finishes.

        Calls the provied post_routine method if it is provided and clears
        the progress queue of the `obj:Routine`.
        """
        logger.debug('Performing post-routine %s on %s.' % (
            self.__class__.__name__, instance.__class__.__name__))

        if self._post_routine:
            self._post_routine()

        self.clear_queue()

    @require_not_in_progress
    def pre_routine(self, instance):
        """
        Performs operations that are meant to occur just before the
        `obj:Routine` starts and calls the provied pre_routine method if it
        is provided.

        NOTE:
        ----
        Note that the `obj:Routine`'s state will only ever be NOT_STARTED
        before the first time it is run, so we cannot enforce that the
        pre_routine require the state be NOT_STARTED.
        """
        logger.debug('Performing pre-routine %s on %s.' % (
            self.__class__.__name__, instance.__class__.__name__))

        # The queue should have already been cleared by the post_routine.
        assert len(self.queue) == 0

        if self._pre_routine:
            self._pre_routine()

    def raise_in_progress(self, *args, **kwargs):
        """
        Raises an error to indicate that the `obj:Routine` is in progress.
        """
        kwargs.update(
            cls=RoutineInProgressError,
            id=self.id
        )
        self.raise_with_self(*args, **kwargs)

    def raise_not_in_progress(self, *args, **kwargs):
        """
        Raises an error to indicate that the `obj:Routine` is not in progress.
        """
        kwargs.update(
            cls=RoutineNotInProgressError,
            id=self.id
        )
        self.raise_with_self(*args, **kwargs)

    def raise_finished(self, *args, **kwargs):
        """
        Raises an error to indicate that the `obj:Routine` has not finished.
        """
        kwargs.update(
            cls=RoutineNotFinishedError,
            id=self.id
        )
        self.raise_with_self(*args, **kwargs)

    def raise_not_finished(self, *args, **kwargs):
        """
        Raises an error to indicate that the `obj:Routine` has not finished.
        """
        kwargs.update(
            cls=RoutineNotFinishedError,
            id=self.id
        )
        self.raise_with_self(*args, **kwargs)

    def add_to_queue(self, obj):
        """
        Adds an operated element the `obj:Routine`'s progress queue.
        """
        self._queue.append(obj)

    @require_finished
    def clear_queue(self):
        """
        Clears the `obj:Routine`'s progress queue.
        """
        logger.debug(
            "Clearing %s items from the routine queue." % len(self._queue))
        self._queue = []

    @require_not_in_progress
    def clear_history(self):
        logger.debug(
            "Clearing %s items from the history queue." % len(self._history))
        self._history = []

    def reset(self):
        """
        Resets the `obj:Routine` by clearing it's history of operated elements.
        """
        assert len(self.queue) == 0
        self.clear_history()
        self._state = RoutineState.NOT_STARTED

    def store(self, value):
        """
        Adds an operated element the `obj:Routine`'s history.
        """
        assert value not in self._history
        self._history.append(value)
