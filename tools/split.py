import json
import os

SOURCE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "en_kjv.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "books")

def split_bible_into_books():
    """
    Reads the main Bible JSON file and splits it into individual JSON files per book.
    Each file will be named after the book (e.g., Genesis.json) and stored in OUTPUT_DIR.
    """
    try:
        with open(SOURCE_FILE, "r", encoding="utf-8") as f:
            bible_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Source file not found at {SOURCE_FILE}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {SOURCE_FILE}")
        return

    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR)
            print(f"Created directory: {OUTPUT_DIR}")
        except OSError as e:
            print(f"Error: Could not create directory {OUTPUT_DIR}. {e}")
            return

    for book_data in bible_data:
        book_name = book_data.get("name")
        if not book_name:
            print("Warning: Found a book entry without a 'name' field. Skipping.")
            continue

        # Sanitize book name for use as a filename if necessary, though typically not an issue.
        # For simplicity, we'll use it directly. Consider more robust sanitization if names are complex.
        file_name = f"{book_name}.json"
        output_file_path = os.path.join(OUTPUT_DIR, file_name)

        try:
            with open(output_file_path, "w", encoding="utf-8") as f_out:
                json.dump(book_data, f_out, indent=4)
            print(f"Successfully wrote: {output_file_path}")
        except IOError as e:
            print(f"Error writing file {output_file_path}. {e}")
        except Exception as e:
            print(f"An unexpected error occurred while writing {output_file_path}: {e}")

if __name__ == "__main__":
    split_bible_into_books()
