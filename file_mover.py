import os
import shutil
import time
import logging
from datetime import datetime
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('file_mover.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class MRCFileMover:
    def __init__(self, source_dir, destination_dir):
        """Initialize the file mover with source and destination directories."""
        self.source_dir = Path(source_dir)
        self.destination_dir = Path(destination_dir)
        self.processed_files = set()
        
        # Create directories if they don't exist
        self.destination_dir.mkdir(parents=True, exist_ok=True)
        
    def is_file_ready(self, file_path):
        """Check if file is ready to be moved (not being written to)."""
        try:
            # Get initial size
            initial_size = file_path.stat().st_size
            # Wait a short time
            time.sleep(1)
            # Get size again
            final_size = file_path.stat().st_size
            # If sizes are the same, file is likely not being written to
            return initial_size == final_size
        except Exception:
            return False

    def move_file(self, file_path):
        """Move a single file to the destination directory."""
        try:
            if not self.is_file_ready(file_path):
                logging.warning(f"File {file_path} is not ready for moving")
                return False

            # Create destination path with same filename
            dest_path = self.destination_dir / file_path.name
            
            # Move the file
            shutil.move(str(file_path), str(dest_path))
            logging.info(f"Successfully moved {file_path.name} to {dest_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error moving file {file_path}: {str(e)}")
            return False

    def scan_and_move(self):
        """Scan source directory for .mrc files and move them."""
        try:
            # Get all .mrc files in source directory
            mrc_files = list(self.source_dir.glob("*.mrc"))
            
            if not mrc_files:
                logging.debug("No new .mrc files found")
                return
                
            for file_path in mrc_files:
                if file_path.name not in self.processed_files:
                    if self.move_file(file_path):
                        self.processed_files.add(file_path.name)
                        
        except Exception as e:
            logging.error(f"Error scanning directory: {str(e)}")

    def run(self, interval_minutes=5):
        """Run the file mover continuously."""
        logging.info(f"Starting MRC file mover")
        logging.info(f"Monitoring directory: {self.source_dir}")
        logging.info(f"Moving files to: {self.destination_dir}")
        
        while True:
            self.scan_and_move()
            time.sleep(interval_minutes * 60)

def main():
    # Get source and destination directories from command line arguments or use defaults
    if len(sys.argv) != 3:
        print("Usage: python file_mover.py <source_directory> <destination_directory>")
        print("Using default directories...")
        source_dir = "source_folder"
        destination_dir = "destination_folder"
    else:
        source_dir = sys.argv[1]
        destination_dir = sys.argv[2]

    # Create and run the file mover
    mover = MRCFileMover(source_dir, destination_dir)
    mover.run()

if __name__ == "__main__":
    main() 