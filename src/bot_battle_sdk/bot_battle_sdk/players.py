import inspect
from abc import ABCMeta, abstractmethod
from pathlib import Path

from .protocol import Code
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


def make_code(cls: PlayerAbstract) -> Code:
    return Code(
        source=Path(inspect.getsourcefile(cls)).read_text(), cls_name=cls.__name__
    )
