import threading
import os
import time
import shutil
from backend.config import TEMP_PATH  # Import TEMP_PATH

def temp_remove(file_path, delay=8*3600):
    """
    Removes the temporary file after a specified delay if it still exists.

    Args:
        file_path (str): Path to the temporary file.
        delay (int): Time in seconds to wait before removing the file (default: 2*3600 seconds = 2 hours).
    """
    def remove_file():
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                raise RuntimeError(f"Error removing temporary file {file_path}: {e}")

    # Schedule the file removal
    timer = threading.Timer(delay, remove_file)
    timer.start()


def cleanup_whole_temp_folder():
    """
    Removes all files and directories in the temp directory.
    """
    if os.path.exists(TEMP_PATH):
        for filename in os.listdir(TEMP_PATH):
            file_path = os.path.join(TEMP_PATH, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.remove(file_path)  # Remove files or symbolic links
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove directories and their contents
            except Exception as e:
                raise RuntimeError(f"Error removing {file_path}: {e}")
            