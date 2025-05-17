import os
import json
import re
import time
import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

# Configuration
BASE_URL = "https://ebible.org/eng-kjv/"
# OUTPUT_DIR should be data/books relative to project root.
# __file__ is tools/scrape.py, so ../data/books
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "books")

# HTML content of the index page (provided by user)
# (Content of https://ebible.org/eng-kjv/index.htm)
INDEX_PAGE_HTML = """
# [King James Version + Apocrypha](https://eBible.org/)

- [Preface](FRT01.htm)
- [Genesis](GEN01.htm)
- [Exodus](EXO01.htm)
- [Leviticus](LEV01.htm)
- [Numbers](NUM01.htm)
- [Deuteronomy](DEU01.htm)
- [Joshua](JOS01.htm)
- [Judges](JDG01.htm)
- [Ruth](RUT01.htm)
- [1 Samuel](1SA01.htm)
- [2 Samuel](2SA01.htm)
- [1 Kings](1KI01.htm)
- [2 Kings](2KI01.htm)
- [1 Chronicles](1CH01.htm)
- [2 Chronicles](2CH01.htm)
- [Ezra](EZR01.htm)
- [Nehemiah](NEH01.htm)
- [Esther](EST01.htm)
- [Job](JOB01.htm)
- [Psalms](PSA001.htm)
- [Proverbs](PRO01.htm)
- [Ecclesiastes](ECC01.htm)
- [Song of Solomon](SNG01.htm)
- [Isaiah](ISA01.htm)
- [Jeremiah](JER01.htm)
- [Lamentations](LAM01.htm)
- [Ezekiel](EZK01.htm)
- [Daniel](DAN01.htm)
- [Hosea](HOS01.htm)
- [Joel](JOL01.htm)
- [Amos](AMO01.htm)
- [Obadiah](OBA01.htm)
- [Jonah](JON01.htm)
- [Micah](MIC01.htm)
- [Nahum](NAM01.htm)
- [Habakkuk](HAB01.htm)
- [Zephaniah](ZEP01.htm)
- [Haggai](HAG01.htm)
- [Zechariah](ZEC01.htm)
- [Malachi](MAL01.htm)
- [Tobit](TOB01.htm)
- [Judith](JDT01.htm)
- [Esther (Greek)](ESG10.htm)
- [Wisdom of Solomon](WIS01.htm)
- [Sirach](SIR01.htm)
- [Baruch](BAR01.htm)
- [3 Holy Children\'s Song](S3Y01.htm)
- [Susanna](SUS01.htm)
- [Bel and the Dragon](BEL01.htm)
- [1 Maccabees](1MA01.htm)
- [2 Maccabees](2MA01.htm)
- [1 Esdras](1ES01.htm)
- [Prayer of Manasses](MAN01.htm)
- [2 Esdras](2ES01.htm)
- [Matthew](MAT01.htm)
- [Mark](MRK01.htm)
- [Luke](LUK01.htm)
- [John](JHN01.htm)
- [Acts](ACT01.htm)
- [Romans](ROM01.htm)
- [1 Corinthians](1CO01.htm)
- [2 Corinthians](2CO01.htm)
- [Galatians](GAL01.htm)
- [Ephesians](EPH01.htm)
- [Philippians](PHP01.htm)
- [Colossians](COL01.htm)
- [1 Thessalonians](1TH01.htm)
- [2 Thessalonians](2TH01.htm)
- [1 Timothy](1TI01.htm)
- [2 Timothy](2TI01.htm)
- [Titus](TIT01.htm)
- [Philemon](PHM01.htm)
- [Hebrews](HEB01.htm)
- [James](JAS01.htm)
- [1 Peter](1PE01.htm)
- [2 Peter](2PE01.htm)
- [1 John](1JN01.htm)
- [2 John](2JN01.htm)
- [3 John](3JN01.htm)
- [Jude](JUD01.htm)
- [Revelation](REV01.htm)
- [Public Domain](copyright.htm)

[Go!](GEN01.htm)

epub3: [eng-kjv.epub](https://eBible.org/epub/eng-kjv.epub)

[PDF](https://eBible.org/pdf/eng-kjv/)

[Browser
Bible](https://ebible.org/study/?w1=bible&t1=local%3Aeng-kjv&v1=GN1_1)

[Crosswire Sword module](https://ebible.org/sword/zip/engKJV1769eb.zip)

[Read the Holy Bible now.](JHN01.htm)\
\
You may also download the KJV in zipped archives:

[HTML](https://eBible.org/Scriptures/eng-kjv_html.zip)

[plain ASCII text](https://eBible.org/Scriptures/eng-kjv_vpl.zip)

[More download and reading
options\...](https://eBible.org/find/show.php?id=eng-kjv)

For a more modern freely downloadable translation of the Holy Bible, try
the [World English Bible](https://eBible.org/web/). [Help keep free
Bibles online! Support the missionary who runs this
site.](http://mljohnson.org/partners/)

 \
\

HTML generated with [Haiola](https://haiola.org) by
[eBible.org](https://eBible.org) 15 May 2025 from source files dated 15
May 2025\
\
[](https://eBible.org/certified/)
"""


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


