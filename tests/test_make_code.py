from botbattle import make_code

class TestClass():
    pass

def test_make_code():
    code = make_code(TestClass)
    print(code)
    assert code.source.startswith("from botbattle")
