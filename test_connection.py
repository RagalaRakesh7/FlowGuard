
from app.db import get_connection


def test_mysql_connection():
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE(), VERSION()")
        result = cursor.fetchone()

        print("\nFLOWGUARD DATABASE MODULE WORKING!")
        print("Database:", result[0])
        print("MySQL Version:", result[1])

        assert result[0] == "flowguard_db"

        cursor.close()

    finally:
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    test_mysql_connection()
