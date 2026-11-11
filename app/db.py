
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE, override=True)


def get_connection():
    required_variables = ["DB_HOST", "DB_USER", "DB_NAME"]

    missing = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing:
        raise ValueError(
            f"Missing database configuration: {', '.join(missing)}"
        )

    connection = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME"),
        connection_timeout=5,
        autocommit=False
    )

    return connection
