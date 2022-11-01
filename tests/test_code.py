import pytest
from botbattle import IncorrectInheritanceException, make_code, PlayerAbstract


def test_code_correctness():
    class TestClass_1:
        pass

    with pytest.raises(IncorrectInheritanceException):
        code = make_code(TestClass_1)
