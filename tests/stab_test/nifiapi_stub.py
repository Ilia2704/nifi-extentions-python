"""
Строгие стабы NiFi 2.x Python API для контракт-тестов. 
Проверяют типы и базовую логику чтобы класс соответствовал контракту.
"""

# ---------- базовые сущности ----------
class Relationship:
    def __init__(self, name, description=""):
        if not isinstance(name, str) or not name:
            raise TypeError("Relationship.name must be non-empty str")
        self.name = name
        self.description = description


class PropertyDescriptor:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class StandardValidators:
    NON_EMPTY_VALIDATOR = object()


class ExpressionLanguageScope:
    FLOWFILE_ATTRIBUTES = "FLOWFILE_ATTRIBUTES"
    NONE = "NONE"


# ---------- FlowFileTransform ----------
class FlowFileTransform:
    pass


class FlowFileTransformResult:
    def __init__(self, relationship, contents=None, attributes=None):
        if not isinstance(relationship, str) or not relationship:
            raise TypeError("relationship must be non-empty str")
        if contents is not None and not isinstance(contents, (bytes, bytearray)):
            raise TypeError("contents must be bytes or None")
        if attributes is None:
            attributes = {}
        if not isinstance(attributes, dict):
            raise TypeError("attributes must be dict[str,str]")
        for k, v in attributes.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise TypeError("attributes must be dict[str,str]")
        self.relationship = relationship
        self.contents = contents
        self.attributes = attributes


# ---------- FlowFileSource ----------
class FlowFileSource:
    pass


class FlowFileSourceResult:
    def __init__(self, relationship, contents=None, attributes=None):
        if not isinstance(relationship, str) or not relationship:
            raise TypeError("relationship must be non-empty str")
        if contents is not None and not isinstance(contents, (bytes, bytearray, str)):
            raise TypeError("contents must be bytes|str|None")
        if isinstance(contents, str):
            contents = contents.encode("utf-8")
        if attributes is None:
            attributes = {}
        if not isinstance(attributes, dict):
            raise TypeError("attributes must be dict[str,str]")
        for k, v in attributes.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise TypeError("attributes must be dict[str,str]")
        self.relationship = relationship
        self.contents = contents
        self.attributes = attributes


# ---------- RecordTransform ----------
class RecordTransform:
    pass


class RecordTransformResult:
    def __init__(self, record, relationship="success", attributes=None):
        if not isinstance(record, dict):
            raise TypeError("record must be dict")
        if not isinstance(relationship, str) or not relationship:
            raise TypeError("relationship must be non-empty str")
        if attributes is None:
            attributes = {}
        if not isinstance(attributes, dict):
            raise TypeError("attributes must be dict[str,str]")
        for k, v in attributes.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise TypeError("attributes must be dict[str,str]")
        self.record = record
        self.relationship = relationship
        self.attributes = attributes
