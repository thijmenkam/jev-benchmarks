import abc
import time


class BaseClient(abc.ABC):
    name = "base"
    provider = "base"
    model = "base"

    def __init__(self, seed=0):
        self.seed = seed

    @property
    def display_name(self):
        return self.name

    @abc.abstractmethod
    def evaluate(self, state, questions):
        pass

    def timed_evaluate(self, state, questions):
        start = time.perf_counter()
        response = self.evaluate(state, questions)
        response.latency_ms = (time.perf_counter() - start) * 1000.0
        return response