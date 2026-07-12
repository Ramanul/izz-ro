#!/bin/bash
# SessionStart hook — install the pipeline's Python deps so `python -m generator.main`,
# tools/audit.sh, tools/qa_check.py and the project sub-agents work in Claude Code on the web.
# Local machines (Python 3.14, deps already present) are skipped.
set -euo pipefail

# Web sessions only — don't touch the owner's local environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# feedparser pulls in sgmllib3k, whose wheel fails to build against the container's
# system setuptools under PEP 517 isolation, which aborts the whole install. Forcing
# the stdlib distutils shim lets it build (verified: feedparser 6.0.12 installs & imports).
export SETUPTOOLS_USE_DISTUTILS=stdlib

pip install -q -r "${CLAUDE_PROJECT_DIR}/requirements.txt"
