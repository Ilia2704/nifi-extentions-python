"""
Сканируем src/<processor_pkg>/*.py, импортируем модули и валидируем
все классы-процессоры: FlowFileTransform / FlowFileSource / RecordTransform.
Теперь с подробным логированием.
"""
import os
import importlib
import inspect
import logging
from pathlib import Path
from typing import Iterable

from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.flowfilesource   import FlowFileSource,   FlowFileSourceResult
from nifiapi.recordtransform  import RecordTransform,  RecordTransformResult
from nifiapi.relationship     import Relationship
from nifiapi.properties       import PropertyDescriptor

log = logging.getLogger("nifi_stubtest")
SRC_ROOT = Path(os.environ.get("NIFI_SRC_ROOT", "src")).resolve()


def _iter_module_names() -> Iterable[str]:
    """
    Формируем имена модулей вида:
      - '<pkg>'           для src/<pkg>/__init__.py
      - '<pkg>.<module>'  для src/<pkg>/*.py (кроме __init__.py)

    Работает и с обычными пакетами, и с namespace-пакетами.
    """
    if not SRC_ROOT.is_dir():
        log.warning("SRC root not found: %s", SRC_ROOT)
        return

    for pkg_dir in SRC_ROOT.iterdir():
        if not pkg_dir.is_dir() or pkg_dir.name.startswith(("_", ".")):
            continue

        pkg = pkg_dir.name

        init_py = pkg_dir / "__init__.py"
        if init_py.is_file():
            yield pkg

        for py in pkg_dir.glob("*.py"):
            if py.name.startswith("_"):
                continue
            if py.name == "__init__.py":
                continue
            mod = f"{pkg}.{py.stem}"
            yield mod


def _assert_processor_details(cls):
    assert hasattr(cls, "ProcessorDetails"), f"{cls.__name__}: missing ProcessorDetails"
    PD = cls.ProcessorDetails
    version = getattr(PD, "version", "")
    desc    = getattr(PD, "description", "")
    assert isinstance(version, str) and version, f"{cls.__name__}: version must be non-empty str"
    assert isinstance(desc, str)    and desc,    f"{cls.__name__}: description must be non-empty str"

    tags = getattr(PD, "tags", None)
    deps = getattr(PD, "dependencies", None)
    if tags is not None:
        assert isinstance(tags, (list, tuple)) and all(isinstance(t, str) for t in tags), f"{cls.__name__}: tags must be list[str]"
    if deps is not None:
        assert isinstance(deps, (list, tuple)) and all(isinstance(d, str) for d in deps), f"{cls.__name__}: dependencies must be list[str]"

    log.info("ProcessorDetails [%s]: version=%s, desc='%s', tags=%s, deps=%s",
             cls.__name__, version, desc, tags, deps)


def _assert_relationships(proc):
    assert hasattr(proc, "getRelationships"), f"{proc.__class__.__name__}: missing getRelationships()"
    rels = proc.getRelationships()
    assert isinstance(rels, list) and rels, f"{proc.__class__.__name__}: getRelationships() must return non-empty list"
    names = []
    for r in rels:
        assert isinstance(r, Relationship), f"{proc.__class__.__name__}: relationship must be Relationship"
        assert isinstance(r.name, str) and r.name, "relationship.name must be non-empty str"
        names.append(r.name)
    assert len(names) == len(set(names)), f"{proc.__class__.__name__}: relationship names must be unique"

    log.info("Relationships [%s]: %s", proc.__class__.__name__, ", ".join(names))
    return set(names)


def _assert_properties(proc):
    if hasattr(proc, "getPropertyDescriptors"):
        pds = proc.getPropertyDescriptors()
        assert isinstance(pds, list), f"{proc.__class__.__name__}: getPropertyDescriptors() must return list"
        names = []
        for pd in pds:
            assert isinstance(pd, PropertyDescriptor), "each property must be PropertyDescriptor"
            nm = getattr(pd, "name", None)
            if nm:
                names.append(nm)
            desc = getattr(pd, "description", None)
            if desc is not None and not isinstance(desc, str):
                raise AssertionError("PropertyDescriptor.description must be str")
        if names:
            log.info("Properties [%s]: %s", proc.__class__.__name__, ", ".join(names))
        else:
            log.info("Properties [%s]: (none)", proc.__class__.__name__)


