"""Build a macOS single-file database importer with an embedded snapshot."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_NAME = f"category-encyclopedia-import-macos-{platform.machine()}"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from database_bundle import SNAPSHOT_FILENAME, export_snapshot  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="构建产品品类百科 macOS 数据导入器")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="源 MySQL 连接地址，也可通过 DATABASE_URL 提供",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "dist" / "database-bundle",
        help="可执行文件输出目录",
    )
    parser.add_argument("--name", default=DEFAULT_NAME, help="可执行文件名")
    parser.add_argument(
        "--target-architecture",
        default=platform.machine(),
        choices=("arm64", "x86_64", "universal2"),
        help="macOS 架构；需在对应 Python 环境中构建",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("构建时必须提供 --database-url 或 DATABASE_URL")
    if sys.platform != "darwin":
        raise SystemExit("当前构建脚本只面向 macOS，请在 macOS 上执行")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = REPO_ROOT / ".codex" / "database-bundle-build"
    work_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="database-bundle-") as temporary_dir:
        snapshot_path = Path(temporary_dir) / SNAPSHOT_FILENAME
        export_snapshot(args.database_url, snapshot_path)

        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            args.name,
            "--distpath",
            str(output_dir),
            "--workpath",
            str(work_dir / "work"),
            "--specpath",
            str(work_dir / "spec"),
            "--paths",
            str(BACKEND_ROOT),
            "--add-data",
            f"{snapshot_path}{os.pathsep}.",
            "--target-architecture",
            args.target_architecture,
            str(SCRIPT_DIR / "database_bundle.py"),
        ]
        subprocess.run(command, cwd=REPO_ROOT, check=True)

    artifact = output_dir / args.name
    if not artifact.exists():
        raise SystemExit(f"PyInstaller 未生成预期文件：{artifact}")
    artifact.chmod(artifact.stat().st_mode | 0o111)
    print(f"已生成可执行文件：{artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
