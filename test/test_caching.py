import unittest
from unittest import mock
import datetime

# Assuming main.py and llm_handler.py are structured to allow class/function imports
# We might need to adjust paths or use sys.path.append if running tests directly from test/ directory
# For now, assume they are importable.
# If main.py runs Flask app setup at import time, we need to be careful or mock more.

# Mocking google.cloud.firestore and sentence_transformers before they are imported by main/llm_handler
# This is a common pattern if modules are initialized at import time.
# However, for this task, we'll mock specific instances passed around or global ones.

from google.cloud import firestore # For firestore.SERVER_TIMESTAMP, if used in mocks
# It's tricky to directly mock google.cloud.firestore.Client if it's instantiated globally in main.py
# We will use @patch decorator on 'main.db' for VoD tests.

# For LLMHandler tests, we pass mocks into its constructor.
from llm_handler import LLMHandler

# For VoD tests, we'll need to interact with the Flask app if testing endpoint directly
# or try to test the endpoint function in isolation if possible.
# The prompt asks for testing "endpoint logic", suggesting direct function call or test_client.
# Let's assume we can patch 'main.db' and 'main.llm_handler' and then call the route function logic.
# This requires main.py to be importable without side effects like starting the server.

# Placeholder for imports from google.cloud.firestore_v1.vector etc.
# These are mainly for type hinting or if we need to construct Vector for assertions.
try:
    from google.cloud.firestore_v1.base_vector_query import Vector, DistanceMeasure
except ImportError:
    # Fallback if the path is slightly different or for environments where it's not critical for test logic
    Vector = mock.Mock
    DistanceMeasure = mock.Mock


class TestVerseOfTheDayCaching(unittest.TestCase):
    def setUp(self):
        # It's often better to patch objects where they are used (e.g., 'main.db')
        # rather than where they are defined.
        self.mock_db_patcher = mock.patch('main.db')
        self.mock_llm_handler_patcher = mock.patch('main.llm_handler')
        self.mock_x_poster_patcher = mock.patch('main.x_poster') # Verse of the Day posts to X
        self.mock_bible_parser_patcher = mock.patch('main.bible_parser') # For fallbacks

        self.mock_db = self.mock_db_patcher.start()
        self.mock_llm_handler = self.mock_llm_handler_patcher.start()
        self.mock_x_poster = self.mock_x_poster_patcher.start()
        self.mock_bible_parser = self.mock_bible_parser_patcher.start()

        # Mock specific firestore methods
        self.mock_doc_ref = mock.Mock()
        self.mock_doc_snapshot = mock.Mock()
        self.mock_db.collection.return_value.document.return_value = self.mock_doc_ref
        self.mock_doc_ref.get.return_value = self.mock_doc_snapshot
        self.mock_doc_ref.set = mock.Mock() # For cache writes

        # Mock LLM handler's method used by VoD
        self.mock_llm_handler.get_llm_bible_reference = mock.Mock()

        # Mock XPoster's method
        self.mock_x_poster.post_tweet = mock.Mock(return_value=True)

        # Mock BibleParser for fallback
        self.mock_bible_parser.get_random_verse = mock.Mock(return_value="Default fallback verse from parser.")


        # We need to import main AFTER some of these global mocks might be needed,
        # or ensure main.py is structured to allow late binding of db, llm_handler
        # For this exercise, we assume main.py's functions can be called with these patched globals.
        # This is a common challenge in testing Flask apps.
        # A cleaner way is to use app factories and pass configurations/mocks.
        # For now, we proceed with patching globals used by the endpoint.
        global main # Make main accessible for endpoint call
        import main
        self.app = main.app # Get the Flask app instance
        self.client = self.app.test_client() # Use test client for endpoint calls


    def tearDown(self):
        self.mock_db_patcher.stop()
        self.mock_llm_handler_patcher.stop()
        self.mock_x_poster_patcher.stop()
        self.mock_bible_parser_patcher.stop()
        # Ensure session is cleared if using Flask test client and session
        with self.client.session_transaction() as sess:
            sess.clear()


    def test_verse_of_the_day_cache_hit(self):
        cached_verse = "Cached verse from Firestore."
        cached_score = 10
        self.mock_doc_snapshot.exists = True
        self.mock_doc_snapshot.to_dict.return_value = {"response": cached_verse, "score": cached_score}

        with self.app.app_context(): # Ensure app context for logging, etc.
            response = self.client.get('/api/verse_of_the_day')

        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['response'], cached_verse)
        self.assertEqual(json_data['score'], cached_score)
        self.mock_llm_handler.get_llm_bible_reference.assert_not_called()
        self.mock_doc_ref.set.assert_not_called()
        self.mock_db.collection.assert_called_once_with("verse_of_the_day")


    def test_verse_of_the_day_cache_miss_llm_success(self):
        self.mock_doc_snapshot.exists = False # Cache miss
        llm_verse = "Fresh verse from LLM."
        llm_score = 9
        self.mock_llm_handler.get_llm_bible_reference.return_value = ({"response": llm_verse, "score": llm_score}, 200)

        with self.app.app_context():
             # Need to mock session for llm_handler.get_llm_bible_reference if it uses session
            with mock.patch('main.session', {}): # Mock Flask session
                response = self.client.get('/api/verse_of_the_day')

        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['response'], llm_verse)
        self.assertEqual(json_data['score'], llm_score)
        self.mock_llm_handler.get_llm_bible_reference.assert_called_once()
        self.mock_doc_ref.set.assert_called_once()
        # Assert specific data written to Firestore
        args, kwargs = self.mock_doc_ref.set.call_args
        self.assertEqual(args[0]['response'], llm_verse)
        self.assertEqual(args[0]['score'], llm_score)
        self.assertIn('timestamp', args[0]) # Check if timestamp is being set


    def test_verse_of_the_day_cache_miss_llm_fail_fallback_to_parser(self):
        self.mock_doc_snapshot.exists = False # Cache miss
        # LLM fails, e.g. returns error or empty
        self.mock_llm_handler.get_llm_bible_reference.return_value = ({"error": "LLM down"}, 500)
        fallback_verse_from_parser = "Fallback from BibleParser due to LLM failure."
        self.mock_bible_parser.get_random_verse.return_value = fallback_verse_from_parser

        with self.app.app_context():
            with mock.patch('main.session', {}):
                 response = self.client.get('/api/verse_of_the_day')

        self.assertEqual(response.status_code, 200) # Fallback should still be 200
        json_data = response.get_json()
        self.assertEqual(json_data['response'], fallback_verse_from_parser)
        self.assertIsNone(json_data.get('score')) # Fallback usually has no score
        self.mock_llm_handler.get_llm_bible_reference.assert_called_once()
        self.mock_doc_ref.set.assert_not_called() # Cache write should not happen on LLM failure
        self.mock_bible_parser.get_random_verse.assert_called_once()


