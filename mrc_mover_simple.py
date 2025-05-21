import os
import shutil
import time
import logging
from datetime import datetime
import sys
from pathlib import Path
import json
import hashlib

# Set up logging with more details
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mrc_mover.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class MRCFileMover:
    def __init__(self, config_path='config.json'):
        """Initialize the file mover using settings from config file."""
        self.config_path = config_path
        logging.debug(f"Looking for config file at: {os.path.abspath(config_path)}")
        self.load_config()
        self.processed_files = set()
        
        # Create destination directory if it doesn't exist
        Path(self.dest_dir).mkdir(parents=True, exist_ok=True)
        
    def load_config(self):
        """Load configuration from config.json file."""
        try:
            logging.debug(f"Attempting to read config file...")
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.source_dir = config['source_directory']
                self.dest_dir = config['destination_directory']

            # Log the actual paths being used
            logging.debug(f"Full source path: {os.path.abspath(self.source_dir)}")
            logging.debug(f"Full destination path: {os.path.abspath(self.dest_dir)}")
            
            # Verify directories exist
            if not os.path.exists(self.source_dir):
                logging.error(f"Source directory does not exist: {self.source_dir}")
                sys.exit(1)
            if not os.path.exists(self.dest_dir):
                logging.error(f"Destination directory does not exist: {self.dest_dir}")
                sys.exit(1)

            logging.info(f"Successfully loaded configuration:")
            logging.info(f"Source directory: {self.source_dir}")
            logging.info(f"Destination directory: {self.dest_dir}")
                
        except FileNotFoundError:
            logging.error(f"Config file {self.config_path} not found!")
            self.create_default_config()
            sys.exit(1)
        except json.JSONDecodeError as e:
            logging.error(f"Error reading config file! Please check the format. Error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Unexpected error loading config: {str(e)}")
            sys.exit(1)
            
    def create_default_config(self):
        """Create a default config file if none exists."""
        default_config = {
            "source_directory": "C:/source_folder",
            "destination_directory": "D:/destination_folder"
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
            
        logging.info(f"Created default config file: {self.config_path}")
        logging.info("Please edit the config file with your desired paths and restart the program.")

    def calculate_file_hash(self, file_path):
        """Calculate MD5 hash of a file for verification."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def is_file_ready(self, file_path):
        """Check if file is ready to be moved (not being written to)."""
        try:
            initial_size = os.path.getsize(file_path)
            time.sleep(1)
            final_size = os.path.getsize(file_path)
            logging.debug(f"File {file_path} size check - Initial: {initial_size}, Final: {final_size}")
            return initial_size == final_size
        except Exception as e:
            logging.error(f"Error checking if file is ready: {str(e)}")
            return False

    def verify_copy(self, source_path, dest_path):
        """Verify that the file was copied correctly using MD5 hash."""
        try:
            source_hash = self.calculate_file_hash(source_path)
            dest_hash = self.calculate_file_hash(dest_path)
            logging.debug(f"File hash comparison - Source: {source_hash}, Destination: {dest_hash}")
            return source_hash == dest_hash
        except Exception as e:
            logging.error(f"Error verifying file copy: {str(e)}")
            return False

    def safe_copy_and_delete(self, source_path):
        """Safely copy file to destination and delete original after verification."""
        try:
            logging.debug(f"Attempting to process file: {source_path}")
            
            if not self.is_file_ready(source_path):
                logging.warning(f"File {source_path} is not ready for copying")
                return False

            filename = os.path.basename(source_path)
            dest_path = os.path.join(self.dest_dir, filename)
            
            logging.debug(f"Copying {filename} to {dest_path}")
            shutil.copy2(source_path, dest_path)
            logging.info(f"Copied {filename} to {self.dest_dir}")
            
            if self.verify_copy(source_path, dest_path):
                logging.debug(f"Verification successful, deleting source file: {source_path}")
                os.remove(source_path)
                logging.info(f"Verified copy successful and deleted source file: {filename}")
                return True
            else:
                logging.error(f"Copy verification failed for {filename}")
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                    logging.debug(f"Removed failed copy at destination: {dest_path}")
                return False
            
        except Exception as e:
            logging.error(f"Error processing file {source_path}: {str(e)}")
            return False

    def scan_and_process(self):
        """Scan source directory for .mrc files and process them."""
        try:
            logging.debug(f"Scanning directory: {self.source_dir}")
            mrc_files = [f for f in os.listdir(self.source_dir) 
                        if f.endswith('.mrc') and os.path.isfile(os.path.join(self.source_dir, f))]
            
            logging.debug(f"Found {len(mrc_files)} .mrc files")
            files_processed = 0
            
            for filename in mrc_files:
                file_path = os.path.join(self.source_dir, filename)
                logging.debug(f"Processing file: {filename}")
                if filename not in self.processed_files:
                    if self.safe_copy_and_delete(file_path):
                        self.processed_files.add(filename)
                        files_processed += 1
            
            return files_processed
                        
        except Exception as e:
            logging.error(f"Error scanning directory: {str(e)}")
            return 0

    def run(self):
        """Run the file mover once and exit after completion."""
        logging.info("Starting MRC file mover")
        files_processed = self.scan_and_process()
        
        if files_processed > 0:
            logging.info(f"Successfully processed {files_processed} files")
        else:
            logging.info("No new files to process")
        
        logging.info("File processing complete. Exiting...")

def main():
    mover = MRCFileMover()
    mover.run()

if __name__ == "__main__":
    main() 