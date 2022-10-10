from abc import ABCMeta, abstractmethod

from .sides import Side
from .state import State


class PlayerAbstract(metaclass=ABCMeta):
    """Participates in games."""

    side: Side

    def __init__(self, side: Side):
        self.side = side

    @abstractmethod
    def make_move(self, state: State) -> int:
        ...
