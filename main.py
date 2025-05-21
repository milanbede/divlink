import os  # Still needed for FLASK_SECRET_KEY and os.urandom
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

response_model = api.model(
    "LLMResponse",
    {
        "response": fields.String(description="Bible passage text"),
        "score": fields.Integer(
            description="Combined relevance+helpfulness score", allow_null=True
        ),
        "latency_ms": fields.Float(description="LLM latency in ms", allow_null=True),
        "prompt_tokens": fields.Integer(
            description="Prompt token count", allow_null=True
        ),
        "completion_tokens": fields.Integer(
            description="Completion token count", allow_null=True
        ),
    },
)
# --------------------------------

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
    @api.marshal_with(response_model)
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
    @api.marshal_with(response_model)
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


if __name__ == "__main__":
    app.run(debug=True)
