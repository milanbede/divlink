import unittest
from unittest.mock import MagicMock # Still needed for logger
import os
import json
from dotenv import load_dotenv
from openai import OpenAI # For real client initialization

from llm_handler import LLMHandler
from bible_parser import BibleParser

# Load environment variables from .env file for API Key
load_dotenv()

# FaithBench Test Data:
# This list should be populated with approximately 100 test cases.
# Each dictionary in the list represents a single test case with:
#   - "prompt": The user input string to send to the LLM.
#   - "expected_references": A list of Bible reference strings (e.g., "John 3:16", "Proverbs 3:5-6").
#                            The test will pass if the LLM returns a passage corresponding to
#                            AT LEAST ONE of these references.
#
# Example:
# {
#     "prompt": "User's question or statement.",
#     "expected_references": ["Book Chapter:Verse", "Book Chapter:Verse-AnotherVerse"]
# }
#
FAITHBENCH_TEST_CASES = [
    {
        "prompt": "I feel like giving up.",
        "expected_references": ["Galatians 6:9", "Isaiah 40:31", "2 Corinthians 4:16-18"],
    },
    {
        "prompt": "How should I treat others fairly?",
        "expected_references": ["Matthew 7:12", "Luke 6:31", "Philippians 2:3-4"],
    },
    # TODO: Add approximately 98 more test cases here to reach the 100 prompt goal.
    # Example of a case that might be harder for an LLM:
    # {
    #     "prompt": "Is it okay to tell a white lie to protect someone's feelings?",
    #     "expected_references": ["Proverbs 12:22", "Ephesians 4:25", "Colossians 3:9"]
    # },
]

# Skip integration tests if OPENROUTER_API_KEY is not set
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

@unittest.skipIf(not OPENROUTER_API_KEY, "OPENROUTER_API_KEY not set, skipping integration tests.")
class TestFaithBenchIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        
        self.bible_parser = BibleParser(logger=self.mock_logger)
        self.assertTrue(self.bible_parser.is_data_loaded(), 
                        "Bible data (data/en_kjv.json) failed to load for tests. "
                        "Ensure tests are run from the project root and the data file exists at 'data/en_kjv.json'.")

        # Initialize real OpenAI client for OpenRouter
        self.openai_client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
        
        self.llm_handler = LLMHandler(
            client=self.openai_client, # Use the real client
            logger=self.mock_logger,
            bible_parser=self.bible_parser,
        )

    def test_faithbench_prompts_integration(self):
        if not FAITHBENCH_TEST_CASES or (len(FAITHBENCH_TEST_CASES) == 2 and FAITHBENCH_TEST_CASES[0]["prompt"] == "I feel like giving up."):
            self.skipTest("FaithBench test cases are not fully populated. Skipping integration test.")

        success_count = 0
        total_cases = len(FAITHBENCH_TEST_CASES)
        results_summary = []

        for i, case in enumerate(FAITHBENCH_TEST_CASES):
            with self.subTest(prompt=case["prompt"]):
                mock_session = {}  # Simulate Flask session for conversation history

                self.mock_logger.info(f"FaithBench Test Case {i+1}/{total_cases}: Prompt: '{case['prompt']}'")

                # Call the method under test - this makes a REAL API call
                result, status_code = self.llm_handler.get_llm_bible_reference(
                    session=mock_session, user_query=case["prompt"]
                )

                # Basic check for successful API communication
                self.assertEqual(status_code, 200, 
                                 f"Prompt '{case['prompt']}': Expected status 200, got {status_code}. Result: {result}")
                self.assertIn("response", result, 
                              f"Prompt '{case['prompt']}': Result missing 'response' key. Result: {result}")
                
                passage_text = result.get("response", "")
                returned_reference_line = passage_text.splitlines()[0].strip() if passage_text else ""
                
                is_expected_reference_found = False
                matched_reference = None
                for expected_ref in case["expected_references"]:
                    # The BibleParser.get_passage prepends the canonical reference.
                    # We check if the first line of the response (the reference part) matches an expected reference.
                    # We should normalize the expected reference format if BibleParser does so.
                    parsed_expected_ref_obj = self.bible_parser.parse_reference(expected_ref)
                    canonical_expected_ref_header = ""
                    if parsed_expected_ref_obj:
                        # Get the canonical representation that get_passage would produce for the reference part
                        # Ensure get_passage doesn't return an error string before splitting
                        passage_or_error = self.bible_parser.get_passage(parsed_expected_ref_obj)
                        if not passage_or_error.startswith("Error:") and not passage_or_error.startswith("Book '") and not passage_or_error.startswith("Chapter ") and not passage_or_error.startswith("No verses found"):
                            canonical_expected_ref_header = passage_or_error.splitlines()[0].strip()
                        else: # Could not form canonical header from this expected_ref
                            self.mock_logger.warning(f"Could not form canonical header for expected_ref '{expected_ref}' during test setup. Error: {passage_or_error}")
                            # Fallback to direct comparison if canonical form fails
                            if returned_reference_line == expected_ref.strip():
                                is_expected_reference_found = True
                                matched_reference = expected_ref
                                break
                            continue # Try next expected_ref

                    if returned_reference_line == canonical_expected_ref_header:
                        is_expected_reference_found = True
                        matched_reference = expected_ref # The one from our list
                        break
                    elif not canonical_expected_ref_header and returned_reference_line == expected_ref.strip(): # Fallback if canonical_expected_ref_header was not formed
                        is_expected_reference_found = True
                        matched_reference = expected_ref
                        break
                
                if is_expected_reference_found:
                    success_count += 1
                    results_summary.append(f"PASS: Prompt: \"{case['prompt']}\" -> Matched: \"{matched_reference}\" (Returned: \"{returned_reference_line}\")")
                    self.mock_logger.info(f"FaithBench PASS: Prompt: \"{case['prompt']}\" -> Matched: \"{matched_reference}\"")
                else:
                    results_summary.append(f"FAIL: Prompt: \"{case['prompt']}\" -> Expected one of {case['expected_references']}, Got: \"{returned_reference_line}\"")
                    self.mock_logger.warning(f"FaithBench FAIL: Prompt: \"{case['prompt']}\" -> Expected one of {case['expected_references']}, Got: \"{returned_reference_line}\"")
                
                # This assertion will fail the test if any case fails, which is standard.
                # The summary is for overall reporting.
                self.assertTrue(is_expected_reference_found,
                                f"LLM did not return a passage for one of the expected references "
                                f"{case['expected_references']}.\n"
                                f"Prompt: '{case['prompt']}'\n"
                                f"LLMHandler returned passage starting with: '{returned_reference_line}'\n"
                                f"Full passage returned (first 200 chars): '{passage_text[:200]}...'")
        
        # After all tests, print a summary
        print("\n--- FaithBench Integration Test Summary ---")
        for res_line in results_summary:
            print(res_line)
        print(f"Overall Success Rate: {success_count}/{total_cases} ({((success_count/total_cases)*100) if total_cases > 0 else 0:.2f}%)")
        print("-----------------------------------------\n")


if __name__ == "__main__":
    unittest.main()
