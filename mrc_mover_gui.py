import os
import shutil
import time
import logging
from datetime import datetime
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk
import threading
import json

class MRCMoverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MRC File Mover")
        self.root.geometry("600x400")
        
        # Variables
        self.source_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready to start...")
        self.is_running = False
        
        # Load saved paths if they exist
        self.load_saved_paths()
        
        self.create_gui()
        self.mover = None
        self.mover_thread = None

    def load_saved_paths(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    self.source_path.set(config.get('source', ''))
                    self.dest_path.set(config.get('dest', ''))
        except Exception as e:
            logging.error(f"Error loading config: {e}")

    def save_paths(self):
        try:
            config = {
                'source': self.source_path.get(),
                'dest': self.dest_path.get()
            }
            with open('config.json', 'w') as f:
                json.dump(config, f)
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def create_gui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Source directory selection
        ttk.Label(main_frame, text="Source Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.source_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_source).grid(row=0, column=2)

        # Destination directory selection
        ttk.Label(main_frame, text="Destination Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.dest_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_dest).grid(row=1, column=2)

        # Start/Stop button
        self.start_stop_button = ttk.Button(main_frame, text="Start", command=self.toggle_mover)
        self.start_stop_button.grid(row=2, column=1, pady=20)

        # Status display
        ttk.Label(main_frame, text="Status:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, textvariable=self.status_text).grid(row=3, column=1, sticky=tk.W)

        # Log display
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.log_text = tk.Text(log_frame, height=10, width=60)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def browse_source(self):
        path = filedialog.askdirectory()
        if path:
            self.source_path.set(path)
            self.save_paths()

    def browse_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_path.set(path)
            self.save_paths()

    def update_log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def toggle_mover(self):
        if not self.is_running:
            if not self.source_path.get() or not self.dest_path.get():
                self.update_log("Please select both source and destination directories.")
                return
                
            self.is_running = True
            self.start_stop_button.configure(text="Stop")
            self.status_text.set("Running...")
            self.mover = MRCFileMover(self.source_path.get(), self.dest_path.get(), self.update_log)
            self.mover_thread = threading.Thread(target=self.mover.run)
            self.mover_thread.daemon = True
            self.mover_thread.start()
        else:
            self.is_running = False
            self.start_stop_button.configure(text="Start")
            self.status_text.set("Stopped")
            if self.mover:
                self.mover.stop()

class MRCFileMover:
    def __init__(self, source_dir, destination_dir, log_callback):
        self.source_dir = Path(source_dir)
        self.destination_dir = Path(destination_dir)
        self.processed_files = set()
        self.running = True
        self.log_callback = log_callback
        
        # Create directories if they don't exist
        self.destination_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler('mrc_mover.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def log_message(self, message):
        logging.info(message)
        if self.log_callback:
            self.log_callback(message)

    def is_file_ready(self, file_path):
        try:
            initial_size = file_path.stat().st_size
            time.sleep(1)
            final_size = file_path.stat().st_size
            return initial_size == final_size
        except Exception:
            return False

    def move_file(self, file_path):
        try:
            if not self.is_file_ready(file_path):
                self.log_message(f"File {file_path} is not ready for moving")
                return False

            dest_path = self.destination_dir / file_path.name
            shutil.move(str(file_path), str(dest_path))
            self.log_message(f"Successfully moved {file_path.name} to {dest_path}")
            return True
            
        except Exception as e:
            self.log_message(f"Error moving file {file_path}: {str(e)}")
            return False

    def scan_and_move(self):
        try:
            mrc_files = list(self.source_dir.glob("*.mrc"))
            
            if not mrc_files:
                return
                
            for file_path in mrc_files:
                if not self.running:
                    break
                if file_path.name not in self.processed_files:
                    if self.move_file(file_path):
                        self.processed_files.add(file_path.name)
                        
        except Exception as e:
            self.log_message(f"Error scanning directory: {str(e)}")

    def stop(self):
        self.running = False

    def run(self):
        self.log_message("Starting MRC file mover")
        self.log_message(f"Monitoring directory: {self.source_dir}")
        self.log_message(f"Moving files to: {self.destination_dir}")
        
        while self.running:
            self.scan_and_move()
            time.sleep(300)  # 5 minutes

def main():
    root = tk.Tk()
    app = MRCMoverGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 