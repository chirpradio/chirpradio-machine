import argparse
import sqlite3

from database import _modify_tag

def parse_arguments():
    """
    Parse command-line arguments for fingerprint, tag name, and new value.
    """
    parser = argparse.ArgumentParser(description="Modify tags in database.")
    parser.add_argument("fingerprint")
    parser.add_argument("id3_frame")
    parser.add_argument("new_value")

    return parser.parse_args()

def main():
    # Parse command-line arguments
    args = parse_arguments()
    conn = sqlite3.connect("file.db") #connect to some test file

    # Call _modify_tag from database.py
    _modify_tag(conn, args.fingerprint, args.id3_frame, args.new_value)

if __name__ == "__main__":
    main()

