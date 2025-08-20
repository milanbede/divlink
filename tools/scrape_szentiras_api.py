import os
import json
import re
import time
import random
import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

# Configuration for SZIT (Szent István Társulati) Bible from szentiras.eu API
API_BASE_URL = "https://szentiras.eu/api/idezet/"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "books_szit")

# Hungarian book names and abbreviations from szentiras.eu
HUNGARIAN_BOOKS = [
    # New Testament
    {"name": "Máté", "abbrev": "Mt", "filename_base": "Máté"},
    {"name": "Márk", "abbrev": "Mk", "filename_base": "Márk"},
    {"name": "Lukács", "abbrev": "Lk", "filename_base": "Lukács"},
    {"name": "János", "abbrev": "Jn", "filename_base": "János"},
    {
        "name": "Apostolok Cselekedetei",
        "abbrev": "ApCsel",
        "filename_base": "Apostolok Cselekedetei",
    },
    {"name": "Rómaiak", "abbrev": "Róm", "filename_base": "Rómaiak"},
    {"name": "1 Korintusi", "abbrev": "1Kor", "filename_base": "1 Korintusi"},
    {"name": "2 Korintusi", "abbrev": "2Kor", "filename_base": "2 Korintusi"},
    {"name": "Galatáknak", "abbrev": "Gal", "filename_base": "Galatáknak"},
    {"name": "Efezusiaknak", "abbrev": "Ef", "filename_base": "Efezusiaknak"},
    {"name": "Filippieknek", "abbrev": "Fil", "filename_base": "Filippieknek"},
    {"name": "Kolosszeieknek", "abbrev": "Kol", "filename_base": "Kolosszeieknek"},
    {"name": "1 Tesszaloniki", "abbrev": "1Tesz", "filename_base": "1 Tesszaloniki"},
    {"name": "2 Tesszaloniki", "abbrev": "2Tesz", "filename_base": "2 Tesszaloniki"},
    {"name": "1 Timóteus", "abbrev": "1Tim", "filename_base": "1 Timóteus"},
    {"name": "2 Timóteus", "abbrev": "2Tim", "filename_base": "2 Timóteus"},
    {"name": "Titusznak", "abbrev": "Tit", "filename_base": "Titusznak"},
    {"name": "Filemonnak", "abbrev": "Filem", "filename_base": "Filemonnak"},
    {"name": "Zsidóknak", "abbrev": "Zsid", "filename_base": "Zsidóknak"},
    {"name": "Jakab", "abbrev": "Jak", "filename_base": "Jakab"},
    {"name": "1 Péter", "abbrev": "1Pt", "filename_base": "1 Péter"},
    {"name": "2 Péter", "abbrev": "2Pt", "filename_base": "2 Péter"},
    {"name": "1 János", "abbrev": "1Jn", "filename_base": "1 János"},
    {"name": "2 János", "abbrev": "2Jn", "filename_base": "2 János"},
    {"name": "3 János", "abbrev": "3Jn", "filename_base": "3 János"},
    {"name": "Júdás", "abbrev": "Júd", "filename_base": "Júdás"},
    {"name": "Jelenések", "abbrev": "Jel", "filename_base": "Jelenések"},
    # Old Testament
    {"name": "Teremtés", "abbrev": "Ter", "filename_base": "Teremtés"},
    {"name": "Kivonulás", "abbrev": "Kiv", "filename_base": "Kivonulás"},
    {"name": "Leviták", "abbrev": "Lev", "filename_base": "Leviták"},
    {"name": "Számok", "abbrev": "Szám", "filename_base": "Számok"},
    {
        "name": "Második Törvénykönyv",
        "abbrev": "MTörv",
        "filename_base": "Második Törvénykönyv",
    },
    {"name": "Józsué", "abbrev": "Józs", "filename_base": "Józsué"},
    {"name": "Bírák", "abbrev": "Bír", "filename_base": "Bírák"},
    {"name": "Ruth", "abbrev": "Rut", "filename_base": "Ruth"},
    {"name": "1 Sámuel", "abbrev": "1Sám", "filename_base": "1 Sámuel"},
    {"name": "2 Sámuel", "abbrev": "2Sám", "filename_base": "2 Sámuel"},
    {"name": "1 Királyok", "abbrev": "1Kir", "filename_base": "1 Királyok"},
    {"name": "2 Királyok", "abbrev": "2Kir", "filename_base": "2 Királyok"},
    {"name": "1 Krónika", "abbrev": "1Krón", "filename_base": "1 Krónika"},
    {"name": "2 Krónika", "abbrev": "2Krón", "filename_base": "2 Krónika"},
    {"name": "Ezdrás", "abbrev": "Ezd", "filename_base": "Ezdrás"},
    {"name": "Nehemiás", "abbrev": "Neh", "filename_base": "Nehemiás"},
    # Deuterocanonical Books
    {"name": "Tóbit", "abbrev": "Tób", "filename_base": "Tóbit"},
    {"name": "Judit", "abbrev": "Jud", "filename_base": "Judit"},
    {"name": "Eszter", "abbrev": "Esz", "filename_base": "Eszter"},
    {"name": "Jób", "abbrev": "Jób", "filename_base": "Jób"},
    {"name": "Zsoltárok", "abbrev": "Zsolt", "filename_base": "Zsoltárok"},
    {"name": "Példabeszédek", "abbrev": "Péld", "filename_base": "Példabeszédek"},
    {"name": "Prédikátor", "abbrev": "Préd", "filename_base": "Prédikátor"},
    {"name": "Énekek Éneke", "abbrev": "Én", "filename_base": "Énekek Éneke"},
    # More Deuterocanonical Books
    {
        "name": "Bölcsesség könyve",
        "abbrev": "Bölcs",
        "filename_base": "Bölcsesség könyve",
    },
    {"name": "Sirach", "abbrev": "Sir", "filename_base": "Sirach"},
    {"name": "Izajás", "abbrev": "Iz", "filename_base": "Izajás"},
    {"name": "Jeremiás", "abbrev": "Jer", "filename_base": "Jeremiás"},
    {
        "name": "Jeremiás siralmai",
        "abbrev": "Siral",
        "filename_base": "Jeremiás siralmai",
    },
    # More Deuterocanonical Books
    {"name": "Báruk", "abbrev": "Bár", "filename_base": "Báruk"},
    {"name": "Ezekiel", "abbrev": "Ez", "filename_base": "Ezekiel"},
    {"name": "Dániel", "abbrev": "Dán", "filename_base": "Dániel"},
    {"name": "Hóseás", "abbrev": "Oz", "filename_base": "Hóseás"},
    {"name": "Jóel", "abbrev": "Jo", "filename_base": "Jóel"},
    {"name": "Ámós", "abbrev": "Ám", "filename_base": "Ámós"},
    {"name": "Abdiás", "abbrev": "Abd", "filename_base": "Abdiás"},
    {"name": "Jónás", "abbrev": "Jón", "filename_base": "Jónás"},
    {"name": "Mikeás", "abbrev": "Mik", "filename_base": "Mikeás"},
    {"name": "Náhum", "abbrev": "Náh", "filename_base": "Náhum"},
    {"name": "Habakuk", "abbrev": "Hab", "filename_base": "Habakuk"},
    {"name": "Szofoniás", "abbrev": "Szof", "filename_base": "Szofoniás"},
    {"name": "Aggeus", "abbrev": "Ag", "filename_base": "Aggeus"},
    {"name": "Zakariás", "abbrev": "Zak", "filename_base": "Zakariás"},
    {"name": "Malakiás", "abbrev": "Mal", "filename_base": "Malakiás"},
    # Final Deuterocanonical Books
    {"name": "1 Makkabeusok", "abbrev": "1Mak", "filename_base": "1 Makkabeusok"},
    {"name": "2 Makkabeusok", "abbrev": "2Mak", "filename_base": "2 Makkabeusok"},
]


