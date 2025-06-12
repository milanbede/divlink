import os  # Still needed for FLASK_SECRET_KEY and os.urandom
import datetime
import holidays
from flask import Flask, render_template, session
from flask_restx import Api, Resource, fields
from dotenv import load_dotenv
from google.cloud import firestore # Add Firestore import
from openai import OpenAI
from sentence_transformers import SentenceTransformer # Add SentenceTransformer import
from random_seeder import RandomSeeder
from bible_parser import BibleParser
from llm_handler import LLMHandler  # Import the new LLMHandler class
from x_poster import XPoster # Import XPoster

load_dotenv()  # Load variables from .env file

app = Flask(__name__, static_url_path="/static")
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY", os.urandom(24)
)  # Needed for session management

# ---- Flask-RESTX API setup ----
api = Api(
    app,
    version="1.0",
    title="Bible Reference API",
    description="Ask for relevant Bible verses via LLM or fetch a random Psalm",
    prefix="/api",  # Set the API prefix
    doc="/docs",  # Swagger UI served at /api/docs
)

query_model = api.model(
    "Query",
    {
        "query": fields.String(required=True, description="Your spiritual question"),
    },
)

# Model for responses that primarily return a Bible passage and an optional score
PassageResponseModel = api.model(
    "PassageResponse",
    {
        "response": fields.String(description="Bible passage text or fallback message"),
        "score": fields.Integer(
            description="Combined relevance+helpfulness score", allow_null=True
        ),
    },
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize OpenAI client for OpenRouter
if OPENROUTER_API_KEY:
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
else:
    app.logger.error(
        "OPENROUTER_API_KEY not found in .env file. LLM functionality will be disabled."
    )
    client = None  # Explicitly set client to None if key is missing

# Initialize Firestore client
try:
    db = firestore.Client()
    app.logger.info("Firestore client initialized successfully.")
except Exception as e:
    app.logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)
    db = None # Ensure db is None if initialization fails

# Initialize Sentence Transformer model
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    app.logger.info("SentenceTransformer model initialized successfully.")
except Exception as e:
    app.logger.error(f"Failed to initialize SentenceTransformer model: {e}", exc_info=True)
    embedding_model = None # Ensure embedding_model is None if initialization fails

# Initialize the random number generator at application startup
seeder = RandomSeeder(app.logger)
seeder.initialize_seeding()

# Initialize BibleParser
bible_parser = BibleParser(app.logger)

# Initialize LLMHandler
llm_handler = LLMHandler(
    client, app.logger, bible_parser, "deepseek/deepseek-chat-v3-0324:free", db, embedding_model
)

# Initialize XPoster
x_poster = XPoster()


@app.route("/")
def index():
    return render_template("index.html")


@api.route("/query")
class QueryEndpoint(Resource):
    @api.expect(query_model)
    @api.marshal_with(PassageResponseModel)  # Documents the full response structure
    def post(self):
        """Ask for a Bible reference by natural‐language query"""
        user_query = api.payload.get("query")
        if not user_query:
            api.abort(400, "No query provided.")

        result, status_code = llm_handler.get_llm_bible_reference(session, user_query)

        if status_code != 200:
            app.logger.error(
                f"LLM query failed (status {status_code}), falling back to random Psalm."
            )
            passage_text = bible_parser.get_random_psalm_passage()
            if passage_text is None:
                fallback_verse = (
                    "For God so loved the world, that he gave his only begotten Son, "
                    "that whosoever believeth in him should not perish, but have everlasting life. – John 3:16"
                )
                return {"response": fallback_verse, "score": None}, 200
            return {"response": passage_text, "score": None}, 200

        return result, status_code


@api.route("/random_psalm")
class RandomPsalmEndpoint(Resource):
    @api.marshal_with(PassageResponseModel)  # Uses the model for passage responses
    def get(self):
        """Get a random curated powerful Psalm"""
        passage_text = bible_parser.get_random_psalm_passage()
        if passage_text is None:
            fallback_verse = (
                "For God so loved the world, that he gave his only begotten Son, "
                "that whosoever believeth in him should not perish, but have everlasting life. – John 3:16"
            )
            return {"response": fallback_verse, "score": None}, 200
        return {"response": passage_text, "score": None}, 200


