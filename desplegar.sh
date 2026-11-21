#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    echo 'Se requiere Python 3.10 o posterior.' >&2
    exit 1
fi
export PYTHONUTF8=1
python3 -m unittest discover -s tests -v
python3 -m finops "$@"