class TestLLMSemanticCache(unittest.TestCase):
    def setUp(self):
        self.mock_openai_client = mock.Mock()
        self.mock_logger = mock.Mock()
        self.mock_bible_parser = mock.Mock()
        self.mock_firestore_db = mock.Mock()
        self.mock_embedding_model = mock.Mock()

        # LLMHandler instance with mocked dependencies
        self.llm_handler_instance = LLMHandler(
            client=self.mock_openai_client,
            logger=self.mock_logger,
            bible_parser=self.mock_bible_parser,
            model_name="test-model",
            db=self.mock_firestore_db,
            embedding_model=self.mock_embedding_model
        )

        # Mocking specific methods of dependencies
        self.sample_embedding = [0.1, 0.2, 0.3]
        # self.mock_embedding_model.encode.return_value.tolist.return_value = self.sample_embedding # Original
        mock_encode_result = mock.Mock()
        mock_encode_result.tolist.return_value = self.sample_embedding
        self.mock_embedding_model.encode.return_value = mock_encode_result


        self.mock_db_collection_ref = mock.Mock()
        self.mock_firestore_db.collection.return_value = self.mock_db_collection_ref

        self.mock_vector_query = mock.Mock()
        self.mock_db_collection_ref.find_nearest.return_value = self.mock_vector_query

        self.mock_llm_completion = mock.Mock()
        self.mock_llm_completion.choices = [mock.Mock()]
        self.mock_llm_completion.choices[0].message.content = json.dumps([{"ref": "John 3:16", "relevance": 10, "helpfulness": 10}])
        self.mock_llm_completion.usage.prompt_tokens = 10
        self.mock_llm_completion.usage.completion_tokens = 5
        self.mock_openai_client.chat.completions.create.return_value = self.mock_llm_completion

        self.mock_bible_parser.parse_reference.return_value = {"book": "John", "chapter_start": 3, "verse_start": 16}
        self.mock_bible_parser.get_passage.return_value = "For God so loved the world..."


    def test_llm_semantic_cache_hit(self):
        user_query = "test query for cache hit"
        cached_response_text = "Cached LLM response"
        cached_score = 15 # Example score

        mock_cached_doc = mock.Mock()
        mock_cached_doc.get.side_effect = lambda key: {"distance": 0.05, "response": cached_response_text, "score": cached_score}.get(key)
        mock_cached_doc.to_dict.return_value = {"response": cached_response_text, "score": cached_score}
        self.mock_vector_query.stream.return_value = [mock_cached_doc]

        # Mock session object for the call
        mock_session = {"conversation_history": []}

        result, status_code = self.llm_handler_instance.get_llm_bible_reference(mock_session, user_query)

        self.assertEqual(status_code, 200)
        self.assertEqual(result['response'], cached_response_text)
        self.assertEqual(result['score'], cached_score)
        self.mock_embedding_model.encode.assert_called_once_with(user_query)
        self.mock_firestore_db.collection.assert_called_once_with("llm_semantic_cache")
        self.mock_db_collection_ref.find_nearest.assert_called_once()
        self.mock_openai_client.chat.completions.create.assert_not_called()
        self.mock_db_collection_ref.add.assert_not_called()

    def test_llm_semantic_cache_miss_due_to_no_match(self):
        user_query = "new query, no match"
        self.mock_vector_query.stream.return_value = [] # No match in cache

        mock_session = {"conversation_history": []}
        result, status_code = self.llm_handler_instance.get_llm_bible_reference(mock_session, user_query)

        self.assertEqual(status_code, 200)
        self.assertEqual(result['response'], "For God so loved the world...") # From mocked LLM via bible_parser
        self.mock_embedding_model.encode.assert_called_once_with(user_query)
        self.mock_openai_client.chat.completions.create.assert_called_once()
        self.mock_db_collection_ref.add.assert_called_once()
        # Check data written to cache
        args, kwargs = self.mock_db_collection_ref.add.call_args
        self.assertEqual(args[0]['user_query'], user_query)
        self.assertEqual(args[0]['query_embedding'], self.sample_embedding)
        self.assertEqual(args[0]['response'], "For God so loved the world...")


    def test_llm_semantic_cache_miss_due_to_distance_threshold(self):
        user_query = "query with far match"
        mock_far_doc = mock.Mock()
        # Distance is 0.2, threshold is 0.1
        mock_far_doc.get.side_effect = lambda key: {"distance": 0.2, "response": "Far response", "score": 5}.get(key)
        self.mock_vector_query.stream.return_value = [mock_far_doc]

        mock_session = {"conversation_history": []}
        result, status_code = self.llm_handler_instance.get_llm_bible_reference(mock_session, user_query)

        self.assertEqual(status_code, 200)
        self.assertEqual(result['response'], "For God so loved the world...")
        self.mock_embedding_model.encode.assert_called_once_with(user_query)
        self.mock_openai_client.chat.completions.create.assert_called_once()
        self.mock_db_collection_ref.add.assert_called_once()
        args, kwargs = self.mock_db_collection_ref.add.call_args
        self.assertEqual(args[0]['user_query'], user_query)


    def test_llm_semantic_cache_firestore_unavailable_fallback(self):
        user_query = "query when firestore is down"
        # Simulate Firestore being unavailable in two ways:
        # 1. self.llm_handler_instance.db is None
        original_db = self.llm_handler_instance.db
        self.llm_handler_instance.db = None

        mock_session = {"conversation_history": []}
        result, status_code = self.llm_handler_instance.get_llm_bible_reference(mock_session, user_query)

        self.assertEqual(status_code, 200)
        self.assertEqual(result['response'], "For God so loved the world...")
        # Embedding model might still be called if db is None but model is available (current logic)
        # The cache check is `if self.db and self.embedding_model:`. If db is None, it skips.
        self.mock_embedding_model.encode.assert_not_called() # Because the whole block is skipped
        self.mock_openai_client.chat.completions.create.assert_called_once()
        self.mock_db_collection_ref.add.assert_not_called() # Write is also skipped

        # Reset db for other tests
        self.llm_handler_instance.db = original_db

        # 2. Firestore call raises an exception
        self.mock_firestore_db.collection.side_effect = Exception("Firestore unavailable")
        # Clear previous call counts for create and add
        self.mock_openai_client.chat.completions.create.reset_mock()
        self.mock_db_collection_ref.add.reset_mock()
        self.mock_embedding_model.encode.reset_mock()


        mock_session_2 = {"conversation_history": []}
        result, status_code = self.llm_handler_instance.get_llm_bible_reference(mock_session_2, user_query + " 2")

        self.assertEqual(status_code, 200)
        self.assertEqual(result['response'], "For God so loved the world...")
        self.mock_embedding_model.encode.assert_called_once_with(user_query + " 2") # encode is called before firestore exception
        self.mock_openai_client.chat.completions.create.assert_called_once()
        self.mock_db_collection_ref.add.assert_not_called() # Write is skipped due to earlier error or lack of embedding


if __name__ == '__main__':
    unittest.main()
