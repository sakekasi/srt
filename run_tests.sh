#!/bin/bash
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
pytest tests/test_srt.py -v 2>&1 | tee test_output.txt