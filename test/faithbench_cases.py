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
        "prompt": "I'm addicted to porn and I hate myself for it.",
        "expected_references": [
            "1 Corinthians 10:13",
            "Job 31:1",
            "Romans 6:12-14",
        ],
    },
    {
        "prompt": "I feel stuck in the wrong place in life.",
        "expected_references": [
            "Jeremiah 29:11",
            "Romans 8:28",
            "Proverbs 3:5-6",
        ],
    },
    {
        "prompt": "I'm afraid to take the next step.",
        "expected_references": [
            "Joshua 1:9",
            "Psalm 56:3",
            "2 Timothy 1:7",
        ],
    },
    {
        "prompt": "I'm broke and don't know how to fix my life.",
        "expected_references": [
            "Matthew 6:31-33",
            "Philippians 4:19",
            "Proverbs 3:9-10",
        ],
    },
    {
        "prompt": "I feel like I missed out on life.",
        "expected_references": [
            "Joel 2:25",
            "Ecclesiastes 3:1",
            "Isaiah 43:18-19",
        ],
    },
    {
        "prompt": "People are targeting and harassing me.",
        "expected_references": [
            "Psalm 91:1-7",
            "Romans 12:19",
            "Matthew 5:10-12",
        ],
    },
    {
        "prompt": "I want to take revenge on someone who hurt me.",
        "expected_references": [
            "Romans 12:17-21",
            "Proverbs 20:22",
            "Matthew 5:44",
        ],
    },
    {
        "prompt": "My mother is overbearing and I feel trapped.",
        "expected_references": [
            "Ephesians 6:2-4",
            "Genesis 2:24",
            "Colossians 3:21",
        ],
    },
    {
        "prompt": "I waste too much time doomscrolling.",
        "expected_references": [
            "Ephesians 5:15-16",
            "Philippians 4:8",
            "Colossians 3:2",
        ],
    },
    {
        "prompt": "I'm constantly comparing myself to others.",
        "expected_references": [
            "Galatians 6:4-5",
            "2 Corinthians 10:12",
            "Psalm 139:14",
        ],
    },
    {
        "prompt": "I feel spiritually dry and distant from God.",
        "expected_references": [
            "Psalm 42:1-2",
            "James 4:8",
            "Jeremiah 29:13",
        ],
    },
    {
        "prompt": "I'm struggling with lustful thoughts.",
        "expected_references": [
            "Matthew 5:28",
            "1 Thessalonians 4:3-5",
            "Psalm 119:9-11",
        ],
    },
    {
        "prompt": "I feel like a failure.",
        "expected_references": [
            "Romans 8:1",
            "Philippians 1:6",
            "Psalm 73:26",
        ],
    },
    {
        "prompt": "I want validation from others.",
        "expected_references": [
            "Galatians 1:10",
            "Colossians 3:23",
            "1 Thessalonians 2:4",
        ],
    },
    {
        "prompt": "I'm struggling with pride.",
        "expected_references": [
            "Proverbs 16:18",
            "James 4:6",
            "Philippians 2:3",
        ],
    },
    {
        "prompt": "I feel like a coward.",
        "expected_references": [
            "2 Timothy 1:7",
            "Deuteronomy 31:6",
            "Joshua 1:9",
        ],
    },
    {
        "prompt": "I'm lazy and unmotivated.",
        "expected_references": [
            "Proverbs 13:4",
            "Colossians 3:23",
            "Proverbs 6:6-11",
        ],
    },
    {
        "prompt": "I keep getting betrayed by friends.",
        "expected_references": [
            "Psalm 41:9",
            "Luke 6:27-28",
            "Romans 12:17-21",
        ],
    },
    {
        "prompt": "I'm jealous of my friends' success.",
        "expected_references": [
            "James 3:16",
            "Proverbs 14:30",
            "Romans 12:15",
        ],
    },
    {
        "prompt": "I can't forgive myself for my past mistakes.",
        "expected_references": [
            "1 John 1:9",
            "Isaiah 43:25",
            "Romans 8:1",
        ],
    },
    {
        "prompt": "I'm afraid of failing again.",
        "expected_references": [
            "Psalm 37:23-24",
            "Philippians 4:13",
            "Isaiah 41:10",
        ],
    },
    {
        "prompt": "I don't know my purpose in life.",
        "expected_references": [
            "Jeremiah 29:11",
            "Ephesians 2:10",
            "Proverbs 19:21",
        ],
    },
    {
        "prompt": "I feel like God is silent.",
        "expected_references": [
            "Psalm 13:1-2",
            "Lamentations 3:25-26",
            "Isaiah 30:18",
        ],
    },
    {
        "prompt": "I'm anxious about my future.",
        "expected_references": [
            "Philippians 4:6-7",
            "Matthew 6:34",
            "Psalm 55:22",
        ],
    },
    {
        "prompt": "I have trouble trusting people.",
        "expected_references": [
            "Proverbs 3:5-6",
            "Psalm 118:8",
            "Jeremiah 17:7",
        ],
    },
    {
        "prompt": "I want to be a better man.",
        "expected_references": [
            "1 Timothy 4:12",
            "Micah 6:8",
            "Titus 2:6-8",
        ],
    },
    {
        "prompt": "I'm tempted to cheat in school.",
        "expected_references": [
            "Proverbs 10:9",
            "Colossians 3:23",
            "Luke 16:10",
        ],
    },
    {
        "prompt": "I feel like I don't fit in anywhere.",
        "expected_references": [
            "1 Peter 2:9",
            "Romans 12:2",
            "Psalm 139:13-16",
        ],
    },
    {
        "prompt": "I'm angry all the time.",
        "expected_references": [
            "James 1:19-20",
            "Ephesians 4:26-27",
            "Proverbs 29:11",
        ],
    },
    {
        "prompt": "I can't stop lying.",
        "expected_references": [
            "Ephesians 4:25",
            "Proverbs 12:22",
            "Colossians 3:9",
        ],
    },
    {
        "prompt": "I'm addicted to video games.",
        "expected_references": [
            "1 Corinthians 6:12",
            "Ephesians 5:15-16",
            "Colossians 3:17",
        ],
    },
    {
        "prompt": "I feel like my prayers aren't heard.",
        "expected_references": [
            "1 John 5:14",
            "Psalm 34:17",
            "Matthew 7:7-8",
        ],
    },
    {
        "prompt": "I want to quit my bad habits.",
        "expected_references": [
            "Romans 12:2",
            "1 Corinthians 10:13",
            "Galatians 5:16-17",
        ],
    },
    {
        "prompt": "I'm afraid I'll never find love.",
        "expected_references": [
            "Psalm 37:4",
            "Proverbs 18:22",
            "Matthew 6:33",
        ],
    },
    {
        "prompt": "My dad left when I was young. How do I deal with that pain?",
        "expected_references": [
            "Psalm 68:5",
            "Isaiah 41:10",
            "2 Corinthians 1:3-4",
        ],
    },
    {
        "prompt": "I feel like I'm not good enough.",
        "expected_references": [
            "2 Corinthians 12:9-10",
            "Psalm 139:14",
            "Romans 8:37",
        ],
    },
    {
        "prompt": "I'm scared of what people think of me.",
        "expected_references": [
            "Proverbs 29:25",
            "Galatians 1:10",
            "Isaiah 51:12",
        ],
    },
    {
        "prompt": "I want to be rich.",
        "expected_references": [
            "1 Timothy 6:9-10",
            "Matthew 6:19-21",
            "Proverbs 23:4-5",
        ],
    },
    {
        "prompt": "I keep falling back into sin.",
        "expected_references": [
            "1 John 1:9",
            "Romans 7:15-25",
            "Proverbs 24:16",
        ],
    },
    {
        "prompt": "I'm addicted to weed.",
        "expected_references": [
            "1 Corinthians 6:12",
            "Romans 6:16",
            "Galatians 5:1",
        ],
    },
    {
        "prompt": "I don't want to forgive someone who hurt me badly.",
        "expected_references": [
            "Ephesians 4:32",
            "Matthew 6:14-15",
            "Colossians 3:13",
        ],
    },
    {
        "prompt": "I'm exhausted from trying to please everyone.",
        "expected_references": [
            "Matthew 11:28-30",
            "Galatians 1:10",
            "Psalm 46:10",
        ],
    },
    {
        "prompt": "I feel like my dreams are impossible.",
        "expected_references": [
            "Luke 1:37",
            "Philippians 4:13",
            "Mark 9:23",
        ],
    },
    {
        "prompt": "I'm afraid to talk about my faith.",
        "expected_references": [
            "Romans 1:16",
            "Matthew 10:32-33",
            "2 Timothy 1:8",
        ],
    },
    {
        "prompt": "I want to be respected.",
        "expected_references": [
            "Proverbs 22:1",
            "1 Timothy 4:12",
            "Romans 12:10",
        ],
    },
    {
        "prompt": "I'm always second-guessing myself.",
        "expected_references": [
            "James 1:5-8",
            "Proverbs 3:5-6",
            "Isaiah 26:3",
        ],
    },
    {
        "prompt": "I have a hard time apologizing.",
        "expected_references": [
            "James 5:16",
            "Matthew 5:23-24",
            "Colossians 3:13",
        ],
    },
    {
        "prompt": "I'm struggling with body image.",
        "expected_references": [
            "Psalm 139:14",
            "1 Samuel 16:7",
            "1 Corinthians 6:19-20",
        ],
    },
    {
        "prompt": "I feel like I have no friends.",
        "expected_references": [
            "Proverbs 18:24",
            "Psalm 68:6",
            "John 15:15",
        ],
    },
    {
        "prompt": "I'm afraid of being alone forever.",
        "expected_references": [
            "Deuteronomy 31:6",
            "Isaiah 41:10",
            "Matthew 28:20",
        ],
    },
    {
        "prompt": "I want to be a good leader.",
        "expected_references": [
            "1 Timothy 3:1-7",
            "Mark 10:43-45",
            "Proverbs 11:14",
        ],
    },
    {
        "prompt": "My parents don't understand me.",
        "expected_references": [
            "Ephesians 6:1-4",
            "Proverbs 1:8-9",
            "Colossians 3:20",
        ],
    },
    {
        "prompt": "I feel like a burden.",
        "expected_references": [
            "Matthew 11:28-30",
            "Psalm 55:22",
            "1 Peter 5:7",
        ],
    },
    {
        "prompt": "I'm worried about my grades.",
        "expected_references": [
            "Philippians 4:6-7",
            "Colossians 3:23",
            "Proverbs 16:3",
        ],
    },
    {
        "prompt": "I want to quit my job.",
        "expected_references": [
            "Proverbs 16:3",
            "Colossians 3:23",
            "James 1:5",
        ],
    },
    {
        "prompt": "I feel like God can't use me.",
        "expected_references": [
            "1 Corinthians 1:27-29",
            "Jeremiah 1:6-8",
            "Exodus 4:10-12",
        ],
    },
    {
        "prompt": "I'm afraid I'll disappoint my family.",
        "expected_references": [
            "Colossians 3:23",
            "Proverbs 29:25",
            "Psalm 27:10",
        ],
    },
    {
        "prompt": "I want to be more disciplined.",
        "expected_references": [
            "2 Timothy 1:7",
            "1 Corinthians 9:24-27",
            "Proverbs 25:28",
        ],
    },
    {
        "prompt": "I'm struggling with self-control.",
        "expected_references": [
            "Galatians 5:22-23",
            "Proverbs 25:28",
            "1 Corinthians 10:13",
        ],
    },
    {
        "prompt": "I don't know how to pray.",
        "expected_references": [
            "Matthew 6:9-13",
            "Romans 8:26",
            "Luke 11:1-4",
        ],
    },
    {
        "prompt": "I want to make a difference in the world.",
        "expected_references": [
            "Matthew 5:13-16",
            "Micah 6:8",
            "James 1:27",
        ],
    },
    {
        "prompt": "I'm afraid of death.",
        "expected_references": [
            "John 11:25-26",
            "Romans 8:38-39",
            "Psalm 23:4",
        ],
    },
    {
        "prompt": "I'm struggling with doubt.",
        "expected_references": [
            "Mark 9:24",
            "James 1:5-8",
            "John 20:27-29",
        ],
    },
    {
        "prompt": "I want to be a better friend.",
        "expected_references": [
            "Proverbs 17:17",
            "John 15:13",
            "1 Thessalonians 5:11",
        ],
    },
    {
        "prompt": "I'm being bullied.",
        "expected_references": [
            "Psalm 34:18-19",
            "Romans 12:17-21",
            "Matthew 5:44",
        ],
    },
    {
        "prompt": "I'm struggling with anger towards my dad.",
        "expected_references": [
            "Ephesians 4:26-27",
            "Colossians 3:13",
            "Exodus 20:12",
        ],
    },
    {
        "prompt": "I feel like my life has no meaning.",
        "expected_references": [
            "Ecclesiastes 12:13",
            "John 10:10",
            "Romans 8:28",
        ],
    },
    {
        "prompt": "I want to be more generous.",
        "expected_references": [
            "2 Corinthians 9:6-8",
            "Acts 20:35",
            "Proverbs 11:25",
        ],
    },
    {
        "prompt": "I'm struggling with envy.",
        "expected_references": [
            "James 3:16",
            "Proverbs 14:30",
            "Exodus 20:17",
        ],
    },
    {
        "prompt": "I want to stop gossiping.",
        "expected_references": [
            "Ephesians 4:29",
            "Proverbs 16:28",
            "James 1:26",
        ],
    },
    {
        "prompt": "I feel like I can't change.",
        "expected_references": [
            "2 Corinthians 5:17",
            "Romans 12:2",
            "Philippians 1:6",
        ],
    },
    {
        "prompt": "I'm struggling with my sexual identity.",
        "expected_references": [
            "Genesis 1:27",
            "1 Corinthians 6:18-20",
            "Psalm 139:13-16",
        ],
    },
    {
        "prompt": "I'm worried about my future career.",
        "expected_references": [
            "Proverbs 16:3",
            "Jeremiah 29:11",
            "Psalm 32:8",
        ],
    },
    {
        "prompt": "I want to be a good boyfriend.",
        "expected_references": [
            "1 Corinthians 13:4-7",
            "Ephesians 5:25",
            "Philippians 2:3-4",
        ],
    },
    {
        "prompt": "I feel guilty for not reading the Bible.",
        "expected_references": [
            "Psalm 119:105",
            "2 Timothy 3:16-17",
            "Joshua 1:8",
        ],
    },
    {
        "prompt": "I'm struggling with social anxiety.",
        "expected_references": [
            "Isaiah 41:10",
            "Philippians 4:6-7",
            "2 Timothy 1:7",
        ],
    },
    {
        "prompt": "I want to be more courageous.",
        "expected_references": [
            "Joshua 1:9",
            "Psalm 27:1",
            "1 Corinthians 16:13",
        ],
    },
    {
        "prompt": "I don't know how to make friends.",
        "expected_references": [
            "Proverbs 18:24",
            "Romans 12:10",
            "Philippians 2:3-4",
        ],
    },
    {
        "prompt": "I'm addicted to my phone.",
        "expected_references": [
            "1 Corinthians 6:12",
            "Ephesians 5:15-16",
            "Colossians 3:2",
        ],
    },
    {
        "prompt": "I feel like I'm always overlooked.",
        "expected_references": [
            "1 Samuel 16:7",
            "Psalm 27:10",
            "Matthew 6:4",
        ],
    },
    {
        "prompt": "I'm afraid of rejection.",
        "expected_references": [
            "Isaiah 41:10",
            "Romans 8:31",
            "Psalm 27:10",
        ],
    },
    {
        "prompt": "I want to be more grateful.",
        "expected_references": [
            "1 Thessalonians 5:18",
            "Colossians 3:15",
            "Psalm 107:1",
        ],
    },
    {
        "prompt": "I'm struggling with my faith.",
        "expected_references": [
            "Mark 9:24",
            "Hebrews 11:1",
            "Romans 10:17",
        ],
    },
    {
        "prompt": "I want to be a good son.",
        "expected_references": [
            "Ephesians 6:1-3",
            "Proverbs 1:8-9",
            "Colossians 3:20",
        ],
    },
    {
        "prompt": "I'm afraid of being vulnerable.",
        "expected_references": [
            "2 Corinthians 12:9-10",
            "James 5:16",
            "Proverbs 27:17",
        ],
    },
    {
        "prompt": "I want to be more humble.",
        "expected_references": [
            "Philippians 2:3",
            "James 4:6",
            "Micah 6:8",
        ],
    },
    {
        "prompt": "I'm worried about my health.",
        "expected_references": [
            "3 John 1:2",
            "Psalm 103:2-3",
            "Philippians 4:6-7",
        ],
    },
    {
        "prompt": "I want to be more patient.",
        "expected_references": [
            "James 1:2-4",
            "Galatians 5:22",
            "Romans 12:12",
        ],
    },
    {
        "prompt": "I'm struggling with temptation.",
        "expected_references": [
            "1 Corinthians 10:13",
            "James 1:13-15",
            "Matthew 26:41",
        ],
    },
    {
        "prompt": "I'm afraid of the future.",
        "expected_references": [
            "Jeremiah 29:11",
            "Matthew 6:34",
            "Psalm 23:4",
        ],
    },
    {
        "prompt": "I want to be a better student.",
        "expected_references": [
            "Colossians 3:23",
            "Proverbs 1:5",
            "James 1:5",
        ],
    },
    {
        "prompt": "I can't stop procrastinating.",
        "expected_references": [
            "Proverbs 6:6-8",
            "Ephesians 5:15-16",
            "Colossians 3:23",
        ],
    },
    {
        "prompt": "I want to be more honest.",
        "expected_references": [
            "Ephesians 4:25",
            "Proverbs 12:22",
            "Colossians 3:9",
        ],
    },
    {
        "prompt": "I'm struggling with greed.",
        "expected_references": [
            "Luke 12:15",
            "1 Timothy 6:10",
            "Hebrews 13:5",
        ],
    },
    {
        "prompt": "I want to have a better relationship with my siblings.",
        "expected_references": [
            "Ephesians 4:32",
            "Romans 12:10",
            "Colossians 3:13",
        ],
    },
    {
        "prompt": "I'm worried about my parents' divorce.",
        "expected_references": [
            "Psalm 34:18",
            "Isaiah 41:10",
            "2 Corinthians 1:3-4",
        ],
    },
    {
        "prompt": "I want to be more faithful.",
        "expected_references": [
            "Galatians 5:22-23",
            "Hebrews 11:6",
            "2 Timothy 2:13",
        ],
    },
    {
        "prompt": "I'm struggling with loneliness.",
        "expected_references": [
            "Psalm 68:6",
            "Matthew 28:20",
            "Hebrews 13:5",
        ],
    },
    {
        "prompt": "I want to be a better listener.",
        "expected_references": [
            "James 1:19",
            "Proverbs 18:13",
            "Proverbs 19:20",
        ],
    },
    {
        "prompt": "I'm tempted to give up on my dreams.",
        "expected_references": [
            "Galatians 6:9",
            "Philippians 3:13-14",
            "Isaiah 40:31",
        ],
    },
    {
        "prompt": "I'm struggling with my identity.",
        "expected_references": [
            "2 Corinthians 5:17",
            "Galatians 2:20",
            "1 Peter 2:9",
        ],
    },
    {
        "prompt": "I want to be a good example.",
        "expected_references": [
            "1 Timothy 4:12",
            "Matthew 5:16",
            "Philippians 2:14-15",
        ],
    },
    {
        "prompt": "I'm afraid to ask for help.",
        "expected_references": [
            "James 5:16",
            "Galatians 6:2",
            "Ecclesiastes 4:9-10",
        ],
    },
]
