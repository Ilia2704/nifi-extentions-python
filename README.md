# nifi-extentions-python

Here is the template and small sandbox to create your own nifi-processor with python env for NiFi 2.x

# NiFi Python Processor — Deploy & Runtime Guide

This README gives you **copy-paste** commands to:

* set up local dev/tests,
* ship your processor package(s) to a remote NiFi box,
* (re)create/update the processor’s Python environment (venv) on the server,
* and see where to configure NiFi for Python extensions.

---

## Project layout

```
src/
  hello_processor/
    __init__.py
    HelloTransform.py
    hello.py
    requirements.txt   # keep runtime deps here (inside the processor package)
tests/
  ...                  # your unit tests
  stab_test/           # strict contract tests (no NiFi needed)
```

> **Universal import** in `HelloTransform.py` (works both locally and on NiFi):

```python
try:
    import hello                      # NiFi runtime (top-level module)
except ImportError:
    from hello_processor import hello # local dev/tests (package import)
```

---

## 1) Local dev & tests

```bash
python3 -m venv .nifi_env
source .nifi_env/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install pytest

pytest -q

pytest tests -q
```

---

## 2) NiFi settings (where to look)

Edit `$NIFI_HOME/conf/nifi.properties` and ensure:

```properties
# Python Extensions
nifi.python.command=/usr/bin/python3
nifi.python.framework.source.directory=./python/framework
nifi.python.extensions.source.directory.default=./python/extensions
nifi.python.working.directory=./work/python
nifi.python.max.processes=100
nifi.python.max.processes.per.extension.type=10
```

On Ubuntu, make sure NiFi can create venvs:

```bash
sudo apt-get update && sudo apt-get install -y python3-venv
```

---

## 3) Ship your processor package(s) to the server

Set your params (adjust if needed):

```bash
# === set your server paths/addresses ===
PEM="path to .pem key"
HOST="host_ip"                 # your private/public IP
EXT_DIR="/opt/nifi/python/extensions"      # where processor code lives on the server
PKG="hello_processor"                       # your processor package name
```

Create the target dir, upload all processors from `src/`, and (optionally) upload `requirements.txt` inside your package:

```bash
# ensure target exists
ssh -i "$PEM" "$HOST" "mkdir -p '$EXT_DIR'"

# upload ALL packages from src/ (keeps folder names under extensions/)
scp -i "$PEM" -r src/* "$HOST:$EXT_DIR/"

# (optional) if your requirements is still at repo root,
# move it into the package locally first, so NiFi will pick it up:
# mv requirements.txt "src/$PKG/requirements.txt"
# scp -i "$PEM" "src/$PKG/requirements.txt" "$HOST:$EXT_DIR/$PKG/requirements.txt"

# clean bytecode caches (helps reloading after restart)
ssh -i "$PEM" "$HOST" "find '$EXT_DIR' -type d -name '__pycache__' -exec rm -rf {} +"
```

> **Best practice:** keep `requirements.txt` **inside each processor package**
> (e.g., `/opt/nifi/python/extensions/hello_processor/requirements.txt`) so NiFi installs those deps into the processor’s own venv.

---

## 4) Create/refresh the processor’s environment (venv) on the server

NiFi keeps per-processor venvs under:

```
$NIFI_HOME/work/python/extensions/<ProcessorName>/<Version>/
```

Pick **one** of the methods below.

### A) Bump the processor version → restart NiFi (recommended)

In your class:

```python
class ProcessorDetails:
    version = "0.1.3"   # bump this
    description = "..."
```

Then restart NiFi (it will create a new venv and install deps from the package’s `requirements.txt`):

```bash
sudo systemctl restart nifi
```

### B) Delete the current venv → start NiFi

```bash
sudo systemctl stop nifi

# remove venv(s) for this processor (match folder by package name)
sudo bash -lc '
  find /opt/nifi/work/python/extensions -type f -name pyvenv.cfg -printf "%h\n" \
  | grep -i "/hello_processor/" | xargs -r rm -rf
'

sudo systemctl start nifi
```

### C) Install deps into the existing venv (no version bump)

```bash
# find the venv dir for your processor
VENV_DIR=$(sudo bash -lc 'find /opt/nifi/work/python/extensions -type f -name pyvenv.cfg -printf "%h\n" \
            | grep -i "/hello_processor/" | head -n1'); echo "$VENV_DIR"

# install deps from the package-local requirements.txt
sudo "$VENV_DIR/bin/python" -m pip install --upgrade pip
sudo "$VENV_DIR/bin/pip" install -r "/opt/nifi/python/extensions/hello_processor/requirements.txt"
```

---

## 5) Quick self-check on the server (before/after restart)

Verify import and constructor with the same Python NiFi uses:

```bash
sudo -u nifi -H bash -lc '
export PYTHONPATH=/opt/nifi/python/api:/opt/nifi/python/framework:/opt/nifi/python/extensions
/usr/bin/python3 - <<PY
import importlib, traceback
try:
    m = importlib.import_module("hello_processor.HelloTransform")
    print("import OK:", m.__file__)
    from hello_processor.HelloTransform import HelloTransform
    p = HelloTransform(jvm=None)
    print("class OK:", type(p))
except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()
PY'
```

Check logs if something goes wrong:

```bash
tail -n 200 /opt/nifi/logs/nifi-app.log | grep -Ei "python|extensions|hello_processor|traceback" -n
```

---

## 6) Notes & common issues

* **Extra relationship `original` in UI:** NiFi auto-adds `original` for `FlowFileTransform`/`RecordTransform`. If unused, mark it **Auto-terminate** in the processor settings.
* **`ModuleNotFoundError: hello_processor` on NiFi:** Use the universal import shown above (`try: import hello … except: from hello_processor import hello`).
* **`TypeError: __init__ got unexpected keyword 'jvm'`:** add a constructor:

  ```python
  def __init__(self, jvm=None, **kwargs):
      self.jvm = jvm
      try: super().__init__()
      except Exception: pass
  ```

* **NiFi can’t create venv:** `sudo apt-get install -y python3-venv`.
* **Permissions:** ensure the NiFi service user can write to `$NIFI_HOME/work/python`:

  ```bash
  # if NiFi runs as 'nifi'
  sudo chown -R nifi:nifi /opt/nifi/work/python
  ```

---

## 7) Deployment checklist

1. Run tests locally: `pytest tests -q` → green.
2. Upload `src/*` to `/opt/nifi/python/extensions/`.
3. Ensure `requirements.txt` lives inside each processor package.
4. Refresh venv: **A)** bump `ProcessorDetails.version` and restart NiFi, **or**
   **B)** delete the processor’s venv and start NiFi, **or**
   **C)** install deps into the found venv.
5. Run the self-check script; confirm the processor is **Valid** in the NiFi UI.
6. Mark `original` as **Auto-terminate** if you don’t use it.
