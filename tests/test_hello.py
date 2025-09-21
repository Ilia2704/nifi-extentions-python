# tests/test_hello.py
import pytest
from hello_processor.hello import transform

def test_empty_body():
    out, attrs = transform(b"")
    assert out == b"Hello"
    assert attrs["greeting"] == "Hello"

def test_non_empty_body():
    out, attrs = transform(b"world")
    assert out == b"Hello world"
    assert attrs["greeting"] == "Hello"

def test_type_errors():
    with pytest.raises(TypeError):
        transform("not-bytes")  # type: ignore
