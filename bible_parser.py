import os
import json
import re
import random # For selecting a random Psalm chapter

class BibleParser:
    def __init__(self, logger, bible_file_path_override=None):
        self.logger = logger
        self.bible_data = []
        self.book_map = {}
        self.divine_name_pattern = re.compile(r"\b(LORD|Lord)\b")
        self._load_bible_data(bible_file_path_override)

    def _load_bible_data(self, bible_file_path_override=None):
        """Loads Bible data from JSON file and populates book_map."""
        try:
            if bible_file_path_override:
                bible_file_path = bible_file_path_override
            else:
                # Default path relative to this file's location (or common project structure)
                current_dir = os.path.dirname(__file__)
                bible_file_path = os.path.join(current_dir, "data", "en_kjv.json")
                if not os.path.exists(bible_file_path):
                    # Fallback for common execution from project root if app/parser is in a subdirectory
                    bible_file_path_alt = os.path.join(os.getcwd(), "data", "en_kjv.json")
                    if os.path.exists(bible_file_path_alt):
                        bible_file_path = bible_file_path_alt
                    else:
                        raise FileNotFoundError(
                            f"Bible data file not found at {bible_file_path} or {bible_file_path_alt}"
                        )

            with open(bible_file_path, "r", encoding="utf-8") as f:
                self.bible_data = json.load(f)

            for i, book_data_item in enumerate(self.bible_data):
                self.book_map[book_data_item["name"].lower()] = i
                self.book_map[book_data_item["abbrev"].lower()] = i
                if book_data_item["name"].lower() == "psalms":
                    self.book_map["psalm"] = i
            
            if not self.bible_data or not self.book_map:
                self.logger.error("Bible data loaded but result is empty (BIBLE_DATA or BOOK_MAP).")
            else:
                self.logger.info("Bible data and book map loaded successfully.")

        except FileNotFoundError as e:
            self.logger.error(f"Bible data file (data/en_kjv.json) not found. {e}")
        except json.JSONDecodeError:
            self.logger.error("Error decoding Bible data JSON (data/en_kjv.json).")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred loading Bible data: {e}")

    def is_data_loaded(self):
        """Checks if Bible data was successfully loaded."""
        return bool(self.bible_data and self.book_map)

    def parse_reference(self, reference_str):
        """
        Parses a Bible reference string into its components.
        Handles "Book Chapter:Verse", "Book Chapter:Verse-Verse", "Book Chapter".
        """
        match = re.match(
            r"^(.*?)\s*(\d+)(?:\s*:\s*(\d+)(?:\s*-\s*(\d+))?)?$", reference_str.strip()
        )

        if not match:
            self.logger.info(f"Could not parse reference string: {reference_str}")
            return None

        book_name_str = match.group(1).strip()
        chapter_str = match.group(2)
        start_verse_str = match.group(3)
        end_verse_str = match.group(4)

        try:
            parsed_ref = {
                "book_name": book_name_str,
                "chapter": int(chapter_str),
                "start_verse": int(start_verse_str) if start_verse_str else None,
                "end_verse": (
                    int(end_verse_str)
                    if end_verse_str
                    else (int(start_verse_str) if start_verse_str else None)
                ),
            }
            return parsed_ref
        except ValueError:
            self.logger.error(f"ValueError parsing numbers in reference: {reference_str}")
            return None

    def get_passage(self, parsed_ref):
        """
        Retrieves and formats Bible passage text from the loaded JSON data.
        """
        if not self.is_data_loaded():
            self.logger.error("Attempted to get passage, but Bible data is not loaded.")
            return "Error: Bible data not loaded on the server."

        book_name_key = parsed_ref["book_name"].lower()
        book_index = self.book_map.get(book_name_key)

        if book_index is None:
            if book_name_key.endswith("s") and self.book_map.get(book_name_key[:-1]) is not None:
                book_index = self.book_map.get(book_name_key[:-1])
            elif (
                not book_name_key.endswith("s")
                and self.book_map.get(book_name_key + "s") is not None
            ):
                book_index = self.book_map.get(book_name_key + "s")

            if book_index is None:
                return f"Book '{parsed_ref['book_name']}' not found. Please check spelling or try a standard abbreviation (e.g., Gen, Exo, Psa, Mat, Rom)."

        book_data = self.bible_data[book_index]
        chapter_num = parsed_ref["chapter"]
        chapter_index = chapter_num - 1

        if not (0 <= chapter_index < len(book_data["chapters"])):
            return f"Chapter {chapter_num} not found in {book_data['name']} (max: {len(book_data['chapters'])})."

        chapter_verses_list = book_data["chapters"][chapter_index]
        start_verse = parsed_ref["start_verse"]
        end_verse = parsed_ref["end_verse"]
        passage_texts = []
        output_reference_display = f"{book_data['name']} {chapter_num}"

        if start_verse is None:  # Whole chapter
            for i, verse_text in enumerate(chapter_verses_list):
                cleaned_verse_text = re.sub(r"\{.*?\}", "", verse_text).strip()
                cleaned_verse_text_highlighted = self.divine_name_pattern.sub(
                    r'<span class="divine-name">\1</span>', cleaned_verse_text
                )
                passage_texts.append(f"{i+1} {cleaned_verse_text_highlighted}")
        else:
            start_verse_index = start_verse - 1
            end_verse_index = (
                (end_verse - 1) if end_verse is not None else start_verse_index
            )

            if not (0 <= start_verse_index < len(chapter_verses_list)):
                return f"Start verse {start_verse} not found in {book_data['name']} chapter {chapter_num} (max: {len(chapter_verses_list)})."
            if (
                not (0 <= end_verse_index < len(chapter_verses_list))
                or end_verse_index < start_verse_index
            ):
                return f"End verse {end_verse} is invalid for {book_data['name']} chapter {chapter_num}."

            for i in range(start_verse_index, end_verse_index + 1):
                verse_text = chapter_verses_list[i]
                cleaned_verse_text = re.sub(r"\{.*?\}", "", verse_text).strip()
                cleaned_verse_text_highlighted = self.divine_name_pattern.sub(
                    r'<span class="divine-name">\1</span>', cleaned_verse_text
                )
                passage_texts.append(f"{i+1} {cleaned_verse_text_highlighted}")

            if start_verse == end_verse:
                output_reference_display += f":{start_verse}"
            else:
                output_reference_display += f":{start_verse}-{end_verse}"

        if not passage_texts:
            return f"No verses found for '{parsed_ref['book_name']} {chapter_num}:{start_verse if start_verse else ''}{'-'+str(end_verse) if end_verse and end_verse != start_verse else ''}'."

        full_passage_text = "\n".join(passage_texts)
        return f"{output_reference_display}\n{full_passage_text}"

    def get_random_psalm_passage(self):
        """Retrieves the full text of a random Psalm."""
        if not self.is_data_loaded():
            self.logger.error("Cannot fetch random Psalm, Bible data not loaded.")
            return "Error: Bible data not available to fetch a random Psalm."

        psalms_book_key = "psalms"
        psalms_book_index = self.book_map.get(psalms_book_key)

        if psalms_book_index is None:
            self.logger.error(f"Book '{psalms_book_key}' not found in BOOK_MAP for random Psalm.")
            return "Error: Book of Psalms not found."

        psalms_book_data = self.bible_data[psalms_book_index]
        num_chapters_in_psalms = len(psalms_book_data["chapters"])

        if num_chapters_in_psalms == 0:
            self.logger.error("Book of Psalms has no chapters listed for random Psalm.")
            return "Error: No Psalms available."

        random_chapter_num = random.randint(1, num_chapters_in_psalms)

        parsed_ref = {
            "book_name": psalms_book_data["name"],
            "chapter": random_chapter_num,
            "start_verse": None,
            "end_verse": None,
        }

        passage_text = self.get_passage(parsed_ref)

        # Check if get_passage returned an error (it shouldn't with controlled input, but good practice)
        if (
            not passage_text
            or passage_text.startswith("Error:")
            or passage_text.startswith("Book '") # From get_passage error
            or passage_text.startswith("Chapter ") # From get_passage error
            or passage_text.startswith("No verses found") # From get_passage error
        ):
            self.logger.error(
                f"Failed to get passage for random Psalm: {psalms_book_data['name']} {random_chapter_num}. Internal error: {passage_text}"
            )
            return "Error: Could not retrieve the random Psalm text due to an internal issue."
        
        self.logger.info(
            f"Successfully retrieved random Psalm: {psalms_book_data['name']} {random_chapter_num}"
        )
        return passage_text
