from pickyoptions.lib.utils import ensure_iterable

from pickyoptions.core.base import BaseModel

from .routine import Routine
from .routines import Routines


class Routined(BaseModel):
    def __init__(self, routines=None):
        if not isinstance(routines, Routines):
            routines = ensure_iterable(routines, cast=tuple)
            self.routines = Routines(*routines)
        else:
            self.routines = routines

    def create_routine(self, id, cls=None, **kwargs):
        cls = cls or Routine
        routine = cls(self, id, **kwargs)
        self.routines.append(routine)

    def reset_routines(self):
        self.routines.reset()

    def clear_routine_queues(self):
        self.routines.clear_queues()