def parse_index_page(html_content):
    """
    Parses the main index page text content (expected in markdown-like list format)
    to get a list of all available books, their display names, abbreviations (derived from URL),
    and first chapter URLs.
    Filters out non-book entries like 'Preface' or 'Public Domain'.
    """
    books_info = []
    # Regex to capture book name and href from lines like: "- [Genesis](GEN01.htm)"
    # It also handles potential leading/trailing whitespace around the line or components.
    line_pattern = re.compile(r"^\s*-\s*\[\s*([^\]]+?)\s*\]\s*\(\s*([^)]+?)\s*\)\s*$")

    for line in html_content.strip().split("\n"):
        line_match = line_pattern.match(line.strip())
        if line_match:
            book_name_text = line_match.group(1).strip()
            href = line_match.group(2).strip()

            # Filter by typical book URL pattern: CODE + chapter_number + .htm
            # e.g., GEN01.htm, PSA001.htm, 1SA01.htm, S3Y01.htm
            # This regex also ensures the href is for a .htm file.
            url_match = re.match(
                r"^([A-Z0-9]{2,5})(\d{2,3})\.htm$", href, re.IGNORECASE
            )
            if url_match:
                abbrev_candidate = url_match.group(1).upper()

                if book_name_text in ["Preface", "Public Domain"]:
                    print(f"Skipping non-book entry: {book_name_text}")
                    continue

                # Apostrophes in book names like "3 Holy Children's Song" are handled fine by most
                # OS for filenames, so no replacement is strictly needed for 'filename_base'.
                # If issues arise, book_name_text.replace("'", "") could be used for filename_base.
                books_info.append(
                    {
                        "name": book_name_text,
                        "abbrev": abbrev_candidate,
                        "first_chapter_path": href,
                        "filename_base": book_name_text,  # Used for the .json filename
                    }
                )
            # else:
            #     # This condition means the extracted href didn't match the expected book chapter URL pattern.
            #     # Original code had a commented-out print here. Keeping it silent unless debugging is needed.
            #     # print(f"Skipping link: {book_name_text} ({href}) - does not match expected book URL pattern.")

    return books_info


