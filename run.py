"""一键启动：生成数据 -> 评测 -> 启动 FastAPI 服务。

用法：
    python run.py            # 默认 0.0.0.0:8000
    python run.py --no-eval  # 跳过评测，直接启动
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    print(">>", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", default="8000")
    ap.add_argument("--no-eval", action="store_true", help="跳过评测")
    ap.add_argument("--no-gen", action="store_true", help="跳过数据生成")
    args = ap.parse_args()

    if not args.no_gen:
        run([sys.executable, "-B", "scripts/generate_data.py"])
    if not args.no_eval:
        run([sys.executable, "-B", "scripts/evaluate.py"])
    run([sys.executable, "-B", "-m", "uvicorn", "app.main:app",
         "--host", args.host, "--port", args.port])


if __name__ == "__main__":
    main()
