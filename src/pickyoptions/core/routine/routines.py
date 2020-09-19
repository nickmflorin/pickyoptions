from copy import deepcopy

from .exceptions import RoutineDoesNotExistError
from .routine import Routine


# TODO: Eventually we want to implement this as a Parent instance.  We will have
# to blend the concept of `field` with `id`.
class Routines(list):
    def __init__(self, *args):
        assert all([isinstance(x, Routine) for x in args])
        list.__init__(self, list(args))

    def __new__(cls, *args):
        instance = super(Routines, cls).__new__(cls)
        instance.__init__(*tuple(list(args)))
        return instance

    def __deepcopy__(self, memo):
        elements = deepcopy(self[:], memo)
        cls = self.__class__
        return cls.__new__(cls, *tuple(elements))

    def __getattr__(self, k):
        return self.get_routine(k)

    def append(self, routine):
        # TODO: Come up with better errors here.
        assert isinstance(routine, Routine)
        assert routine.id not in [rout.id for rout in self]
        super(Routines, self).append(routine)

    def subsection(self, ids):
        # Note: The individual routines are not __deepcopy__'d, so they may
        # be mutated in the subsections and the mutations will apply to the
        # original `obj:Routine` in the `obj:Routines`.
        subroutines = [getattr(self, id) for id in ids]
        return self.__class__(*tuple(subroutines))

    def get_routine(self, id):
        try:
            return [routine for routine in self if routine.id == id][0]
        except IndexError:
            raise RoutineDoesNotExistError(id=id)

    def clear_queues(self):
        for routine in self:
            routine.clear_queue()

    def reset(self):
        for routine in self:
            routine.reset()

    def all(self, attribute):
        return all([getattr(routine, attribute) for routine in self])

    def any(self, attribute):
        return any([getattr(routine, attribute) for routine in self])
