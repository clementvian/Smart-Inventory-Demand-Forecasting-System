from sqlalchemy import text
from db import get_server_engine, get_db_engine

DATABASE_NAME = "smart_inventory_db"


def main():
    server_engine = get_server_engine()

    with server_engine.begin() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {DATABASE_NAME}"))
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME}"))
        print(f"Database '{DATABASE_NAME}' reset and created successfully.")

    db_engine = get_db_engine()

    # Read the schema.sql file
    with open("schema.sql", "r") as f:
        schema_sql = f.read()

    # Split schema statements by semicolon and filter out empty ones
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

    with db_engine.begin() as conn:
        for statement in statements:
            # Skip the USE statement since our engine is already bound to the database
            if statement.upper().startswith("USE "):
                continue
            conn.execute(text(statement))
        print("All tables created successfully from schema.sql.")


if __name__ == "__main__":
    main()