import os  # Still needed for FLASK_SECRET_KEY and os.urandom
import datetime
import holidays
from flask import Flask, render_template, session
from flask_restx import Api, Resource, fields
from dotenv import load_dotenv
from openai import OpenAI
from random_seeder import RandomSeeder
from bible_parser import BibleParser
from llm_handler import LLMHandler  # Import the new LLMHandler class

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

# Initialize the random number generator at application startup
seeder = RandomSeeder(app.logger)
seeder.initialize_seeding()

# Initialize BibleParser
bible_parser = BibleParser(app.logger)

# Initialize LLMHandler
llm_handler = LLMHandler(
    client, app.logger, bible_parser, "deepseek/deepseek-chat-v3-0324:free"
)


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
        try:
            today = datetime.date.today()
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
                app.logger.info(f"Successfully fetched verse of the day from LLM: {result.get('response')[:100]}...")
                return result, 200
            else:
                error_msg = result.get('error', 'Unknown error from LLM')
                app.logger.error(f"LLM query for verse of the day failed (status {status_code}, error: {error_msg}). Falling back.")
                # Fallback logic:
                verse_text = bible_parser.get_random_verse()
                if verse_text is None:
                    app.logger.info("Fallback get_random_verse() returned None, using ultimate fallback verse.")
                    fallback_verse = "In the beginning God created the heaven and the earth. - Genesis 1:1"
                    return {"response": fallback_verse, "score": None}, 200
                app.logger.info(f"Fallback random verse: {verse_text[:100]}...")
                return {"response": verse_text, "score": None}, 200

        except Exception as e:
            app.logger.error(f"Unexpected error in VerseOfTheDayEndpoint: {e}", exc_info=True)
            # Ultimate fallback in case of any unexpected error
            app.logger.info("Unexpected error, using ultimate fallback verse.")
            fallback_verse = "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life. – John 3:16"
            return {"response": fallback_verse, "score": None}, 500


if __name__ == "__main__":
    app.run(debug=True)
