#!/bin/bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
pytest tests/test_srt.py -v

