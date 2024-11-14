import psycopg2
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import serial
import requests
from io import BytesIO
import os
import logging
from typing import List, Tuple, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self, dbname: str, user: str, password: str, host: str, port: str):
        self.conn_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.cursor: Optional[psycopg2.extensions.cursor] = None

    def connect(self) -> None:
        try:
            logging.info(f"Attempting to connect to database: {self.conn_params['dbname']}")
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor()
            logging.info("Successfully connected to the database.")

            # Create voters table if it doesn't exist
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS voters (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    image_url TEXT,
                    has_voted BOOLEAN
                )
            """)
            self.conn.commit()

            self.cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = self.cursor.fetchall()
            logging.info(f"Tables in the database: {tables}")

        except psycopg2.Error as e:
            logging.error(f"PostgreSQL error occurred: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during database connection: {e}")
            raise

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")

    def execute_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        if not self.conn or not self.cursor:
            logging.error("Database connection is not established.")
            raise psycopg2.Error("Database connection is not established.")
        
        try:
            self.cursor.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                return self.cursor.fetchall()
            else:
                self.conn.commit()
                return []
        except psycopg2.Error as e:
            logging.error(f"Database error: {e}")
            raise

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()

class ArduinoManager:
    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate
        self.arduino: Optional[serial.Serial] = None

    def connect(self) -> None:
        try:
            self.arduino = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=0.1)
            logging.info("Successfully connected to Arduino.")
        except serial.SerialException as e:
            logging.error(f"Error connecting to Arduino: {e}")
            raise

    def read_data(self) -> str:
        if self.arduino and self.arduino.in_waiting:
            return self.arduino.readline().decode('utf-8').strip()
        return ""

class Voter:
    def __init__(self, id: str, name: str, image_url: str, has_voted: bool):
        self.id = id
        self.name = name
        self.image_url = image_url
        self.has_voted = has_voted

class EVMGUI:
    def __init__(self, db_manager: DatabaseManager, arduino_manager: ArduinoManager):
        self.db_manager = db_manager
        self.arduino_manager = arduino_manager
        self.root = tk.Tk()
        self.root.title("EVM Voter List")
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

        self.search_var = tk.StringVar()
        self.selected_voter: Optional[Voter] = None

        self.create_widgets()

    def create_widgets(self) -> None:
        # Search frame
        search_frame = ttk.Frame(self.root, padding="10")
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        ttk.Button(search_frame, text="Search", command=self.search_voter).pack(side=tk.LEFT, padx=(5, 0))

        # Voter list
        self.voter_tree = ttk.Treeview(self.root, columns=('ID', 'Name', 'Voted'), show='headings')
        self.voter_tree.heading('ID', text='ID')
        self.voter_tree.heading('Name', text='Name')
        self.voter_tree.heading('Voted', text='Voted')
        self.voter_tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.voter_tree.bind('<<TreeviewSelect>>', self.on_voter_select)

        # Voter details frame
        details_frame = ttk.Frame(self.root, padding="10")
        details_frame.pack(fill=tk.X)

        self.voter_name_label = ttk.Label(details_frame, text="Name: ")
        self.voter_name_label.pack(side=tk.LEFT)

        self.voter_image_label = ttk.Label(details_frame)
        self.voter_image_label.pack(side=tk.LEFT, padx=(10, 0))

        self.mark_voted_button = ttk.Button(details_frame, text="Mark as Voted", command=self.mark_as_voted)
        self.mark_voted_button.pack(side=tk.RIGHT)

        # Create a placeholder image
        self.placeholder_image = ImageTk.PhotoImage(Image.new('RGB', (100, 100), color='gray'))
        self.voter_image_label.config(image=self.placeholder_image)

    def search_voter(self) -> None:
        query = self.search_var.get()
        try:
            voters = self.db_manager.execute_query(
                "SELECT id, name, image_url, has_voted FROM voters WHERE name ILIKE %s OR id ILIKE %s",
                ('%' + query + '%', '%' + query + '%')
            )
            self.update_voter_list(voters)
        except psycopg2.Error as e:
            messagebox.showerror("Search Error", f"Unable to search for voter: {e}")

    def update_voter_list(self, voters: List[Tuple]) -> None:
        self.voter_tree.delete(*self.voter_tree.get_children())
        for voter in voters:
            self.voter_tree.insert('', 'end', values=(voter[0], voter[1], 'Yes' if voter[3] else 'No'))

    def on_voter_select(self, event) -> None:
        selection = self.voter_tree.selection()
        if selection:
            voter_id = self.voter_tree.item(selection[0])['values'][0]
            try:
                voter_data = self.db_manager.execute_query(
                    "SELECT id, name, image_url, has_voted FROM voters WHERE id = %s",
                    (str(voter_id,))
                )[0]
                self.selected_voter = Voter(*voter_data)
                self.display_voter_details()
            except psycopg2.Error as e:
                messagebox.showerror("Error", f"Unable to fetch voter details: {e}")

    def display_voter_details(self) -> None:
        if self.selected_voter:
            self.voter_name_label.config(text=f"Name: {self.selected_voter.name}")
            self.load_voter_image()
            self.mark_voted_button.config(state=tk.NORMAL if not self.selected_voter.has_voted else tk.DISABLED)

    def load_voter_image(self) -> None:
        self.voter_image_label.config(image=self.placeholder_image)
        if self.selected_voter:
            try:
                response = requests.get(self.selected_voter.image_url)
                if response.status_code == 200 and response.headers['Content-Type'].startswith('image'):
                    image = Image.open(BytesIO(response.content))
                    image = image.resize((100, 100))
                    photo = ImageTk.PhotoImage(image)
                    self.voter_image_label.config(image=photo)
                    self.voter_image_label.image = photo
            except Exception as e:
                logging.error(f"Error loading image: {e}")

    def mark_as_voted(self) -> None:
        if self.selected_voter and not self.selected_voter.has_voted:
            try:
                self.db_manager.execute_query(
                    "UPDATE voters SET has_voted = TRUE WHERE id = %s",
                    (self.selected_voter.id,)
                )
                self.db_manager.commit()
                messagebox.showinfo("Vote", f"{self.selected_voter.name} has been marked as voted.")
                self.selected_voter.has_voted = True
                self.refresh_voter_list()
            except psycopg2.Error as e:
                messagebox.showerror("Error", f"Unable to update database: {e}")

    def refresh_voter_list(self) -> None:
        try:
            voters = self.db_manager.execute_query("SELECT id, name, image_url, has_voted FROM voters")
            self.update_voter_list(voters)
        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Unable to refresh voter list: {e}")

    def check_arduino(self) -> None:
        data = self.arduino_manager.read_data()
        if data:
            if data == "1":
                self.mark_as_voted()
            # Add more conditions for other Arduino signals if needed

        self.root.after(100, self.check_arduino)

    def run(self) -> None:
        self.refresh_voter_list()
        self.check_arduino()
        self.root.mainloop()

def main():
    db_manager = DatabaseManager(
        dbname="evm_database",
        user="postgres",
        password="12345678",
        host="localhost",
        port="5432"
    )
    arduino_manager = ArduinoManager('COM4', 9600)

    try:
        db_manager.connect()
        arduino_manager.connect()
        
        gui = EVMGUI(db_manager, arduino_manager)
        gui.run()
    except psycopg2.Error as e:
        logging.error(f"PostgreSQL error: {e}")
        messagebox.showerror("Database Error", f"PostgreSQL error: {e}\nPlease check your database configuration and ensure the server is running.")
    except serial.SerialException as e:
        logging.error(f"Arduino connection error: {e}")
        messagebox.showerror("Arduino Error", f"Unable to connect to Arduino: {e}\nPlease check if the Arduino is connected and the COM port is correct.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
    finally:
        db_manager.disconnect()

if __name__ == "__main__":
    main()