def scrape_chapter_page(chapter_url):
    """
    Fetches and parses a single book chapter page from ebible.org.
    Returns a list of verse texts and the relative path to the next chapter page (if any).
    """
    print(f"Fetching {chapter_url}...")
    try:
        response = requests.get(chapter_url)
        response.raise_for_status()
        time.sleep(0.25)  # Be polite
    except requests.RequestException as e:
        print(f"Error fetching {chapter_url}: {e}")
        return None, None

    soup = BeautifulSoup(response.content, "html.parser")
    verses = []

    main_content = soup.find("div", class_="main")
    if not main_content:
        # Fallback for pages that might use a different main content wrapper
        main_content = soup.find("article", class_="main")
    if not main_content:
        # Try to find any div that might look like the main content area
        # This is a guess if the primary 'div.main' is not found
        possible_main_divs = soup.find_all("div")
        for div in possible_main_divs:
            if div.find(
                "span", class_="verse"
            ):  # Heuristic: if it contains verse markers
                main_content = div
                break
    if not main_content:
        print(f"Could not find main content block in {chapter_url}")
        return [], None  # Return empty list for verses, no next chapter

    # Verse extraction logic for ebible.org:
    # Verses are marked by <span class="verse" id="vX"><sup>X</sup></span>
    # The text of the verse follows this span.
    verse_elements = main_content.find_all("span", class_="verse")
    if verse_elements:
        for verse_span in verse_elements:
            verse_parts = []
            current_node = verse_span.next_sibling
            while current_node:
                # Stop if we hit the next verse marker or a clear structural break
                if (
                    current_node.name == "span"
                    and "verse" in current_node.get("class", [])
                ) or (
                    current_node.name == "div"
                    and "footnotes" in current_node.get("class", [])
                ):  # Stop before footnotes div
                    break

                if hasattr(current_node, "get_text"):
                    # Get text, preserving some whitespace for joining, but strip leading/trailing on the whole part
                    verse_parts.append(current_node.get_text(separator=" ", strip=True))
                elif isinstance(current_node, str):  # NavigableString
                    verse_parts.append(str(current_node).strip())

                current_node = current_node.next_sibling

            full_verse_text = " ".join(filter(None, verse_parts)).strip()
            # Cleanups:
            full_verse_text = re.sub(
                r"\s+", " ", full_verse_text
            )  # Normalize whitespace
            full_verse_text = re.sub(
                r"\{\d+:\d+\}", "", full_verse_text
            ).strip()  # Remove {1:1} style markers
            full_verse_text = re.sub(
                r"\[[a-zA-Z0-9]+\]", "", full_verse_text
            ).strip()  # Remove [a], [b] footnote markers

            if full_verse_text:
                verses.append(full_verse_text)
    else:
        print(
            f"Warning: No <span class='verse'> elements found in {chapter_url}. Verse extraction might fail or be incomplete."
        )
        # As a very basic fallback, try to get text from <p> tags if no verse spans were found.
        # This is unlikely to be accurate for ebible.org but included for robustness.
        for p_tag in main_content.find_all("p"):
            text = p_tag.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                # This will not be verse-separated, just paragraph text.
                # Better to return empty if primary method fails for this site.
                pass  # Not adding this crude fallback for ebible.org as it would be misleading.

    # Find next chapter link
    next_chapter_path = None

    # Attempt 1: Find by rel="next"
    next_link_tag = soup.find("a", rel="next")

    # Attempt 2: If not found by rel="next", try finding by common link texts ('>' or '►')
    if not next_link_tag:
        possible_next_texts = [">", "►"]  # Common symbols for "next"
        all_a_tags = soup.find_all("a", href=True)
        for link_tag_candidate in all_a_tags:
            link_text = link_tag_candidate.get_text(strip=True)
            if link_text in possible_next_texts:
                href_value = link_tag_candidate["href"]
                # Ensure it's a relative .htm path and matches chapter pattern (e.g., XYZ01.htm)
                if (
                    href_value.endswith(".htm")
                    and not href_value.startswith(("http://", "https://", "#"))
                    and re.match(
                        r"^[A-Z0-9]{2,5}\d{2,3}\.htm$", href_value, re.IGNORECASE
                    )
                ):
                    next_link_tag = link_tag_candidate
                    break  # Found a plausible candidate, use the first one that matches

    # Process the found link (if any) by validating its href
    if next_link_tag and next_link_tag.has_attr("href"):
        href_path = next_link_tag["href"]
        # Final validation of the href_path from the chosen link tag
        if (
            href_path.endswith(".htm")
            and not href_path.startswith(("http://", "https://", "#"))
            and re.match(r"^[A-Z0-9]{2,5}\d{2,3}\.htm$", href_path, re.IGNORECASE)
        ):
            next_chapter_path = href_path
        # else:
        # This implies that the link found (either by rel="next" or by text)
        # didn't pass the final validation for its href.
        # print(f"Candidate next link href '{href_path}' from {chapter_url} did not meet criteria.")

    if not verses:
        print(
            f"Warning: No verses extracted for {chapter_url}. Check parsing logic and page structure if this is unexpected."
        )

    return verses, next_chapter_path


