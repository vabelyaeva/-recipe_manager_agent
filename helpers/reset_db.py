from app.db import get_connection


def clear_all_data():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM ingredients")
    cursor.execute("DELETE FROM steps")
    cursor.execute("DELETE FROM recipes")
    cursor.execute("DELETE FROM collections")

    conn.commit()
    conn.close()

    print("All test data deleted successfully.")


if __name__ == "__main__":
    clear_all_data()