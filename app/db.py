import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("cookbook.db")


def get_connection():
    logger.info("Opening SQLite connection to %s", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    logger.info("Initializing database schema")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        collection_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        servings INTEGER NOT NULL,
        prep_time INTEGER NOT NULL,
        FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
        UNIQUE(collection_id, name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        order_num INTEGER NOT NULL,
        description TEXT NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
        UNIQUE(recipe_id, order_num)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        unit TEXT NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")
    print("Database initialized successfully.")


if __name__ == "__main__":
    from app.logging_config import setup_logging

    setup_logging()
    init_db()