@api.route("/verse_of_the_day")
class VerseOfTheDayEndpoint(Resource):
    @api.marshal_with(PassageResponseModel)
    def get(self):
        """Get a verse of the day, querying LLM based on current date and holidays."""
        today = datetime.date.today()
        today_doc_id = today.strftime("%Y-%m-%d")
        collection_name = "verse_of_the_day"

        # Attempt to fetch from Firestore cache
        if db: # Check if Firestore client is available
            try:
                doc_ref = db.collection(collection_name).document(today_doc_id)
                doc = doc_ref.get()
                if doc.exists:
                    cached_data = doc.to_dict()
                    app.logger.info(f"Cache hit for Verse of the Day: {today_doc_id}. Data: {cached_data.get('response')[:50]}...")
                    # Ensure response format matches PassageResponseModel
                    return {"response": cached_data.get("response"), "score": cached_data.get("score")}, 200
                else:
                    app.logger.info(f"Cache miss for Verse of the Day: {today_doc_id}")
            except Exception as e:
                app.logger.error(f"Error accessing Firestore cache for {today_doc_id}: {e}", exc_info=True)
        else:
            app.logger.warn("Firestore client (db) not available, skipping cache check for Verse of the Day.")

        # Cache miss or Firestore unavailable, proceed to generate verse
        try:
            # For simplicity, using US holidays. This could be made configurable.
            # Also, note that most Christian holidays recognized by the 'holidays' library
            # are based on Western Christian traditions by default.
            # Common non-country specific Christian holidays are often part of general Christian calendars.
            # For broader Christian holiday coverage, one might need a more specialized calendar
            # or check multiple country calendars if the user base is diverse.
            # Example: us_holidays = holidays.US()
            # Example: ChristianHolidays = holidays.registry.ChristianHolidays # This might not be directly usable as a class

            # Let's try a specific country known for observing many Christian holidays,
            # or rely on a common set if available.
            # For now, we'll use a placeholder for holiday checking.
            # A more robust solution would involve selecting an appropriate calendar.
            # For example, holidays.CountryHoliday('US', prov=None, state=None, years=today.year)
            # Some holiday libraries allow creating custom holiday sets.

            # Using a specific country's calendar that includes Christian holidays:
            # For example, Poland (PL) has many Christian holidays.
            country_holidays = holidays.CountryHoliday('PL', years=today.year) # Using Poland as an example for Christian holidays

            today_str = today.strftime("%B %d, %Y")
            holiday_name = country_holidays.get(today)

            query = f"Select a single verse from the King James Bible that offers strength, hope, or encouragement for {today_str}"
            if holiday_name:
                query += f", especially considering today is {holiday_name}."
            else:
                query += "."

            app.logger.info(f"Constructed Verse of the Day query: {query}")

            # Ensure llm_handler and session are available as they are in other endpoints
            result, status_code = llm_handler.get_llm_bible_reference(session, query)

            if status_code == 200 and result.get('response'):
                verse_to_tweet = result.get('response')
                score = result.get('score')
                app.logger.info(f"Successfully fetched verse of the day from LLM: {verse_to_tweet[:100]}...")

                # Attempt to post to X
                if x_poster.post_tweet(verse_to_tweet):
                    app.logger.info("Verse of the day posted to X successfully.")
                else:
                    app.logger.error("Failed to post verse of the day to X.")

                # Store in Firestore cache
                if db:
                    try:
                        doc_ref = db.collection(collection_name).document(today_doc_id)
                        data_to_store = {
                            'response': verse_to_tweet,
                            'score': score,
                            'timestamp': firestore.SERVER_TIMESTAMP
                        }
                        doc_ref.set(data_to_store)
                        app.logger.info(f"Verse of the Day {today_doc_id} cached successfully in Firestore. Data: {verse_to_tweet[:50]}...")
                    except Exception as e:
                        app.logger.error(f"Error caching Verse of the Day {today_doc_id} to Firestore: {e}", exc_info=True)
                else:
                    app.logger.warn(f"Firestore client (db) not available, skipping cache write for Verse of the Day {today_doc_id}.")

                return result, 200
            else:
                error_msg = result.get('error', 'Unknown error from LLM')
                app.logger.error(f"LLM query for verse of the day failed (status {status_code}, error: {error_msg}). Falling back.")
                # Fallback logic:
                verse_to_tweet = bible_parser.get_random_verse()
                if verse_to_tweet is None:
                    app.logger.info("Fallback get_random_verse() returned None, using ultimate fallback verse.")
                    verse_to_tweet = "In the beginning God created the heaven and the earth. - Genesis 1:1"
                    # Attempt to post ultimate fallback verse to X
                    if x_poster.post_tweet(verse_to_tweet):
                        app.logger.info("Ultimate fallback verse of the day posted to X successfully.")
                    else:
                        app.logger.error("Failed to post ultimate fallback verse of the day to X.")
                    return {"response": verse_to_tweet, "score": None}, 200

                # Attempt to post fallback verse to X
                if x_poster.post_tweet(verse_to_tweet):
                    app.logger.info("Fallback random verse of the day posted to X successfully.")
                else:
                    app.logger.error("Failed to post fallback random verse of the day to X.")
                app.logger.info(f"Fallback random verse: {verse_to_tweet[:100]}...")
                return {"response": verse_to_tweet, "score": None}, 200

        except Exception as e:
            app.logger.error(f"Unexpected error in VerseOfTheDayEndpoint: {e}", exc_info=True)
            # Ultimate fallback in case of any unexpected error
            app.logger.info("Unexpected error, using ultimate fallback verse.")
            verse_to_tweet = "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life. – John 3:16"
            # Attempt to post this fallback to X as well
            if x_poster.post_tweet(verse_to_tweet):
                app.logger.info("General error fallback verse posted to X successfully.")
            else:
                app.logger.error("Failed to post general error fallback verse to X.")
            return {"response": verse_to_tweet, "score": None}, 500


if __name__ == "__main__":
    app.run(debug=True)
