import os
import shutil
import time
import sys
from datetime import datetime
from pathlib import Path
import json
import hashlib
import logging

class MRCFileMover:
    def __init__(self, config_path='config.json'):
        """Initialize the file mover using settings from config file."""
        self.config_path = config_path
        self.load_config()
        self.processed_files = set()
        self.setup_logging()
        
        # Create destination directory if it doesn't exist
        Path(self.dest_dir).mkdir(parents=True, exist_ok=True)
        
    def setup_logging(self):
        """Set up logging to file with rotation."""
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Set up logging configuration
        log_filename = log_dir / "mrc_transfer.log"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, mode='a'),
                logging.StreamHandler(sys.stdout)  # Also print to console
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def load_config(self):
        """Load configuration from config.json file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.source_dir = config['source_directory']
                self.dest_dir = config['destination_directory']
            
            # Verify directories exist
            if not os.path.exists(self.source_dir):
                print(f"Source directory does not exist: {self.source_dir}")
                sys.exit(1)
            if not os.path.exists(self.dest_dir):
                print(f"Destination directory does not exist: {self.dest_dir}")
                sys.exit(1)
                
        except FileNotFoundError:
            self.create_default_config()
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error reading config file! Please check the format.")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error loading config")
            sys.exit(1)
            
    def create_default_config(self):
        """Create a default config file if none exists."""
        default_config = {
            "source_directory": "C:/source_folder",
            "destination_directory": "D:/destination_folder"
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
            
        print(f"Created default config file: {self.config_path}")
        print("Please edit the config file with your desired paths and restart the program.")

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
            return initial_size == final_size
        except Exception:
            return False

    def verify_copy(self, source_path, dest_path):
        """Verify that the file was copied correctly using MD5 hash."""
        try:
            source_hash = self.calculate_file_hash(source_path)
            dest_hash = self.calculate_file_hash(dest_path)
            return source_hash == dest_hash
        except Exception:
            return False

    def get_file_size_mb(self, file_path):
        """Get file size in megabytes."""
        try:
            size_bytes = os.path.getsize(file_path)
            return round(size_bytes / (1024 * 1024), 2)
        except Exception:
            return 0

    def safe_copy_and_delete(self, source_path):
        """Safely copy file to destination and delete original after verification."""
        try:
            if not self.is_file_ready(source_path):
                return False

            filename = os.path.basename(source_path)
            dest_path = os.path.join(self.dest_dir, filename)
            file_size_mb = self.get_file_size_mb(source_path)
            
            # Copy the file
            start_time = time.time()
            shutil.copy2(source_path, dest_path)
            copy_time = round(time.time() - start_time, 2)
            
            # Verify the copy
            if self.verify_copy(source_path, dest_path):
                # Delete original file
                os.remove(source_path)
                
                # Log successful transfer - this is the only thing we log as per requirement
                self.logger.info(f"SUCCESS: {filename} ({file_size_mb}MB) - Copied, verified, and deleted in {copy_time}s - TRUE")
                return True
            else:
                # Clean up failed copy
                if os.path.exists(dest_path):
                    os.remove(dest_path)
                return False
            
        except Exception as e:
            return False

    def scan_and_process(self):
        """Scan source directory for .mrc files and process them."""
        try:
            mrc_files = [f for f in os.listdir(self.source_dir) 
                        if f.endswith('.mrc') and os.path.isfile(os.path.join(self.source_dir, f))]
            
            files_processed = 0
            
            for filename in mrc_files:
                file_path = os.path.join(self.source_dir, filename)
                if filename not in self.processed_files:
                    if self.safe_copy_and_delete(file_path):
                        self.processed_files.add(filename)
                        files_processed += 1
            
            return files_processed
                        
        except Exception:
            return 0

    def run(self):
        """Run the file mover once and exit after completion."""
        self.logger.info("Starting MRC file mover")
        files_processed = self.scan_and_process()
        
        if files_processed > 0:
            self.logger.info(f"Successfully processed {files_processed} files")
        else:
            print("No new files to process")  # Don't log this to reduce space
        
        self.logger.info("File processing complete. Exiting...")

def main():
    mover = MRCFileMover()
    mover.run()

if __name__ == "__main__":
    main()