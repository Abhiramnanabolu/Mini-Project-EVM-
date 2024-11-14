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

def print_voters():
    conn = None
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, image_url, has_voted FROM voters ORDER BY id")
        voters = cursor.fetchall()

        print("\nVoter List:")
        print("===========")
        for voter in voters:
            print(f"ID: {voter[0]}, Name: {voter[1]}, Image URL: {voter[2]}, Has Voted: {voter[3]}")

        logging.info("Voter list has been printed successfully")

    except psycopg2.Error as e:
        logging.error(f"Database error: {e}")
        print(f"Error: Unable to connect to the database. Please check your connection settings.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        print(f"An unexpected error occurred. Please check the log for details.")
    finally:
        if conn:
            cursor.close()
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    print_voters()