def test_all_processors_contract_and_smoke():
    log.info("Scanning processors under: %s", SRC_ROOT)
    found_any_module = False
    found_any_processor = False

    for mod_name in _iter_module_names():
        found_any_module = True
        log.info("Importing module: %s", mod_name)
        mod = importlib.import_module(mod_name)

        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ != mod.__name__:
                continue
            if not issubclass(cls, (FlowFileTransform, FlowFileSource, RecordTransform)):
                continue

            found_any_processor = True
            kind = "Transform" if issubclass(cls, FlowFileTransform) else \
                   "Source"    if issubclass(cls, FlowFileSource)   else \
                   "RecordTransform"
            log.info("Processor class found: %s (%s)", cls.__name__, kind)

            _assert_processor_details(cls)
            proc = cls()

            if issubclass(cls, FlowFileTransform):
                sig = inspect.signature(cls.transform)
                log.info("Method signature: %s.transform %s", cls.__name__, sig)
                assert list(sig.parameters) == ["self", "context", "flowfile"], f"{cls.__name__}.transform must be (self, context, flowfile)"
                rels = _assert_relationships(proc)
                assert "success" in rels, f"{cls.__name__} must declare 'success' relationship"
                _assert_properties(proc)

                class _FF:
                    def __init__(self, data=b"ping"):
                        self._data = data
                    def getContentsAsBytes(self):
                        return self._data
                class _Ctx: 
                    def getProperty(self, name):
                        # Значения по умолчанию для Smoke-тесирования.
                        # Реальных внешних вызовов не будет — HOST/PORT пустые моки.
                        defaults = {
                            "HOST": "localhost",
                            "PORT": "8000",
                            "System Prompt": "",
                            "Temperature": "0.7",
                        }
                        return defaults.get(name, "")


                res = proc.transform(_Ctx(), _FF())
                assert isinstance(res, FlowFileTransformResult)
                log.info("Smoke result: relationship=%s, contents_len=%s, attrs=%s",
                         res.relationship,
                         None if res.contents is None else len(res.contents),
                         list(res.attributes.keys()))
                assert res.relationship in rels

            elif issubclass(cls, FlowFileSource):
                sig = inspect.signature(cls.create)
                log.info("Method signature: %s.create %s", cls.__name__, sig)
                assert list(sig.parameters) == ["self", "context"], f"{cls.__name__}.create must be (self, context)"
                rels = _assert_relationships(proc)
                assert "success" in rels
                _assert_properties(proc)

                class _Ctx:
                    def getProperty(self, name):
                        # Значения по умолчанию для Smoke-тесирования.
                        # Реальных внешних вызовов не будет — HOST/PORT пустые моки.
                        defaults = {
                            "HOST": "localhost",
                            "PORT": "8000",
                            "System Prompt": "",
                            "Temperature": "0.7",
                        }
                        return defaults.get(name, "")
                res = proc.create(_Ctx())
                if res is None:
                    log.info("Smoke result: create() returned None (no FlowFile this tick)")
                else:
                    assert isinstance(res, FlowFileSourceResult)
                    log.info("Smoke result: relationship=%s, contents_len=%s, attrs=%s",
                             res.relationship,
                             None if res.contents is None else len(res.contents),
                             list(res.attributes.keys()))
                    assert res.relationship in rels

            elif issubclass(cls, RecordTransform):
                sig = inspect.signature(cls.transform)
                log.info("Method signature: %s.transform %s", cls.__name__, sig)
                assert list(sig.parameters) == ["self", "context", "record"], f"{cls.__name__}.transform must be (self, context, record)"
                rels = _assert_relationships(proc)
                assert "success" in rels
                _assert_properties(proc)

                class _Ctx: 
                    def getProperty(self, name):
                        # Значения по умолчанию для Smoke-тесирования.
                        # Реальных внешних вызовов не будет — HOST/PORT пустые моки.
                        defaults = {
                            "HOST": "localhost",
                            "PORT": "8000",
                            "System Prompt": "",
                            "Temperature": "0.7",
                        }
                        return defaults.get(name, "")
                sample = {"a": 1}
                res = proc.transform(_Ctx(), sample)
                assert isinstance(res, RecordTransformResult)
                log.info("Smoke result: relationship=%s, record_keys=%s, attrs=%s",
                         res.relationship, list(res.record.keys()), list(res.attributes.keys()))
                assert res.relationship in rels

    assert found_any_module, f"В '{SRC_ROOT}' не найдено ни одного модуля процессора (ожидаем src/<pkg>/*.py)."
    assert found_any_processor, "Не найдено ни одного класса-процессора (FlowFileTransform/FlowFileSource/RecordTransform)."
