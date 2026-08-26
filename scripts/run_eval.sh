#!/usr/bin/env bash
# 一键评测（生成数据 -> 评测 -> 单元测试 + 覆盖率）
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)"
python scripts/generate_data.py
python scripts/evaluate.py
python -m pytest tests/ -q --cov=app --cov-report=term-missing
