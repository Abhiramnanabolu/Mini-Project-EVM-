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

sample_voters = [
    ("1", "Narendra Modi", "https://res.cloudinary.com/dbs6hvga4/image/upload/v1730199397/WhatsApp_Image_2024-10-29_at_16.14.31_8f4fefb5_fybtcu.jpg", False),
    ("2", "Rahul Gandhi", "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Rahul_Gandhi.png/330px-Rahul_Gandhi.png", False),
    ("3", "Bob Johnson", "https://res.cloudinary.com/dbs6hvga4/image/upload/v1730199397/WhatsApp_Image_2024-10-29_at_16.14.31_8f4fefb5_fybtcu.jpg", False),
    ("4", "Kasula Raghu", "https://res.cloudinary.com/dbs6hvga4/image/upload/v1730202683/Screenshot_2024-10-29_172021_ctfogy.png", False),
    ("5", "Dr G Madhavi", "https://res.cloudinary.com/dbs6hvga4/image/upload/v1730202683/Screenshot_2024-10-29_172053_yrd5bv.png", False),
    ("6", "Dr S Srinivasa Rao", "https://res.cloudinary.com/dbs6hvga4/image/upload/v1730202876/Screenshot_2024-10-29_172405_w1cvdu.png", False),
    ("7", "Dhruva Gupta", "https://media.licdn.com/dms/image/v2/D5603AQEPl39dPufM7g/profile-displayphoto-shrink_200_200/profile-displayphoto-shrink_200_200/0/1703523040663?e=2147483647&v=beta&t=NTXOLDM-klJ-AgXYxRZvwYtVbzvZAnyOy1QtXqqLImA", False),
]

def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS voters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                image_url TEXT,
                has_voted BOOLEAN DEFAULT FALSE
            )
        """)
    conn.commit()
    logging.info("Voters table created or already exists.")

def insert_voters(conn, voters):
    with conn.cursor() as cur:
        for voter in voters:
            cur.execute(
                sql.SQL("INSERT INTO voters (id, name, image_url, has_voted) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING"),
                voter
            )
    conn.commit()
    logging.info(f"{len(voters)} voters inserted or skipped if already exist.")

def main():
    try:
        conn = psycopg2.connect(**db_params)
        logging.info("Connected to the database successfully.")

        create_table(conn)

        insert_voters(conn, sample_voters)

        logging.info("Database population completed successfully.")

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