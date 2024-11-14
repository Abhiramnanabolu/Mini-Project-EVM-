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

def add_voter(voter_id, name, image_url):
    conn = None
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO voters (id, name, image_url, has_voted) VALUES (%s, %s, %s, FALSE)",
            (voter_id, name, image_url)
        )
        
        conn.commit()

        logging.info(f"Added new voter: ID={voter_id}, Name={name}")

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
    print("Please enter the following information for the new voter:")
    voter_id = input("Enter ID: ")
    name = input("Enter Name: ")
    image_url = input("Enter image URL: ")
    
    add_voter(voter_id, name, image_url)