def scrape_entire_book(book_info):
    """
    Scrapes all chapters for a given book by following 'next chapter' links.
    Returns a list of chapters, where each chapter is a list of verse texts.
    """
    all_chapters_content = []
    current_relative_path = book_info["first_chapter_path"]

    # Safety: Keep track of visited paths to prevent infinite loops from bad navigation links
    visited_paths = set()

    # Extract the book code/prefix from the first chapter path (e.g., "GEN" from "GEN01.htm")
    # This helps ensure we stay within the same book when following "next" links.
    book_code_match = re.match(
        r"^([A-Z0-9]{2,5})\d{2,3}\.htm$", book_info["first_chapter_path"], re.IGNORECASE
    )
    if not book_code_match:
        print(
            f"Error: Could not determine book code for {book_info['name']} from path {book_info['first_chapter_path']}. Cannot scrape."
        )
        return None
    expected_book_prefix = book_code_match.group(1).upper()

    while current_relative_path:
        if current_relative_path in visited_paths:
            print(
                f"Warning: Path {current_relative_path} already visited for book {book_info['name']}. Stopping to prevent loop."
            )
            break
        visited_paths.add(current_relative_path)

        # Validate that the current path still belongs to the expected book
        current_path_match = re.match(
            r"^([A-Z0-9]{2,5})\d{2,3}\.htm$", current_relative_path, re.IGNORECASE
        )
        if (
            not current_path_match
            or current_path_match.group(1).upper() != expected_book_prefix
        ):
            # print(f"Path {current_relative_path} does not seem to belong to book {book_info['name']} (expected prefix {expected_book_prefix}). Stopping.")
            break

        chapter_url = BASE_URL + current_relative_path
        verses, next_relative_path_candidate = scrape_chapter_page(chapter_url)

        if (
            verses is None
        ):  # Indicates a critical error during fetching/parsing of this chapter
            print(
                f"Failed to scrape chapter at {chapter_url} for book {book_info['name']}. Aborting this book."
            )
            return None  # Signal failure for the entire book

        if verses:  # Only add chapter if it contains verses
            all_chapters_content.append(verses)
        else:
            # If a page yields no verses, it might be an interstitial, error, or end of content.
            # Log it, but don't necessarily stop unless it's a persistent issue.
            print(
                f"Warning: Chapter at {chapter_url} for book {book_info['name']} yielded no verses."
            )

        current_relative_path = next_relative_path_candidate  # Move to the next chapter

    return all_chapters_content


def main():
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")

    existing_book_filenames = get_existing_book_names(OUTPUT_DIR)
    print(
        f"Found {len(existing_book_filenames)} existing books: {sorted(list(existing_book_filenames))}"
    )

    website_books_meta = parse_index_page(INDEX_PAGE_HTML)
    if not website_books_meta:
        print("No book information parsed from the website's index page. Exiting.")
        return

    print(f"Found {len(website_books_meta)} potential books listed on the website.")

    missing_books_to_scrape = []
    for book_meta in website_books_meta:
        # Compare using book_meta['filename_base'] (derived from link text)
        if book_meta["filename_base"] not in existing_book_filenames:
            missing_books_to_scrape.append(book_meta)

    if not missing_books_to_scrape:
        print(
            "No missing books found. All books from website index seem to exist in output directory."
        )
        return

    print(
        f"Found {len(missing_books_to_scrape)} missing books to scrape: {[b['name'] for b in missing_books_to_scrape]}"
    )

    for book_meta_to_scrape in missing_books_to_scrape:
        print(
            f"\nStarting scrape for book: {book_meta_to_scrape['name']} (Abbrev: {book_meta_to_scrape['abbrev']}, First chapter: {book_meta_to_scrape['first_chapter_path']})"
        )

        book_chapters_data = scrape_entire_book(book_meta_to_scrape)

        if (
            book_chapters_data is None or not book_chapters_data
        ):  # Check if scrape_entire_book failed or returned no data
            print(
                f"Failed to scrape any content for {book_meta_to_scrape['name']}, or book was empty. Skipping file creation."
            )
            continue

        # Prepare JSON data structure
        output_json_data = {
            "name": book_meta_to_scrape["name"],  # Full name, e.g., "Song of Solomon"
            "abbrev": book_meta_to_scrape[
                "abbrev"
            ],  # Derived abbreviation, e.g., "SNG"
            "chapters": book_chapters_data,
        }

        # Filename based on 'filename_base' (e.g., "Song of Solomon.json")
        output_filename = f"{book_meta_to_scrape['filename_base']}.json"
        output_filepath = os.path.join(OUTPUT_DIR, output_filename)

        try:
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(output_json_data, f, ensure_ascii=False, indent=2)
            print(
                f"Successfully saved {book_meta_to_scrape['name']} to {output_filepath}"
            )
        except IOError as e:
            print(f"Error writing JSON file {output_filepath}: {e}")
        except Exception as e:  # Catch any other unexpected errors during JSON writing
            print(
                f"An unexpected error occurred while writing JSON for {book_meta_to_scrape['name']}: {e}"
            )

    print("\nScraping process completed.")


if __name__ == "__main__":
    main()
