import unittest
from unittest.mock import MagicMock
import os
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

from llm_handler import LLMHandler
from bible_parser import BibleParser

# Import test cases from individual category files
from .faithbench_anger import ANGER_TEST_CASES
from .faithbench_apathy import APATHY_TEST_CASES
from .faithbench_despair import DESPAIR_TEST_CASES
from .faithbench_gluttony import GLUTTONY_TEST_CASES
from .faithbench_greed import GREED_TEST_CASES
from .faithbench_lust import LUST_TEST_CASES
from .faithbench_pride import PRIDE_TEST_CASES
from .faithbench_vanity import VANITY_TEST_CASES

# Load environment variables from .env file for API Key
load_dotenv()

# Skip integration tests if OPENROUTER_API_KEY is not set
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


@unittest.skipIf(
    not OPENROUTER_API_KEY, "OPENROUTER_API_KEY not set, skipping integration tests."
)
class TestFaithBenchIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()

        self.bible_parser = BibleParser(logger=self.mock_logger)
        self.assertTrue(
            self.bible_parser.is_data_loaded(),
            "Bible data (data/en_kjv.json) failed to load for tests. "
            "Ensure tests are run from the project root and the data file exists at 'data/en_kjv.json'.",
        )

        # Initialize real OpenAI client for OpenRouter
        self.openai_client = OpenAI(
            api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1"
        )

        self.llm_handler = LLMHandler(
            client=self.openai_client,  # Use the real client
            logger=self.mock_logger,
            bible_parser=self.bible_parser,
            model_name="deepseek/deepseek-r1-distill-qwen-32b:free",  # Ensure model_name is passed
        )

    def test_faithbench_prompts_integration(self):
        # Aggregate all test cases and add category information
        all_test_data_sources = {
            "anger": ANGER_TEST_CASES,
            "apathy": APATHY_TEST_CASES,
            "despair": DESPAIR_TEST_CASES,
            "gluttony": GLUTTONY_TEST_CASES,
            "greed": GREED_TEST_CASES,
            "lust": LUST_TEST_CASES,
            "pride": PRIDE_TEST_CASES,
            "vanity": VANITY_TEST_CASES,
        }

        ALL_FAITHBENCH_TEST_CASES_WITH_CATEGORY = []
        for category, cases_list in all_test_data_sources.items():
            if cases_list:  # Ensure the list is not None or empty
                for case_content in cases_list:
                    case_copy = case_content.copy()
                    case_copy["category"] = category
                    ALL_FAITHBENCH_TEST_CASES_WITH_CATEGORY.append(case_copy)
            else:
                self.mock_logger.warning(
                    f"No test cases found for category: {category}"
                )

        if not ALL_FAITHBENCH_TEST_CASES_WITH_CATEGORY:
            self.skipTest(
                "No FaithBench test cases were loaded from category files. Skipping integration test."
            )

        success_count = 0
        total_cases = len(ALL_FAITHBENCH_TEST_CASES_WITH_CATEGORY)
        results_summary = []

        for i, case in enumerate(tqdm(ALL_FAITHBENCH_TEST_CASES_WITH_CATEGORY, desc="FaithBench Progress")):
            with self.subTest(category=case["category"], prompt=case["prompt"]):
                mock_session = {}  # Simulate Flask session for conversation history

                self.mock_logger.info(
                    f"FaithBench Test Case {i+1}/{total_cases}: Category: {case['category']}, Prompt: '{case['prompt']}'"
                )

                # Call the method under test - this makes a REAL API call
                result, status_code = self.llm_handler.get_llm_bible_reference(
                    session=mock_session, user_query=case["prompt"]
                )

                # Basic check for successful API communication
                self.assertEqual(
                    status_code,
                    200,
                    f"Prompt '{case['prompt']}': Expected status 200, got {status_code}. Result: {result}",
                )
                self.assertIn(
                    "response",
                    result,
                    f"Prompt '{case['prompt']}': Result missing 'response' key. Result: {result}",
                )

                passage_text = result.get("response", "")
                returned_reference_line = (
                    passage_text.splitlines()[0].strip() if passage_text else ""
                )

                is_expected_reference_found = False
                matched_reference = None
                for expected_ref in case["expected_references"]:
                    # The BibleParser.get_passage prepends the canonical reference.
                    # We check if the first line of the response (the reference part) matches an expected reference.
                    # We should normalize the expected reference format if BibleParser does so.
                    parsed_expected_ref_obj = self.bible_parser.parse_reference(
                        expected_ref
                    )
                    canonical_expected_ref_header = ""
                    if parsed_expected_ref_obj:
                        # Get the canonical representation that get_passage would produce for the reference part
                        # Ensure get_passage doesn't return an error string before splitting
                        passage_or_error = self.bible_parser.get_passage(
                            parsed_expected_ref_obj
                        )
                        if (
                            not passage_or_error.startswith("Error:")
                            and not passage_or_error.startswith("Book '")
                            and not passage_or_error.startswith("Chapter ")
                            and not passage_or_error.startswith("No verses found")
                        ):
                            canonical_expected_ref_header = (
                                passage_or_error.splitlines()[0].strip()
                            )
                        else:  # Could not form canonical header from this expected_ref
                            self.mock_logger.warning(
                                f"Could not form canonical header for expected_ref '{expected_ref}' during test setup. Error: {passage_or_error}"
                            )
                            # Fallback to direct comparison if canonical form fails
                            if returned_reference_line == expected_ref.strip():
                                is_expected_reference_found = True
                                matched_reference = expected_ref
                                break
                            continue  # Try next expected_ref

                    if returned_reference_line == canonical_expected_ref_header:
                        is_expected_reference_found = True
                        matched_reference = expected_ref  # The one from our list
                        break
                    elif (
                        not canonical_expected_ref_header
                        and returned_reference_line == expected_ref.strip()
                    ):  # Fallback if canonical_expected_ref_header was not formed
                        is_expected_reference_found = True
                        matched_reference = expected_ref
                        break

                if is_expected_reference_found:
                    success_count += 1
                    results_summary.append(
                        f"PASS ({case['category']}): Prompt: \"{case['prompt']}\" -> Matched: \"{matched_reference}\" (Returned: \"{returned_reference_line}\")"
                    )
                    self.mock_logger.info(
                        f"FaithBench PASS ({case['category']}): Prompt: \"{case['prompt']}\" -> Matched: \"{matched_reference}\""
                    )
                else:
                    results_summary.append(
                        f"FAIL ({case['category']}): Prompt: \"{case['prompt']}\" -> Expected one of {case['expected_references']}, Got: \"{returned_reference_line}\""
                    )
                    self.mock_logger.warning(
                        f"FaithBench FAIL ({case['category']}): Prompt: \"{case['prompt']}\" -> Expected one of {case['expected_references']}, Got: \"{returned_reference_line}\""
                    )

                # This assertion will fail the test if any case fails, which is standard.
                # The summary is for overall reporting.
                self.assertTrue(
                    is_expected_reference_found,
                    f"LLM did not return a passage for one of the expected references "
                    f"{case['expected_references']}.\n"
                    f"Prompt: '{case['prompt']}'\n"
                    f"LLMHandler returned passage starting with: '{returned_reference_line}'\n"
                    f"Full passage returned (first 200 chars): '{passage_text[:200]}...'",
                )

        # After all tests, print a summary
        print("\n--- FaithBench Integration Test Summary ---")
        for res_line in results_summary:
            print(res_line)
        print(
            f"Overall Success Rate: {success_count}/{total_cases} ({((success_count/total_cases)*100) if total_cases > 0 else 0:.2f}%)"
        )
        print("-----------------------------------------\n")


if __name__ == "__main__":
    unittest.main()
