import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

try:
    # Ensure port is an integer
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT")),  # Convert port to integer
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    conn.autocommit = True

    # Example query: Create a new database (This typically should be done once, and not in regular code)
    # You might not need to create a database every time you run this script.
    db_create_query = """CREATE DATABASE rideradar;"""

    # Create a cursor object
    cur = conn.cursor()

    # Execute a query
    cur.execute(db_create_query)

    # Fetch results
    # rows = cur.fetchall()  # `fetchall()` is not necessary here as `CREATE DATABASE` does not return rows

    # Close the cursor and connection
    cur.close()
    conn.close()

    print("Database created successfully.")

except Exception as e:
    print(f"Error connecting to the database: {e}")
