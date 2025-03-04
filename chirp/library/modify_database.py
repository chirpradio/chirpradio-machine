import argparse
import sqlite3

from database import _modify_tag, Database

def parse_arguments():
    """
    Parse command-line arguments for fingerprint, tag name, and new value.
    """
    parser = argparse.ArgumentParser(description="Modify tags in database.")
    parser.add_argument("changes", nargs='+', help = "fingerprint, id3_frame, and"
                        "new_value, separated with space."
                        "Format: fingerprint id3_frame new_value")

    return parser.parse_args()

def main():
    # Parse command-line arguments
    args = parse_arguments()
    conn = sqlite3.connect("file.db") #connect to some test file

    for i in range(0, len(args.changes), 3):
        fingerprint = args.changes[i]
        id3_frame = args.changes[i+1]
        new_value = args.changes[i+2]
        Database db = Database("name.db") 
        # remember to modify the name here when needed, and include true/false 
        # for auto_migrate

        db._modify_tag(conn, fingerprint, id3_frame, new_value)

if __name__ == "__main__":
    main()

