import sqlite3
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "cookbook.db"


EXPECTED_TABLES = {
    "collections": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "name": {"type": "TEXT", "notnull": 1, "pk": 0},
            "description": {"type": "TEXT", "notnull": 0, "pk": 0},
        },
        "foreign_keys": [],
        "unique_indexes": [
            ["name"],
        ],
    },
    "recipes": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "collection_id": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "name": {"type": "TEXT", "notnull": 1, "pk": 0},
            "description": {"type": "TEXT", "notnull": 0, "pk": 0},
            "servings": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "prep_time": {"type": "INTEGER", "notnull": 1, "pk": 0},
        },
        "foreign_keys": [
            {
                "from": "collection_id",
                "to_table": "collections",
                "to_column": "id",
                "on_delete": "CASCADE",
            }
        ],
        "unique_indexes": [
            ["collection_id", "name"],
        ],
    },
    "steps": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "recipe_id": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "order_num": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "description": {"type": "TEXT", "notnull": 1, "pk": 0},
        },
        "foreign_keys": [
            {
                "from": "recipe_id",
                "to_table": "recipes",
                "to_column": "id",
                "on_delete": "CASCADE",
            }
        ],
        "unique_indexes": [
            ["recipe_id", "order_num"],
        ],
    },
    "ingredients": {
        "columns": {
            "id": {"type": "INTEGER", "notnull": 0, "pk": 1},
            "recipe_id": {"type": "INTEGER", "notnull": 1, "pk": 0},
            "name": {"type": "TEXT", "notnull": 1, "pk": 0},
            "amount": {"type": "REAL", "notnull": 1, "pk": 0},
            "unit": {"type": "TEXT", "notnull": 1, "pk": 0},
        },
        "foreign_keys": [
            {
                "from": "recipe_id",
                "to_table": "recipes",
                "to_column": "id",
                "on_delete": "CASCADE",
            }
        ],
        "unique_indexes": [],
    },
}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_tables(conn):
    rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()
    return [row["name"] for row in rows]


def get_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    result = {}
    for row in rows:
        result[row["name"]] = {
            "type": row["type"].upper(),
            "notnull": row["notnull"],
            "pk": row["pk"],
        }
    return result


def get_foreign_keys(conn, table_name):
    rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    result = []
    for row in rows:
        result.append({
            "from": row["from"],
            "to_table": row["table"],
            "to_column": row["to"],
            "on_delete": row["on_delete"].upper(),
        })
    return result


def get_unique_indexes(conn, table_name):
    indexes = conn.execute(f"PRAGMA index_list({table_name})").fetchall()
    unique_indexes = []

    for idx in indexes:
        if idx["unique"] == 1:
            idx_name = idx["name"]
            cols = conn.execute(f"PRAGMA index_info({idx_name})").fetchall()
            ordered_cols = [col["name"] for col in sorted(cols, key=lambda x: x["seqno"])]
            unique_indexes.append(ordered_cols)

    return unique_indexes


def count_rows(conn, table_name):
    row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table_name}").fetchone()
    return row["cnt"]


def print_pass(message):
    print(f"PASS: {message}")


def print_fail(message):
    print(f"FAIL: {message}")


def compare_columns(actual, expected, table_name):
    ok = True

    actual_names = set(actual.keys())
    expected_names = set(expected.keys())

    if actual_names != expected_names:
        missing = expected_names - actual_names
        extra = actual_names - expected_names
        if missing:
            print_fail(f"{table_name}: missing columns {sorted(missing)}")
        if extra:
            print_fail(f"{table_name}: unexpected columns {sorted(extra)}")
        ok = False

    for col_name, exp in expected.items():
        if col_name not in actual:
            continue

        act = actual[col_name]

        if act["type"] != exp["type"]:
            print_fail(
                f"{table_name}.{col_name}: type mismatch "
                f"(expected {exp['type']}, got {act['type']})"
            )
            ok = False

        if act["notnull"] != exp["notnull"]:
            print_fail(
                f"{table_name}.{col_name}: NOT NULL mismatch "
                f"(expected {exp['notnull']}, got {act['notnull']})"
            )
            ok = False

        if act["pk"] != exp["pk"]:
            print_fail(
                f"{table_name}.{col_name}: PK mismatch "
                f"(expected {exp['pk']}, got {act['pk']})"
            )
            ok = False

    if ok:
        print_pass(f"{table_name}: columns are correct")

    return ok


def compare_foreign_keys(actual, expected, table_name):
    ok = True

    if len(actual) != len(expected):
        print_fail(
            f"{table_name}: foreign key count mismatch "
            f"(expected {len(expected)}, got {len(actual)})"
        )
        return False

    for exp_fk in expected:
        if exp_fk not in actual:
            print_fail(f"{table_name}: missing foreign key {exp_fk}")
            ok = False

    if ok:
        print_pass(f"{table_name}: foreign keys are correct")

    return ok


def compare_unique_indexes(actual, expected, table_name):
    ok = True

    actual_sorted = sorted(actual)
    expected_sorted = sorted(expected)

    if actual_sorted != expected_sorted:
        print_fail(
            f"{table_name}: unique indexes mismatch "
            f"(expected {expected_sorted}, got {actual_sorted})"
        )
        ok = False
    else:
        print_pass(f"{table_name}: unique indexes are correct")

    return ok


def main():
    print(f"Checking database: {DB_PATH}")
    print("-" * 60)

    if not DB_PATH.exists():
        print_fail("Database file cookbook.db not found")
        sys.exit(1)

    conn = connect()
    all_ok = True

    actual_tables = get_tables(conn)
    expected_tables = sorted(EXPECTED_TABLES.keys())

    if sorted(actual_tables) != expected_tables:
        print_fail(f"Tables mismatch (expected {expected_tables}, got {actual_tables})")
        all_ok = False
    else:
        print_pass("All required tables exist")

    print("-" * 60)

    for table_name, expected in EXPECTED_TABLES.items():
        print(f"TABLE: {table_name}")

        actual_columns = get_columns(conn, table_name)
        actual_fks = get_foreign_keys(conn, table_name)
        actual_unique_indexes = get_unique_indexes(conn, table_name)

        table_ok = True
        table_ok &= compare_columns(actual_columns, expected["columns"], table_name)
        table_ok &= compare_foreign_keys(actual_fks, expected["foreign_keys"], table_name)
        table_ok &= compare_unique_indexes(
            actual_unique_indexes, expected["unique_indexes"], table_name
        )

        row_count = count_rows(conn, table_name)
        print(f"INFO: {table_name} row count = {row_count}")

        if not table_ok:
            all_ok = False

        print("-" * 60)

    conn.close()

    if all_ok:
        print("FINAL RESULT: DATABASE SCHEMA IS VALID")
        sys.exit(0)
    else:
        print("FINAL RESULT: DATABASE SCHEMA HAS PROBLEMS")
        sys.exit(1)


if __name__ == "__main__":
    main()