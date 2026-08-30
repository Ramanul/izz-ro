#!/bin/bash
# SessionStart hook — install the pipeline's Python deps so `python -m generator.main`,
# tools/audit.sh, tools/qa_check.py and the project sub-agents work in a fresh cloud
# container. A machine that already has the deps is skipped.
set -euo pipefail

# Resolve the repo root from this script's own location, so the hook works on any machine
# and under any agent CLI. The ported version hardcoded C:\Users\cw_26\izz-ro\... and only
# ran there.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$here/../.." && pwd)"

# Gate on the actual condition — are the deps missing? — instead of on CLAUDE_CODE_REMOTE.
# That variable is set by Claude Code and by nothing else, so under Codex the ported hook
# took this branch every single time and exited before doing any work.
if python -c 'import feedparser, jinja2, yaml' >/dev/null 2>&1; then
  exit 0
fi

# feedparser pulls in sgmllib3k, whose wheel fails to build against the container's
# system setuptools under PEP 517 isolation, which aborts the whole install. Forcing
# the stdlib distutils shim lets it build (verified: feedparser 6.0.12 installs & imports).
export SETUPTOOLS_USE_DISTUTILS=stdlib

pip install -q -r "$repo_root/requirements.txt"
