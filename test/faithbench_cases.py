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
FAITHBENCH_TEST_CASES = []
