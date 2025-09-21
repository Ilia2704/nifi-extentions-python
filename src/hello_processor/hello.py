# processor/hello.py
from typing import Tuple, Dict

def transform(data: bytes) -> Tuple[bytes, Dict[str, str]]:
    """
    Если data пустая -> вернём b'Hello'
    Иначе -> b'Hello ' + data
    Плюс атрибут greeting=Hello
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    new_body = b"Hello" if len(data) == 0 else (b"Hello " + data)
    return new_body, {"greeting": "Hello"}
