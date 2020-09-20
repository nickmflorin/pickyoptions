import logging
import six

from pickyoptions import settings

from pickyoptions.core.base import Base
from pickyoptions.core.decorators import raise_with_error

from .constants import RoutineState
from .exceptions import (
    RoutineNotFinishedError, RoutineInProgressError, RoutineNotInProgressError,
    RoutineFinishedError)
from .utils import require_finished, require_not_in_progress


logger = logging.getLogger(settings.PACKAGE_NAME)


class Routine(Base):
    ___abstract__ = False

    def __init__(self, instance, id, pre_routine=None, post_routine=None,
            on_queue_removal=None):
        super(Routine, self).__init__()
        self._instance = instance
        self._id = id
        self._state = RoutineState.NOT_STARTED
        self._history = []
        self._queue = []
        self._pre_routine = pre_routine
        self._post_routine = post_routine
        self._on_queue_removal = on_queue_removal

    def __enter__(self):
        assert len(self._queue) == 0
        self.pre_routine(self._instance)
        self._state = RoutineState.IN_PROGRESS
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._state = RoutineState.ERROR
            return False
        self._state = RoutineState.FINISHED
        self.post_routine(self._instance)
        return False

    def register(self, value, queue=True, history=True):
        if queue:
            self.add_to_queue(value)
        if history:
            self.store(value)

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
        # The queue should have already been cleared by the post_routine.
        assert len(self.queue) == 0
        if self._pre_routine:
            self._pre_routine()

    @raise_with_error(id='id')
    def raise_with_self(self, *args, **kwargs):
        return super(Routine, self).raise_with_self(*args, **kwargs)

    @raise_with_error(error=RoutineInProgressError)
    def raise_in_progress(self, *args, **kwargs):
        """
        Raises an error to indicate that the `obj:Routine` is in progress.
        """
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error=RoutineNotInProgressError)
    def raise_not_in_progress(self, *args, **kwargs):
        """
        Raises an error to indicate that the `obj:Routine` is not in progress.
        """
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error=RoutineFinishedError)
    def raise_finished(self, *args, **kwargs):
        """
        Raises an error to indicate that the `obj:Routine` has not finished.
        """
        return self.raise_with_self(*args, **kwargs)

    @raise_with_error(error=RoutineNotFinishedError)
    def raise_not_finished(self, *args, **kwargs):
        """
        Raises an error to indicate that the `obj:Routine` has not finished.
        """
        return self.raise_with_self(*args, **kwargs)

    def add_to_queue(self, obj):
        """
        Adds an operated element the `obj:Routine`'s progress queue.
        """
        assert obj not in self._queue
        self._queue.append(obj)

    def save(self):
        self._history.append(self._queue)

    @require_finished
    def clear_queue(self):
        """
        Clears the `obj:Routine`'s progress queue.
        """
        logger.debug("Clearing %s items from the %s queue." % (
            len(self._queue),
            self.id,
        ))
        if self._on_queue_removal:
            for obj in self.queue:
                self._on_queue_removal(obj)
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
