from copy import deepcopy


class Routines(list):
    def __init__(self, *args):
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

    def subsection(self, ids):
        subroutines = [getattr(self, id) for id in ids]
        return self.__class__(*tuple(subroutines))

    def get_routine(self, id):
        try:
            return [routine for routine in self if routine.id == id][0]
        except IndexError:
            raise AttributeError(
                "The routine %s does not exist in %s instance."
                % (id, self.__class__.__name__)
            )

    def clear_queue(self):
        for routine in self:
            routine.clear_queue()

    def reset(self):
        for routine in self:
            routine.reset()

    def _all(self, attribute):
        return all([getattr(routine, attribute) for routine in self])

    def _any(self, attribute):
        return any([getattr(routine, attribute) for routine in self])

    @property
    def none_in_progress(self):
        return not self._any('in_progress')

    @property
    def all_in_progress(self):
        return self._all('in_progress')

    @property
    def any_in_progress(self):
        return self._any('in_progress')

    @property
    def none_finished(self):
        return not self._any('finished')

    @property
    def all_finished(self):
        return self._all('finished')

    @property
    def any_finished(self):
        return self._any('finished')

    @property
    def none_started(self):
        return not self._any('started')

    @property
    def all_started(self):
        return self._all('started')

    @property
    def any_started(self):
        return self._any('started')
