import psycopg2
import tkinter as tk
from tkinter import ttk, messagebox, font
from PIL import Image, ImageTk
import serial
import requests
from io import BytesIO
import os
import logging
from typing import List, Tuple, Optional

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
        self.root.title("EVM Voter Management System")
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

        self.search_var = tk.StringVar()
        self.selected_voter: Optional[Voter] = None

        self.setup_styles()
        self.create_widgets()
        self.create_party_votes_display()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        bg_color = "#f0f0f0"
        accent_color = "#3498db"
        text_color = "#2c3e50"

        self.root.configure(bg=bg_color)

        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabel", background=bg_color, foreground=text_color, font=('Helvetica', 12))
        self.style.configure("TButton", background=accent_color, foreground="white", font=('Helvetica', 12, 'bold'), padding=10)
        self.style.map("TButton", background=[('active', "#2980b9")])
        self.style.configure("Treeview", background="white", foreground=text_color, rowheight=25, font=('Helvetica', 11))
        self.style.configure("Treeview.Heading", font=('Helvetica', 12, 'bold'))
        self.style.map("Treeview", background=[('selected', accent_color)], foreground=[('selected', 'white')])

    def create_widgets(self):
        header_frame = ttk.Frame(self.root, padding="20 20 20 0")
        header_frame.pack(fill=tk.X)

        ttk.Label(header_frame, text="EVM Voter Management System", font=('Helvetica', 24, 'bold')).pack(side=tk.LEFT)

        search_frame = ttk.Frame(self.root, padding="20 10")
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self.search_var, font=('Helvetica', 12), width=40).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        ttk.Button(search_frame, text="Search", command=self.search_voter).pack(side=tk.LEFT, padx=(5, 0))

        content_frame = ttk.Frame(self.root, padding="20")
        content_frame.pack(expand=True, fill=tk.BOTH)

        list_frame = ttk.Frame(content_frame)
        list_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        self.voter_tree = ttk.Treeview(list_frame, columns=('ID', 'Name', 'Voted'), show='headings', selectmode='browse')
        self.voter_tree.heading('ID', text='ID')
        self.voter_tree.heading('Name', text='Name')
        self.voter_tree.heading('Voted', text='Voted')
        self.voter_tree.column('ID', width=100)
        self.voter_tree.column('Name', width=200)
        self.voter_tree.column('Voted', width=100)
        self.voter_tree.pack(expand=True, fill=tk.BOTH)
        self.voter_tree.bind('<<TreeviewSelect>>', self.on_voter_select)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.voter_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.voter_tree.configure(yscrollcommand=scrollbar.set)

        details_frame = ttk.Frame(content_frame, padding="0 0 0 20")
        details_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.voter_name_label = ttk.Label(details_frame, text="Name: ", font=('Helvetica', 14, 'bold'))
        self.voter_name_label.pack(anchor=tk.W, pady=(0, 10))

        self.voter_image_label = ttk.Label(details_frame)
        self.voter_image_label.pack(pady=(0, 20))

        self.mark_voted_button = ttk.Button(details_frame, text="Mark as Voted", command=self.mark_as_voted)
        self.mark_voted_button.pack(fill=tk.X)

        self.end_voting_button = ttk.Button(details_frame, text="End Voting", command=self.end_voting)
        self.end_voting_button.pack(fill=tk.X, pady=(10, 0))

        self.placeholder_image = ImageTk.PhotoImage(Image.new('RGB', (200, 200), color='#d0d0d0'))
        self.voter_image_label.config(image=self.placeholder_image)

    def create_party_votes_display(self):
        votes_frame = ttk.Frame(self.root, padding="20")
        votes_frame.pack(fill=tk.X)

        ttk.Label(votes_frame, text="Party Votes:", font=('Helvetica', 16, 'bold')).pack(anchor=tk.W)

        self.party_votes_labels = {}
        for party_id in range(1, 4):
            label = ttk.Label(votes_frame, text=f"Party {party_id}: 0", font=('Helvetica', 14))
            label.pack(anchor=tk.W)
            self.party_votes_labels[party_id] = label

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
                    (str(voter_id),)
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
                    image = image.resize((200, 200))
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

    def update_party_votes_display(self):
        try:
            for party_id in range(1, 4):
                votes = self.db_manager.execute_query(
                    "SELECT votes FROM parties WHERE id = %s",
                    (party_id,)
                )[0][0]
                self.party_votes_labels[party_id].config(text=f"Party {party_id}: {votes}")
        except psycopg2.Error as e:
            logging.error(f"Error updating party votes display: {e}")

    def increment_party_vote(self, party_id: int):
        try:
            self.db_manager.execute_query(
                "UPDATE parties SET votes = votes + 1 WHERE id = %s",
                (party_id,)
            )
            self.db_manager.commit()
            self.update_party_votes_display()
            logging.info(f"Incremented vote for Party {party_id}")
        except psycopg2.Error as e:
            logging.error(f"Error incrementing party vote: {e}")

    def check_arduino(self) -> None:
        data = self.arduino_manager.read_data()
        if data:
            if data in ["1", "2", "3"]:
                party_id = int(data)
                self.increment_party_vote(party_id)
            elif data == "4":  # Assuming '4' is sent when a voter is marked as voted
                self.mark_as_voted()

        self.root.after(100, self.check_arduino)

    def end_voting(self):
        try:
            parties = self.db_manager.execute_query("SELECT id, name, votes FROM parties ORDER BY votes DESC")
            total_votes = sum(party[2] for party in parties)
            
            result_window = tk.Toplevel(self.root)
            result_window.title("Voting Results")
            result_window.geometry("400x300")

            ttk.Label(result_window, text="Voting Results", font=('Helvetica', 18, 'bold')).pack(pady=10)

            for party in parties:
                party_id, party_name, votes = party
                percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
                ttk.Label(result_window, text=f"{party_name}: {votes} votes ({percentage:.2f}%)", font=('Helvetica', 14)).pack()

            if len(parties) > 1 and parties[0][2] == parties[1][2]:
                ttk.Label(result_window, text="\nThere is a tie between:", font=('Helvetica', 14, 'bold')).pack()
                tied_parties = [p[1] for p in parties if p[2] == parties[0][2]]
                ttk.Label(result_window, text=" and ".join(tied_parties), font=('Helvetica', 14)).pack()
            else:
                winner = parties[0]
                ttk.Label(result_window, text=f"\nWinner: {winner[1]}", font=('Helvetica', 16, 'bold')).pack()
                
                majority = (winner[2] / total_votes) > 0.5 if total_votes > 0 else False
                if majority:
                    ttk.Label(result_window, text="Majority achieved", font=('Helvetica', 14)).pack()
                else:
                    ttk.Label(result_window, text="No majority achieved", font=('Helvetica', 14)).pack()

        except psycopg2.Error as e:
            messagebox.showerror("Error", f"Unable to retrieve voting results: {e}")

    def run(self) -> None:
        self.refresh_voter_list()
        self.update_party_votes_display()
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