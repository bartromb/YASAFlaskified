"""
tests/conftest.py — shared setup so `import app` is safe in a test run.

Importing `app` has module-level side effects: it creates UPLOAD_FOLDER,
PROCESSED_FOLDER and the instance directory, and opens a rotating log file.
The production defaults live under /data and /var/log, which are writable
neither in CI nor on a developer workstation.  `_cfg()` lets each of them be
overridden with a YASAFLASKIFIED_* environment variable, so we point them at
a throwaway directory *before* any test module imports `app`.

pytest imports conftest.py before the test modules, which is what makes this
work; nothing here may import `app` itself.
"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="yasaflaskified-tests-")

os.environ.setdefault("YASAFLASKIFIED_UPLOAD_FOLDER", os.path.join(_TMP, "uploads"))
os.environ.setdefault("YASAFLASKIFIED_PROCESSED_FOLDER", os.path.join(_TMP, "processed"))
os.environ.setdefault("YASAFLASKIFIED_LOG_FILE", os.path.join(_TMP, "logs", "app.log"))
os.environ.setdefault(
    "YASAFLASKIFIED_SQLALCHEMY_DATABASE_URI",
    "sqlite:///" + os.path.join(_TMP, "instance", "users.db"),
)
os.environ.setdefault("YASAFLASKIFIED_SECRET_KEY", "test-secret-key-not-for-production")
