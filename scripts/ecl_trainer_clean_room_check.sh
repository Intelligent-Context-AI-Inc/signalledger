#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="/tmp/ecl-trainer-rc-test"

cd "$ROOT_DIR"
python3 -m build
rm -rf "$VENV_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install dist/ecl_trainer-0.1.0rc1-py3-none-any.whl
python - <<'PY'
import socket

class BlockedSocket(socket.socket):
    def __init__(self, *args, **kwargs):
        raise RuntimeError("network disabled during import check")

socket.socket = BlockedSocket
import ecl_trainer

print(ecl_trainer.SDK_VERSION)
PY
ecl-trainer --help
ecl-trainer scan --help
ecl-trainer passport --help
ecl-trainer verify-log --help
ecl-trainer render-pr-comment --help
ecl-trainer github-action --help
ecl-trainer gitlab-ci --help
ecl-trainer hf-card-export --help
ecl-trainer supply-chain-evidence --help
ecl-trainer lifecycle --help
ecl-trainer lifecycle check --help
ecl-trainer lifecycle apply-patch --help
