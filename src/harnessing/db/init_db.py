from pathlib import Path

from sqlite_utils import Database

from .schema import DB_PATH, SCHEMA


def init_db(db_path: Path | None = None) -> Database:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(str(path))
    for table_name, columns in SCHEMA.items():
        if table_name not in db.table_names():
            db[table_name].create(columns)  # type: ignore[union-attr]
    return db

if __name__ == "__main__":
    db = init_db()
    print(f"Database initialized at: {DB_PATH}")
    for table in db.table_names():
        print(f"  - {table}: {db[table].count} rows")
