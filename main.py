import os  # Still needed for FLASK_SECRET_KEY and os.urandom
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from openai import (
    OpenAI,
    # APIError, APIConnectionError, RateLimitError, APITimeoutError are now handled in LLMHandler
)  # OpenAI SDK
from random_seeder import RandomSeeder
from bible_parser import BibleParser
from llm_handler import LLMHandler  # Import the new LLMHandler class

load_dotenv()  # Load variables from .env file

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY", os.urandom(24)
)  # Needed for session management

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


@app.route("/query", methods=["POST"])
def query_llm():
    user_query = request.json.get("query")
    if not user_query:
        return jsonify({"error": "No query provided."}), 400

    # Delegate to LLMHandler
    # The handler will manage session history internally.
    result, status_code = llm_handler.get_llm_bible_reference(session, user_query)

    return jsonify(result), status_code


# The main LLM interaction logic, including prompt definition, history management,
# API calls, retries, JSON parsing, and error handling, has been moved to LLMHandler.
# The old try block content is now inside the loop in the REPLACE section above.
# This SEARCH block is to remove the old structure.
# The outer exception handlers (HTTPError, RequestException, etc.) are now part of the loop structure.


@app.route("/random_psalm", methods=["GET"])
def random_psalm():
    passage_text = bible_parser.get_random_psalm_passage()

    if passage_text is None:
        app.logger.error("Failed to retrieve a random Psalm. Serving a fallback verse.")
        fallback_verse = "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.\n- John 3:16"
        return jsonify({"response": fallback_verse, "score": None}), 200

    # If no error, passage_text contains the Psalm
    # The logger message for success is now inside BibleParser.get_random_psalm_passage()
    return jsonify(
        {"response": passage_text, "score": None}
    )  # Score is null as it's not an LLM eval


if __name__ == "__main__":
    app.run(debug=True)
