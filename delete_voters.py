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

def delete_all_voters():
    conn = None
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM voters")
        deleted_count = cursor.rowcount
        
        conn.commit()

        print(f"Successfully deleted {deleted_count} voter(s) from the database.")
        logging.info(f"Deleted {deleted_count} voter(s) from the database")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logging.error(f"Database error: {e}")
        print(f"Error: Unable to delete voters. {e}")
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"An unexpected error occurred: {e}")
        print(f"An unexpected error occurred. Please check the log for details.")
    finally:
        if conn:
            cursor.close()
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    confirmation = input("Are you sure you want to delete ALL voters? This action cannot be undone. (yes/no): ")
    if confirmation.lower() == 'yes':
        delete_all_voters()
    else:
        print("Operation cancelled. No voters were deleted.")