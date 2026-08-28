"""Test isolation.

Everything here runs before the test modules import `app.*`, which is what
lets us swap in a throwaway database and storage directory. `backend/.env` is
deliberately ignored so a developer's real Postgres URL or API keys can never
be reached by the suite.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import app.config as config

TMP_ROOT = Path(tempfile.mkdtemp(prefix="career-coach-tests-"))

config.Settings.model_config["env_file"] = None

os.environ.update(
    {
        "APP_ENV": "test",
        "SECRET_KEY": "test-secret-not-used-anywhere-real",
        "DATABASE_URL": f"sqlite:///{(TMP_ROOT / 'test.db').as_posix()}",
        "STORAGE_DIR": str(TMP_ROOT / "storage"),
        "FRONTEND_URL": "http://testserver",
        "ADMIN_EMAIL": "admin@careercoach.app",
        "ADMIN_PASSWORD": "SeededAdmin123!",
        # Real limits would make the suite order-dependent and flaky.
        "RATE_LIMIT_ENABLED": "false",
        # No network calls: every agent must fall back to its offline path.
        "LLM_API_KEY": "",
        "GROQ_API_KEY": "",
        "GEMINI_API_KEY": "",
        "DEEPSEEK_API_KEY": "",
        "EMBEDDING_API_KEY": "",
        "STRIPE_SECRET_KEY": "",
        "SMTP_HOST": "",
        "R2_ACCOUNT_ID": "",
    }
)

config.get_settings.cache_clear()


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TMP_ROOT, ignore_errors=True)