def get_existing_book_names(output_dir):
    """Returns a set of canonical book names from existing .json files in output_dir."""
    existing_books = set()
    if not os.path.isdir(output_dir):
        print(f"Warning: Output directory {output_dir} does not exist. Will create it.")
        return existing_books
    for filename in os.listdir(output_dir):
        if filename.endswith(".json"):
            book_name = filename[:-5]  # Remove .json
            existing_books.add(book_name)
    return existing_books


def fetch_book_from_api(book_abbrev, max_retries=5, base_delay=1.0):
    """
    Fetches an entire book from the szentiras.eu API with exponential backoff retry.
    Returns chapters organized as a list of lists (chapters -> verses).
    """
    api_url = f"{API_BASE_URL}{book_abbrev}"
    print(f"Fetching {book_abbrev} from API: {api_url}")

    for attempt in range(max_retries):
        try:
            response = requests.get(api_url)

            if response.status_code == 429:  # Too Many Requests
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    delay = base_delay * (2**attempt) + random.uniform(0, 1)
                    print(
                        f"Rate limited (429). Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    continue
                else:
                    print(f"Failed after {max_retries} attempts due to rate limiting")
                    return None

            response.raise_for_status()

            # Add delay between successful requests
            time.sleep(0.5 + random.uniform(0, 0.3))  # 0.5-0.8s delay with jitter

            data = response.json()
            break

        except requests.RequestException as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2**attempt) + random.uniform(0, 1)
                print(
                    f"Request failed: {e}. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
                continue
            else:
                print(
                    f"Error fetching {book_abbrev} from API after {max_retries} attempts: {e}"
                )
                return None

    if "valasz" not in data or "versek" not in data["valasz"]:
        print(f"Invalid API response structure for {book_abbrev}")
        return None

    verses_data = data["valasz"]["versek"]
    if not verses_data:
        print(f"No verses found in API response for {book_abbrev}")
        return None

    print(f"Received {len(verses_data)} verses from API")

    # Organize verses by chapter
    chapters = {}

    for verse_data in verses_data:
        # Extract verse text and clean HTML
        verse_text = verse_data.get("szoveg", "").strip()
        if not verse_text:
            continue

        # Remove HTML tags but preserve the structure for cleaning
        soup = BeautifulSoup(verse_text, "html.parser")

        # Remove title and header tags that contain book/section titles
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            tag.decompose()  # Completely remove these tags and their content

        # Get clean text without HTML
        verse_text = soup.get_text()
        verse_text = re.sub(r"\s+", " ", verse_text).strip()

        # Extract chapter and verse numbers from location
        location = verse_data.get("hely", {})
        machine_ref = location.get("gepi", "")  # e.g., "1CO_1_1"

        if not machine_ref:
            continue

        # Parse chapter number from machine reference
        # Format is typically: BOOK_CHAPTER_VERSE (e.g., "1CO_1_1")
        parts = machine_ref.split("_")
        if len(parts) >= 2:
            try:
                chapter_num = int(parts[1])

                if chapter_num not in chapters:
                    chapters[chapter_num] = []

                chapters[chapter_num].append(verse_text)

            except ValueError:
                print(f"Could not parse chapter number from {machine_ref}")
                continue

    # Convert to ordered list of chapters
    if not chapters:
        print(f"No chapters parsed for {book_abbrev}")
        return None

    max_chapter = max(chapters.keys())
    ordered_chapters = []

    for chapter_num in range(1, max_chapter + 1):
        if chapter_num in chapters:
            ordered_chapters.append(chapters[chapter_num])
        else:
            print(f"Warning: Missing chapter {chapter_num} in {book_abbrev}")

    print(f"Successfully parsed {len(ordered_chapters)} chapters for {book_abbrev}")
    return ordered_chapters


def main():
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")

    existing_book_filenames = get_existing_book_names(OUTPUT_DIR)
    print(
        f"Found {len(existing_book_filenames)} existing books: {sorted(list(existing_book_filenames))}"
    )

    missing_books_to_scrape = []
    for book_info in HUNGARIAN_BOOKS:
        if book_info["filename_base"] not in existing_book_filenames:
            missing_books_to_scrape.append(book_info)

    if not missing_books_to_scrape:
        print("No missing books found. All books seem to exist in output directory.")
        return

    print(
        f"Found {len(missing_books_to_scrape)} missing books to scrape: {[b['name'] for b in missing_books_to_scrape]}"
    )

    for book_info in missing_books_to_scrape:
        print(
            f"\nStarting scrape for book: {book_info['name']} (Abbrev: {book_info['abbrev']})"
        )

        book_chapters_data = fetch_book_from_api(book_info["abbrev"])

        if book_chapters_data is None or not book_chapters_data:
            print(
                f"Failed to fetch content for {book_info['name']} from API. Skipping file creation."
            )
            continue

        # Prepare JSON data structure
        output_json_data = {
            "name": book_info["name"],
            "abbrev": book_info["abbrev"],
            "chapters": book_chapters_data,
        }

        # Filename based on 'filename_base'
        output_filename = f"{book_info['filename_base']}.json"
        output_filepath = os.path.join(OUTPUT_DIR, output_filename)

        try:
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(output_json_data, f, ensure_ascii=False, indent=2)
            print(f"Successfully saved {book_info['name']} to {output_filepath}")
        except IOError as e:
            print(f"Error writing JSON file {output_filepath}: {e}")
        except Exception as e:
            print(
                f"An unexpected error occurred while writing JSON for {book_info['name']}: {e}"
            )

    print("\nAPI scraping process completed.")


if __name__ == "__main__":
    main()
