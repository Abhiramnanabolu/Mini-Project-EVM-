import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

db_params = {
    "dbname": "evm_database",
    "user": "postgres",
    "password": "12345678",
    "host": "localhost",
    "port": "5432"
}

def reset_votes():
    conn = None
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        cursor.execute("UPDATE parties SET votes = 0")
        
        conn.commit()

        affected_rows = cursor.rowcount
        logging.info(f"Reset votes for {affected_rows} parties.")

        cursor.execute("UPDATE voters SET has_voted = FALSE")
        
        conn.commit()

        affected_voters = cursor.rowcount
        logging.info(f"Reset voting status for {affected_voters} voters.")

    except psycopg2.Error as e:
        logging.error(f"Database error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    reset_votes()