import psycopg2
from psycopg2 import sql
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db_params = {
    "dbname": "evm_database",
    "user": "postgres",
    "password": "12345678",
    "host": "localhost",
    "port": "5432"
}

sample_parties = [
    ("Party 1", 0),
    ("Party 2", 0),
    ("Party 3", 0)
]

def create_parties_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS parties (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                votes INTEGER DEFAULT 0
            )
        """)
    conn.commit()
    logging.info("Parties table created or already exists.")

def insert_parties(conn, parties):
    with conn.cursor() as cur:
        for party in parties:
            cur.execute(
                sql.SQL("INSERT INTO parties (name, votes) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING"),
                party
            )
    conn.commit()
    logging.info(f"{len(parties)} parties inserted or skipped if already exist.")

def main():
    try:
        conn = psycopg2.connect(**db_params)
        logging.info("Connected to the database successfully.")

        create_parties_table(conn)

        insert_parties(conn, sample_parties)

        logging.info("Database population with parties completed successfully.")

    except psycopg2.Error as e:
        logging.error(f"Database error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    main()