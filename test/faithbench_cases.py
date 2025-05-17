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
        "expected_references": [
            "Galatians 6:9",
            "Isaiah 40:31",
            "2 Corinthians 4:16-18",
        ],
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
