"""Export and restore a portable snapshot of the current MySQL database.

The import path is intentionally self-contained so it can be packaged with
PyInstaller.  It only needs a reachable MySQL server; it does not require the
project source tree or an installed Python runtime on the target machine.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import gzip
import json
import os
import re
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import URL, Engine, make_url


if __package__ in {None, ""}:
    # Allow ``python backend/scripts/database_bundle.py`` from the repository root.
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

from app.database import Base  # noqa: E402
from app import models  # noqa: F401, E402


SNAPSHOT_FORMAT_VERSION = 1
CURRENT_ALEMBIC_REVISION = "f6a7b8c9d0e1"
SNAPSHOT_FILENAME = "category_encyclopedia_snapshot.json.gz"
SYSTEM_TABLES = {"alembic_version"}
DATABASE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_$]+$")
CONFIRMATION_TEXT = "OVERWRITE"


def _bundle_root() -> Path:
    bundled_root = getattr(sys, "_MEIPASS", None)
    if bundled_root:
        return Path(bundled_root)
    return Path(__file__).resolve().parent


def default_snapshot_path() -> Path:
    return _bundle_root() / SNAPSHOT_FILENAME


def _encode_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return {"__db_bundle_type__": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"__db_bundle_type__": "date", "value": value.isoformat()}
    if isinstance(value, time):
        return {"__db_bundle_type__": "time", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"__db_bundle_type__": "decimal", "value": str(value)}
    if isinstance(value, bytes):
        return {
            "__db_bundle_type__": "bytes",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, dict):
        return {str(key): _encode_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_value(item) for item in value]
    raise TypeError(f"Unsupported database value type: {type(value).__name__}")


def _decode_value(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
    if not isinstance(value, dict):
        return value

    marker = value.get("__db_bundle_type__")
    if marker == "datetime":
        return datetime.fromisoformat(value["value"])
    if marker == "date":
        return date.fromisoformat(value["value"])
    if marker == "time":
        return time.fromisoformat(value["value"])
    if marker == "decimal":
        return Decimal(value["value"])
    if marker == "bytes":
        return base64.b64decode(value["value"])
    return {key: _decode_value(item) for key, item in value.items()}


def _redacted_url(database_url: str) -> str:
    return make_url(database_url).render_as_string(hide_password=True)


def export_snapshot(database_url: str, output_path: Path) -> dict[str, int]:
    """Export all non-system tables into a compressed JSON snapshot."""

    engine = create_engine(database_url, pool_pre_ping=True)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    table_names = [table.name for table in metadata.sorted_tables if table.name not in SYSTEM_TABLES]

    tables: list[dict[str, Any]] = []
    total_rows = 0
    try:
        with engine.connect() as connection:
            for table_name in table_names:
                table = metadata.tables[table_name]
                rows = [
                    {key: _encode_value(value) for key, value in row.items()}
                    for row in connection.execute(table.select()).mappings()
                ]
                tables.append(
                    {
                        "name": table_name,
                        "columns": [column.name for column in table.columns],
                        "rows": rows,
                    }
                )
                total_rows += len(rows)
    finally:
        engine.dispose()

    snapshot = {
        "format_version": SNAPSHOT_FORMAT_VERSION,
        "alembic_revision": CURRENT_ALEMBIC_REVISION,
        "tables": tables,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, "wt", encoding="utf-8") as output:
        json.dump(snapshot, output, ensure_ascii=False, separators=(",", ":"))

    counts = {table["name"]: len(table["rows"]) for table in tables}
    counts["__total_rows__"] = total_rows
    print(f"已从 {_redacted_url(database_url)} 导出 {len(table_names)} 张表、{total_rows} 条记录")
    return counts


def load_snapshot(snapshot_path: Path) -> dict[str, Any]:
    if not snapshot_path.exists():
        raise FileNotFoundError(f"找不到数据库快照：{snapshot_path}")
    with gzip.open(snapshot_path, "rt", encoding="utf-8") as source:
        snapshot = json.load(source)

    if snapshot.get("format_version") != SNAPSHOT_FORMAT_VERSION:
        raise ValueError("数据库快照版本不受当前导入器支持")
    if not isinstance(snapshot.get("tables"), list):
        raise ValueError("数据库快照缺少 tables 数据")
    return snapshot


def _database_identifier(database_name: str) -> str:
    if not DATABASE_NAME_PATTERN.fullmatch(database_name):
        raise ValueError("数据库名只能包含字母、数字、下划线或美元符号")
    return f"`{database_name}`"


def _create_database(target_url: URL) -> None:
    if not target_url.database:
        raise ValueError("目标数据库连接地址必须包含数据库名")

    # SQLAlchemy keeps the existing database when ``database=None`` is passed;
    # an empty database component is what makes PyMySQL connect to the server.
    server_url = target_url.set(database="")
    server_engine = create_engine(server_url, pool_pre_ping=True)
    try:
        database_identifier = _database_identifier(target_url.database)
        with server_engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS {database_identifier} "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        server_engine.dispose()


def _build_target_url(args: argparse.Namespace) -> str:
    if args.database_url:
        return args.database_url

    password = os.getenv("DB_PASSWORD")
    if password is None:
        password = getpass.getpass(f"MySQL 密码（用户 {args.user}）：")
    return URL.create(
        "mysql+pymysql",
        username=args.user,
        password=password,
        host=args.host,
        port=args.port,
        database=args.database,
        query={"charset": "utf8mb4"},
    ).render_as_string(hide_password=False)


def _ensure_schema(engine: Engine) -> MetaData:
    # The target is intentionally built from the checked-in current model,
    # while the snapshot supplies the full data payload.
    Base.metadata.create_all(engine)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return metadata


def _restore_snapshot(database_url: str, snapshot: dict[str, Any]) -> dict[str, int]:
    target_url = make_url(database_url)
    _create_database(target_url)
    engine = create_engine(target_url, pool_pre_ping=True)
    try:
        metadata = _ensure_schema(engine)
        snapshot_tables = {table["name"]: table for table in snapshot["tables"]}
        expected_tables = set(snapshot_tables)
        actual_tables = set(metadata.tables) - SYSTEM_TABLES
        missing_tables = expected_tables - actual_tables
        if missing_tables:
            missing = ", ".join(sorted(missing_tables))
            raise RuntimeError(f"当前代码无法创建快照中的表：{missing}")

        with engine.connect() as connection:
            # Create this bookkeeping table before the data transaction. MySQL
            # implicitly commits DDL, so doing it inside the transaction would
            # weaken the rollback guarantee if a later insert failed.
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS alembic_version ("
                    "version_num VARCHAR(32) NOT NULL, "
                    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
                    ")"
                )
            )
            connection.commit()
            transaction = connection.begin()
            try:
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

                # Cover mode: clear every current application table before restore.
                for table in reversed(metadata.sorted_tables):
                    if table.name not in SYSTEM_TABLES:
                        connection.execute(table.delete())

                counts: dict[str, int] = {}
                for table_payload in snapshot["tables"]:
                    table_name = table_payload["name"]
                    table = metadata.tables[table_name]
                    columns = set(table_payload.get("columns", []))
                    actual_columns = {column.name for column in table.columns}
                    if columns != actual_columns:
                        missing_columns = columns - actual_columns
                        extra_columns = actual_columns - columns
                        raise RuntimeError(
                            f"表 {table_name} 的列与当前代码不一致；"
                            f"缺少={sorted(missing_columns)}，新增={sorted(extra_columns)}"
                        )

                    rows = [
                        {key: _decode_value(value) for key, value in row.items()}
                        for row in table_payload.get("rows", [])
                    ]
                    if rows:
                        connection.execute(table.insert(), rows)
                    counts[table_name] = len(rows)

                connection.execute(text("DELETE FROM alembic_version"))
                connection.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                    {"revision": snapshot.get("alembic_revision", CURRENT_ALEMBIC_REVISION)},
                )
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                transaction.commit()
            except BaseException:
                transaction.rollback()
                raise
    finally:
        engine.dispose()

    total_rows = sum(counts.values())
    counts["__total_rows__"] = total_rows
    return counts


def import_snapshot(database_url: str, snapshot_path: Path, *, confirm: bool) -> dict[str, int]:
    if not confirm:
        answer = input(
            "即将清空目标数据库中的项目表并恢复全部快照数据。"
            f"请输入 {CONFIRMATION_TEXT} 继续："
        ).strip()
        if answer != CONFIRMATION_TEXT:
            raise RuntimeError("已取消导入")

    snapshot = load_snapshot(snapshot_path)
    print(f"正在导入数据库快照：{snapshot_path}")
    counts = _restore_snapshot(database_url, snapshot)
    print(f"已恢复 {len(counts) - 1} 张表、{counts['__total_rows__']} 条记录")
    for table_name, count in counts.items():
        if table_name != "__total_rows__":
            print(f"  {table_name}: {count}")
    return counts


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="产品品类百科 MySQL 数据快照导入/导出工具",
    )
    subparsers = parser.add_subparsers(dest="command")

    export_parser = subparsers.add_parser("export", help="从源数据库导出快照")
    export_parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="源 MySQL 连接地址，也可通过 DATABASE_URL 提供",
    )
    export_parser.add_argument(
        "--output",
        type=Path,
        default=Path(SNAPSHOT_FILENAME),
        help=f"输出文件，默认：{SNAPSHOT_FILENAME}",
    )

    import_parser = subparsers.add_parser("import", help="将快照覆盖恢复到目标数据库")
    import_parser.add_argument(
        "--database-url",
        help="目标 MySQL 连接地址；不提供时使用下方参数并隐藏式询问密码",
    )
    import_parser.add_argument("--host", default="127.0.0.1")
    import_parser.add_argument("--port", type=int, default=3308)
    import_parser.add_argument("--user", default="root")
    import_parser.add_argument("--database", default="category_encyclopedia")
    import_parser.add_argument(
        "--snapshot",
        type=Path,
        default=default_snapshot_path(),
        help=f"快照文件，默认：{SNAPSHOT_FILENAME}",
    )
    import_parser.add_argument(
        "--yes",
        action="store_true",
        help="跳过覆盖确认，适用于已明确确认目标库为空的自动化执行",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    # The packaged binary is primarily an importer, so allow the short forms
    # ``./category-encyclopedia-import`` and ``./category-encyclopedia-import
    # --database-url ...`` without requiring the ``import`` subcommand.
    if raw_argv and raw_argv[0] not in {"export", "import", "-h", "--help"}:
        raw_argv.insert(0, "import")
    elif not raw_argv:
        raw_argv = ["import"]
    args = _parser().parse_args(raw_argv)
    command = args.command or "import"
    try:
        if command == "export":
            if not args.database_url:
                raise ValueError("导出时必须提供 --database-url 或 DATABASE_URL")
            export_snapshot(args.database_url, args.output)
        elif command == "import":
            database_url = _build_target_url(args)
            import_snapshot(database_url, args.snapshot, confirm=args.yes)
        else:
            raise ValueError(f"未知命令：{command}")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    except Exception as error:  # pragma: no cover - final user-facing safety net
        print(f"数据库导入失败：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
