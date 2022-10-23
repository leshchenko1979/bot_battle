import pytest
from botbattle import IncorrectInheritanceException, make_code, PlayerAbstract


def test_make_code_whole_file():
    class Player(PlayerAbstract):
        ...

    code = make_code(Player)

    print(code)
    assert code.source.startswith("import pytest")


def test_code_correctness():
    class TestClass_1:
        pass

    with pytest.raises(IncorrectInheritanceException):
        code = make_code(TestClass_1)
