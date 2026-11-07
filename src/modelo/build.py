"""Construye el data warehouse ejecutando los archivos de sql/ en orden.

Este archivo ya está completo: el trabajo del reto está en los .sql y en
scd2.py. Uso:

    python -m modelo.build data/raw warehouse.duckdb
"""

import sys
import time
from pathlib import Path

import duckdb

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def sql_files() -> list[Path]:
    return sorted(SQL_DIR.glob("[0-9][0-9]_*.sql"))


def build_warehouse(con: duckdb.DuckDBPyConnection, raw_dir: str | Path) -> None:
    """Ejecuta cada archivo NN_*.sql. Dentro de los .sql, {{raw_dir}} se
    reemplaza por la carpeta donde están los CSV de Olist."""
    raw_dir = Path(raw_dir).resolve().as_posix()
    for path in sql_files():
        t0 = time.perf_counter()
        sql = path.read_text(encoding="utf-8").replace("{{raw_dir}}", raw_dir)
        try:
            con.execute(sql)
        except duckdb.Error as exc:
            raise RuntimeError(f"Falló {path.name}: {exc}") from exc
        print(f"[build] {path.name} ({time.perf_counter() - t0:.2f}s)")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("Uso: python -m modelo.build <carpeta_csv> <archivo.duckdb>")
    raw_dir, db_file = sys.argv[1], sys.argv[2]
    with duckdb.connect(db_file) as con:
        build_warehouse(con, raw_dir)
        for (table,) in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name LIKE 'dim_%' OR table_name LIKE 'fact_%' ORDER BY 1"
        ).fetchall():
            n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table:<20} {n:>10,} filas")


if __name__ == "__main__":
    main()
