import os
import json
import re
import random  # For selecting a random Psalm chapter


class BibleParser:
    def __init__(self, logger, books_dir_override=None):
        self.logger = logger
        self.book_map = {}  # Maps book names/abbreviations to canonical book filenames (e.g., "Genesis")
        self.books_dir_path = None  # Path to the directory containing individual book JSON files (e.g., "data/books")
        self.divine_name_pattern = re.compile(r"\b(LORD|Lord)\b")
        self._load_book_index(books_dir_override)

    def _load_book_index(self, books_dir_override=None):
        """Scans the books directory, gets metadata for each book, and populates book_map."""
        try:
            if books_dir_override:
                self.books_dir_path = books_dir_override
            else:
                current_dir = os.path.dirname(__file__)
                # Potential paths for 'data/books' directory
                path_option1 = os.path.join(
                    current_dir, "data", "books"
                )  # parser at project root
                path_option2 = os.path.join(
                    current_dir, "..", "data", "books"
                )  # parser in subdir (e.g. app/)
                path_option3 = os.path.join(
                    os.getcwd(), "data", "books"
                )  # running from project root

                if os.path.isdir(path_option1):
                    self.books_dir_path = path_option1
                elif os.path.isdir(path_option2):
                    self.books_dir_path = path_option2
                elif os.path.isdir(path_option3):
                    self.books_dir_path = path_option3
                else:
                    checked_paths = ", ".join(
                        filter(
                            None,
                            [
                                (
                                    path_option1 if not books_dir_override else None
                                ),  # Only show default if not overridden
                                path_option2 if not books_dir_override else None,
                                path_option3 if not books_dir_override else None,
                            ],
                        )
                    )
                    raise FileNotFoundError(
                        f"Bible books directory not found. Checked: {checked_paths or 'specified override path'}."
                    )

            if not os.path.isdir(
                self.books_dir_path
            ):  # Check again in case override was faulty
                raise FileNotFoundError(
                    f"Specified Bible books directory does not exist or is not a directory: {self.books_dir_path}"
                )

            self.logger.info(f"Scanning for Bible book files in: {self.books_dir_path}")
            book_files_found = 0
            for filename in os.listdir(self.books_dir_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(self.books_dir_path, filename)
                    try:
                        # We only need to load the book temporarily to get its name and abbrev for the map
                        with open(file_path, "r", encoding="utf-8") as f:
                            book_metadata = json.load(f)

                        book_name = book_metadata.get("name")
                        book_abbrev = book_metadata.get("abbrev")

                        if not book_name or not book_abbrev:
                            self.logger.warning(
                                f"Skipping {filename}: missing 'name' or 'abbrev' in JSON."
                            )
                            continue

                        canonical_name_from_file = filename[
                            :-5
                        ]  # e.g., "Genesis" from "Genesis.json"

                        self.book_map[book_name.lower()] = canonical_name_from_file
                        self.book_map[book_abbrev.lower()] = canonical_name_from_file

                        if book_name.lower() == "psalms":
                            self.book_map["psalm"] = (
                                canonical_name_from_file  # Alias "psalm" for "Psalms"
                            )

                        # Add common aliases
                        if book_name.lower() == "song of solomon":
                            self.book_map["song of songs"] = canonical_name_from_file

                        book_files_found += 1
                    except json.JSONDecodeError:
                        self.logger.error(
                            f"Error decoding JSON from book file {filename} in {self.books_dir_path}."
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error processing book file {filename} in {self.books_dir_path}: {e}"
                        )

            if not self.book_map:
                self.logger.error(
                    f"No book data loaded. Book map is empty. Searched in {self.books_dir_path}"
                )
            else:
                self.logger.info(
                    f"Book index with {len(self.book_map)} distinct entries (from {book_files_found} files) loaded successfully from {self.books_dir_path}."
                )

        except FileNotFoundError as e:
            self.logger.error(f"Error finding Bible books directory: {e}")
            self.books_dir_path = None
        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred loading the book index: {e}"
            )
            self.books_dir_path = None

    def is_data_loaded(self):
        """Checks if the book index (book_map and books_dir_path) was successfully loaded."""
        return bool(self.book_map and self.books_dir_path)

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
            self.logger.error(
                f"ValueError parsing numbers in reference: {reference_str}"
            )
            return None

    def get_passage(self, parsed_ref):
        """
        Retrieves and formats Bible passage text from the loaded JSON data.
        """
        if not self.is_data_loaded():
            self.logger.error(
                "Attempted to get passage, but Bible book index is not loaded."
            )
            return "Error: Bible book index not loaded on the server."

        book_name_key = parsed_ref["book_name"].lower()
        canonical_book_name = self.book_map.get(book_name_key)

        if canonical_book_name is None:
            # Try handling simple pluralization (e.g. "Proverb" vs "Proverbs")
            if book_name_key.endswith("s"):
                potential_singular_key = book_name_key[:-1]
                if self.book_map.get(potential_singular_key) is not None:
                    canonical_book_name = self.book_map.get(potential_singular_key)
            elif not book_name_key.endswith(
                "s"
            ):  # only try adding 's' if it doesn't already end with 's'
                potential_plural_key = book_name_key + "s"
                if self.book_map.get(potential_plural_key) is not None:
                    canonical_book_name = self.book_map.get(potential_plural_key)

            if canonical_book_name is None:
                self.logger.warning(
                    f"Book '{parsed_ref['book_name']}' (key: '{book_name_key}') not found in book_map."
                )
                return f"Book '{parsed_ref['book_name']}' not found. Please check spelling or try a standard abbreviation (e.g., Gen, Exo, Psa, Mat, Rom)."

        # Now, load the specific book's data
        book_file_path = os.path.join(
            self.books_dir_path, f"{canonical_book_name}.json"
        )
        try:
            with open(book_file_path, "r", encoding="utf-8") as f:
                book_data = json.load(f)  # This is the single book's data structure
        except FileNotFoundError:
            self.logger.error(
                f"Data file for book '{canonical_book_name}' not found at {book_file_path}."
            )
            return f"Error: Data file for book '{parsed_ref['book_name']}' not found on server."
        except json.JSONDecodeError:
            self.logger.error(
                f"Error decoding JSON for book '{canonical_book_name}' from {book_file_path}."
            )
            return f"Error: Could not decode data for book '{parsed_ref['book_name']}'."
        except Exception as e:
            self.logger.error(
                f"Unexpected error loading book data for '{canonical_book_name}' from {book_file_path}: {e}"
            )
            return f"Error: Could not load data for book '{parsed_ref['book_name']}' due to an unexpected issue."

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
                def replace_curly_content(match):
                    content = match.group(1)
                    if len(content.split()) <= 2:
                        return f"<em>{content}</em>"
                    return ""
                cleaned_verse_text = re.sub(r"\{(.*?)\}", replace_curly_content, verse_text).strip()
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
                def replace_curly_content(match):
                    content = match.group(1)
                    if len(content.split()) <= 2:
                        return f"<em>{content}</em>"
                    return ""
                cleaned_verse_text = re.sub(r"\{(.*?)\}", replace_curly_content, verse_text).strip()
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
            self.logger.error("Cannot fetch random Psalm, Bible book index not loaded.")
            return "Error: Bible book index not available to fetch a random Psalm."

        # "psalm" key in book_map should map to the canonical filename like "Psalms"
        psalms_canonical_name = self.book_map.get("psalm")

        if psalms_canonical_name is None:
            self.logger.error(
                "Book 'Psalms' (via 'psalm' key) not found in book_map for random Psalm."
            )
            return "Error: Book of Psalms not found in index."

        psalms_file_path = os.path.join(
            self.books_dir_path, f"{psalms_canonical_name}.json"
        )
        try:
            with open(psalms_file_path, "r", encoding="utf-8") as f:
                psalms_book_data = json.load(f)
        except FileNotFoundError:
            self.logger.error(
                f"Psalms data file ('{psalms_canonical_name}.json') not found at {psalms_file_path}."
            )
            return "Error: Psalms data file not found on server."
        except json.JSONDecodeError:
            self.logger.error(
                f"Error decoding Psalms JSON from '{psalms_canonical_name}.json' at {psalms_file_path}."
            )
            return "Error: Could not decode Psalms data."
        except Exception as e:
            self.logger.error(
                f"Unexpected error loading Psalms data from {psalms_file_path}: {e}"
            )
            return "Error: Could not load Psalms data due to an unexpected issue."

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
            or passage_text.startswith("Book '")  # From get_passage error
            or passage_text.startswith("Chapter ")  # From get_passage error
            or passage_text.startswith("No verses found")  # From get_passage error
        ):
            self.logger.error(
                f"Failed to get passage for random Psalm: {psalms_book_data['name']} {random_chapter_num}. Internal error: {passage_text}"
            )
            return "Error: Could not retrieve the random Psalm text due to an internal issue."

        self.logger.info(
            f"Successfully retrieved random Psalm: {psalms_book_data['name']} {random_chapter_num}"
        )
        return passage_text
