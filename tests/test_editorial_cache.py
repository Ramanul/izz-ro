"""Run the real offline/update JavaScript contracts with the publication suite."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_offline_and_update_contracts():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the service worker contracts")
    result = subprocess.run([node, "--test", "tests/editorial_cache.test.mjs"],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
