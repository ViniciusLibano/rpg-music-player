#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"
exec .venv/bin/python3 main.py --debug "$@"
