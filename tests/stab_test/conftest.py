
import os
import sys
import types
import logging
from pathlib import Path


def _inject_nifiapi_stubs():
    for m in list(sys.modules):
        if m == "nifiapi" or m.startswith("nifiapi."):
            sys.modules.pop(m, None)

    from . import nifiapi_stub as stub

    # корневой пакет
    nifiapi_pkg = types.ModuleType("nifiapi")
    sys.modules["nifiapi"] = nifiapi_pkg

    # submodules
    fft = types.ModuleType("nifiapi.flowfiletransform")
    fft.FlowFileTransform = stub.FlowFileTransform
    fft.FlowFileTransformResult = stub.FlowFileTransformResult
    sys.modules["nifiapi.flowfiletransform"] = fft

    ffs = types.ModuleType("nifiapi.flowfilesource")
    ffs.FlowFileSource = stub.FlowFileSource
    ffs.FlowFileSourceResult = stub.FlowFileSourceResult
    sys.modules["nifiapi.flowfilesource"] = ffs

    rct = types.ModuleType("nifiapi.recordtransform")
    rct.RecordTransform = stub.RecordTransform
    rct.RecordTransformResult = stub.RecordTransformResult
    sys.modules["nifiapi.recordtransform"] = rct

    rel = types.ModuleType("nifiapi.relationship")
    rel.Relationship = stub.Relationship
    sys.modules["nifiapi.relationship"] = rel

    props = types.ModuleType("nifiapi.properties")
    props.PropertyDescriptor = stub.PropertyDescriptor
    props.StandardValidators = stub.StandardValidators
    props.ExpressionLanguageScope = stub.ExpressionLanguageScope
    sys.modules["nifiapi.properties"] = props


def pytest_sessionstart(session):
    _inject_nifiapi_stubs()

    repo_root = Path(os.getcwd())
    src_dir = repo_root / "src"
    if src_dir.is_dir():
        sys.path.insert(0, str(src_dir))

    level_name = os.environ.get("STABTEST_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s"
    )
