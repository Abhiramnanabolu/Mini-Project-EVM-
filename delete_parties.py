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

def delete_parties_table():
    conn = None
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS parties")
        
        conn.commit()

        logging.info("Parties table has been deleted successfully.")

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
    delete_parties_table()