import unittest
from unittest.mock import patch, MagicMock # Ensure patch and MagicMock are imported
import os
import json
import datetime # Add this if not already present at the top of test_unit.py
import re # Added import re at the top level
from main import app  # Import the Flask app
from bible_parser import BibleParser

class TestBibleParserUnit(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        # Initialize BibleParser with a controlled environment if possible,
        # or use the actual data knowing its structure for specific tests.
        # For get_random_verse, we'll rely on mocking random selections.
        # self.parser = BibleParser(logger=self.logger, books_dir_override="data/books_test_subset") # Use a dedicated test subset if needed or mock heavily
        # For this test, we will let BibleParser initialize normally and then mock interactions.

    @patch('random.choice')
    def test_get_random_verse_success(self, mock_random_choice):
        # This test relies on the actual data being present in 'data/books'
        # It mocks the random choices to pick a predictable path.

        # Initialize a real parser to get book map and paths
        # This parser instance is only for setup, not the one under test with mocks.
        setup_parser = BibleParser(logger=MagicMock())
        if not setup_parser.is_data_loaded():
            self.skipTest("Real Bible data not loaded via setup_parser, cannot run this test.")

        available_canonical_books = list(set(setup_parser.book_map.values()))
        if not available_canonical_books:
            self.skipTest("No book canonical names found by setup_parser, cannot run test.")

        # Target "Genesis" for predictability if it exists, else pick the first available
        target_book_canonical_name = "Genesis"
        if target_book_canonical_name not in available_canonical_books:
            target_book_canonical_name = available_canonical_books[0]

        # Load the actual data for the target book to determine chapter and verse for mocking
        try:
            book_file_path = os.path.join(setup_parser.books_dir_path, f"{target_book_canonical_name}.json")
            with open(book_file_path, 'r', encoding='utf-8') as f:
                book_data_content = json.load(f)
        except Exception as e:
            self.skipTest(f"Could not load data for target book '{target_book_canonical_name}' to set up mocks: {e}")

        if not book_data_content.get("chapters"):
            self.skipTest(f"Book '{target_book_canonical_name}' has no 'chapters' field or it's empty.")

        num_chapters = len(book_data_content["chapters"])
        if num_chapters == 0:
            self.skipTest(f"Book '{target_book_canonical_name}' has no chapters, cannot test random verse selection.")

        # Target chapter 1 (index 0)
        target_chapter_index = 0 # This is an index
        if target_chapter_index >= num_chapters:
             self.skipTest(f"Target chapter index {target_chapter_index} is out of bounds for '{target_book_canonical_name}'.")

        verses_in_target_chapter = book_data_content["chapters"][target_chapter_index]
        if not verses_in_target_chapter:
            self.skipTest(f"Chapter {target_chapter_index + 1} of '{target_book_canonical_name}' has no verses.")

        # Target verse 1 (index 0)
        target_verse_index = 0 # This is an index
        if target_verse_index >= len(verses_in_target_chapter):
            self.skipTest(f"Target verse index {target_verse_index} is out of bounds for chapter {target_chapter_index+1} of '{target_book_canonical_name}'.")

        # Configure mock_random_choice side_effect:
        # 1. Selects the canonical book name (e.g., "Genesis")
        # 2. Selects the chapter data (a list of verse strings) from the chosen book's "chapters" list
        # 3. Selects the verse text (a string) from the chosen chapter's list of verses

        # The actual chapter data (list of verses) for the chosen chapter
        chosen_chapter_data = book_data_content["chapters"][target_chapter_index]
        # The actual verse string for the chosen verse in the chosen chapter
        chosen_verse_string = chosen_chapter_data[target_verse_index]

        mock_random_choice.side_effect = [
            target_book_canonical_name, # 1st call in get_random_verse
            chosen_chapter_data,        # 2nd call in get_random_verse
            chosen_verse_string         # 3rd call in get_random_verse
        ]

        # This is the parser instance we are testing.
        # It will use the normal book_map loaded from disk, but its random choices will be mocked.
        parser_under_test = BibleParser(logger=self.logger)
        if not parser_under_test.is_data_loaded():
             self.skipTest("BibleParser under test could not load data.") # Should ideally not happen if setup_parser worked

        verse_output = parser_under_test.get_random_verse()
        self.assertIsNotNone(verse_output)
        self.assertIsInstance(verse_output, str)

        expected_book_display_name = book_data_content.get("name", target_book_canonical_name)
        # The verse text from get_passage includes HTML formatting.
        # We need to simulate how get_passage processes the raw verse string.
        # The raw verse string is `chosen_verse_string`.

        # Simulate cleaning from get_passage (simplified, actual get_passage has more complex logic)
        # Basic curly brace removal for comparison: {words} -> <em>words</em> or ""
        def replace_curly_content(match):
            content = match.group(1)
            if len(content.split()) <= 2: # As per get_passage logic
                return f"<em>{content}</em>"
            return ""
        expected_verse_text_cleaned = re.sub(r"\{(.*?)\}", replace_curly_content, chosen_verse_string).strip()
        # Divine name highlighting
        expected_verse_text_highlighted = parser_under_test.divine_name_pattern.sub(
            r'<span class="divine-name">\1</span>', expected_verse_text_cleaned
        )

        # The chapter number is target_chapter_index + 1
        # The verse number is target_verse_index + 1
        expected_reference_display = f"{expected_book_display_name} {target_chapter_index + 1}:{target_verse_index + 1}"

        self.assertTrue(verse_output.startswith(expected_reference_display),
                        f"Output '{verse_output}' does not start with expected reference '{expected_reference_display}'")
        self.assertIn(expected_verse_text_highlighted, verse_output,
                      f"Expected verse text '{expected_verse_text_highlighted}' not found in output '{verse_output}'")

        self.assertEqual(mock_random_choice.call_count, 3, "random.choice was not called the expected number of times")

    @patch('random.choice')
    @patch.object(BibleParser, 'is_data_loaded', return_value=False)
    def test_get_random_verse_no_data_loaded(self, mock_is_data_loaded, mock_random_choice):
        # For this test, the parser instance itself will report is_data_loaded as False
        parser = BibleParser(logger=self.logger) # is_data_loaded is already patched
        verse = parser.get_random_verse()
        self.assertIsNone(verse)
        self.logger.error.assert_called_with("Cannot get random verse, Bible book index not loaded.")
        mock_random_choice.assert_not_called()

    @patch('random.choice')
    def test_get_random_verse_empty_book_map(self, mock_random_choice):
        # Test with a parser that has an empty book_map after initial load attempt
        parser = BibleParser(logger=self.logger)
        # Simulate a scenario where loading finished but book_map is empty
        parser.book_map = {}
        # Ensure books_dir_path is set, so is_data_loaded might pass if it only checks that
        # However, the actual check in get_random_verse is `list(set(self.book_map.values()))`
        # So, an empty book_map is sufficient.

        verse = parser.get_random_verse()
        self.assertIsNone(verse)
        self.logger.error.assert_called_with("No canonical book names available to select a random verse.")
        mock_random_choice.assert_not_called() # Should not be called if book_map is empty

    # TODO: More tests for:
    # - Book JSON is malformed (json.JSONDecodeError) -> get_random_verse returns None, logs error
    # - Book file not found (FileNotFoundError) -> get_random_verse returns None, logs error
    # - Loaded book_data has no "chapters" key or "chapters" is empty -> get_random_verse returns None, logs error
    # - Selected chapter (list of verses) is empty -> get_random_verse returns None, logs error

class TestApiUnit(unittest.TestCase):
    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        app.testing = True

        self.mock_bible_parser_instance = MagicMock(spec=BibleParser)
        self.patcher_bible_parser = patch('main.bible_parser', self.mock_bible_parser_instance)
        self.patcher_bible_parser.start()

        # Add new mock for llm_handler.get_llm_bible_reference
        self.mock_llm_get_reference = MagicMock()
        self.patcher_llm_handler = patch('main.llm_handler.get_llm_bible_reference', self.mock_llm_get_reference)
        self.patcher_llm_handler.start()

        # Mock for holidays.CountryHoliday
        self.mock_holidays_instance = MagicMock()
        self.patcher_holidays = patch('main.holidays.CountryHoliday', return_value=self.mock_holidays_instance) # Patch the class
        self.patcher_holidays.start()

        # Mock for datetime.date.today
        self.mock_datetime_today = patch('main.datetime.date') # Patch date class in main
        self.mock_date_today_instance = self.mock_datetime_today.start()

    def tearDown(self):
        self.patcher_bible_parser.stop()
        self.patcher_llm_handler.stop() # Stop the new patcher
        self.patcher_holidays.stop()
        self.mock_datetime_today.stop()
        self.app_context.pop()

    # Remove or comment out old test_verse_of_the_day_success and test_verse_of_the_day_fallback

    def test_verse_of_the_day_success_no_holiday(self):
        # Mock date and holiday
        fixed_date = datetime.date(2023, 10, 26)
        self.mock_date_today_instance.today.return_value = fixed_date
        self.mock_holidays_instance.get.return_value = None # No holiday

        # Mock LLM response
        expected_llm_response = {"response": "LLM verse for October 26, 2023.", "score": 10}
        self.mock_llm_get_reference.return_value = (expected_llm_response, 200)

        response = self.client.get('/api/verse_of_the_day')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['response'], expected_llm_response['response'])
        self.assertEqual(data['score'], expected_llm_response['score'])

        expected_query = "Select a single verse from the King James Bible that offers strength, hope, or encouragement for October 26, 2023."
        self.mock_llm_get_reference.assert_called_once()
        # Assuming session object is passed as first arg, query is second.
        # Access the call arguments: args, kwargs = self.mock_llm_get_reference.call_args
        # args[1] should be the query
        self.assertEqual(self.mock_llm_get_reference.call_args[0][1], expected_query)
        self.mock_holidays_instance.get.assert_called_once_with(fixed_date)

    def test_verse_of_the_day_success_with_holiday(self):
        fixed_date = datetime.date(2023, 12, 25) # Christmas
        self.mock_date_today_instance.today.return_value = fixed_date
        self.mock_holidays_instance.get.return_value = "Christmas Day" # Holiday

        expected_llm_response = {"response": "LLM verse for Christmas.", "score": 10}
        self.mock_llm_get_reference.return_value = (expected_llm_response, 200)

        response = self.client.get('/api/verse_of_the_day')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['response'], expected_llm_response['response'])

        expected_query = "Select a single verse from the King James Bible that offers strength, hope, or encouragement for December 25, 2023, especially considering today is Christmas Day."
        self.mock_llm_get_reference.assert_called_once()
        self.assertEqual(self.mock_llm_get_reference.call_args[0][1], expected_query)
        self.mock_holidays_instance.get.assert_called_once_with(fixed_date)

    def test_verse_of_the_day_llm_failure_fallback_to_random_verse(self):
        fixed_date = datetime.date(2023, 10, 27)
        self.mock_date_today_instance.today.return_value = fixed_date
        self.mock_holidays_instance.get.return_value = None

        # Mock LLM failure
        self.mock_llm_get_reference.return_value = ({"error": "LLM down"}, 500)

        # Mock bible_parser's get_random_verse
        expected_random_verse = "Random verse from parser."
        self.mock_bible_parser_instance.get_random_verse.return_value = expected_random_verse

        response = self.client.get('/api/verse_of_the_day')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['response'], expected_random_verse)
        self.assertIsNone(data['score'])
        self.mock_llm_get_reference.assert_called_once()
        self.mock_bible_parser_instance.get_random_verse.assert_called_once()

    def test_verse_of_the_day_llm_failure_and_random_verse_failure_ultimate_fallback(self):
        fixed_date = datetime.date(2023, 10, 28)
        self.mock_date_today_instance.today.return_value = fixed_date
        self.mock_holidays_instance.get.return_value = None

        self.mock_llm_get_reference.return_value = ({"error": "LLM down"}, 500)
        self.mock_bible_parser_instance.get_random_verse.return_value = None # Simulate failure

        response = self.client.get('/api/verse_of_the_day')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        expected_fallback_verse = "In the beginning God created the heaven and the earth. - Genesis 1:1"
        self.assertEqual(data['response'], expected_fallback_verse)
        self.assertIsNone(data['score'])
        self.mock_llm_get_reference.assert_called_once()
        self.mock_bible_parser_instance.get_random_verse.assert_called_once()

    def test_verse_of_the_day_unexpected_exception_fallback(self):
        # Make one of the internal calls raise an unexpected exception
        self.mock_date_today_instance.today.side_effect = Exception("Unexpected error in date")

        response = self.client.get('/api/verse_of_the_day')
        self.assertEqual(response.status_code, 500) # Should be 500 as per endpoint's catch-all
        data = json.loads(response.data.decode('utf-8'))
        expected_fallback_verse = "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life. – John 3:16"
        self.assertEqual(data['response'], expected_fallback_verse)
        self.assertIsNone(data['score'])

    def test_random_psalm_success(self):
        expected_psalm = "Psalm 23:1\nThe LORD is my shepherd..."
        self.mock_bible_parser_instance.get_random_psalm_passage.return_value = expected_psalm

        response = self.client.get('/api/random_psalm')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['response'], expected_psalm)
        self.assertIsNone(data['score']) # Assuming random_psalm also returns score:None
        self.mock_bible_parser_instance.get_random_psalm_passage.assert_called_once()

if __name__ == '__main__':
    unittest.main()
