import os  # Still needed for FLASK_SECRET_KEY and os.urandom
import asyncio
from flask import Flask, render_template, session, request, jsonify
from flask_restx import Api, Resource, fields
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Bot, Update
from random_seeder import RandomSeeder
from bible_parser import BibleParser
from llm_handler import LLMHandler  # Import the new LLMHandler class
from telegram_handler import TelegramHandler
from telegram_session import TelegramSessionManager

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
        "version": fields.String(
            required=False,
            description="Bible version: 'kjv' or 'szit'",
            enum=["kjv", "szit"],
        ),
    },
)

version_model = api.model(
    "Version",
    {
        "version": fields.String(
            required=False,
            description="Bible version: 'kjv' or 'szit'",
            enum=["kjv", "szit"],
        ),
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
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Initialize OpenAI client for OpenRouter
if OPENROUTER_API_KEY:
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
else:
    app.logger.error(
        "OPENROUTER_API_KEY not found in .env file. LLM functionality will be disabled."
    )
    client = None  # Explicitly set client to None if key is missing

# Initialize Telegram bot
telegram_bot = None
telegram_handler = None
telegram_session_manager = None

if TELEGRAM_BOT_TOKEN:
    try:
        telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
        telegram_session_manager = TelegramSessionManager(app.logger)
        app.logger.info("Telegram bot initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize Telegram bot: {e}")
        telegram_bot = None
else:
    app.logger.warning(
        "TELEGRAM_BOT_TOKEN not found in .env file. Telegram bot functionality will be disabled."
    )

# Initialize the random number generator at application startup
seeder = RandomSeeder(app.logger)
seeder.initialize_seeding()

# Initialize BibleParser
bible_parser = BibleParser(app.logger)

# Initialize LLMHandler
llm_handler = LLMHandler(
    client, app.logger, bible_parser, "deepseek/deepseek-chat-v3-0324:free"
)

# Initialize Telegram handler after all components are ready
if telegram_bot and telegram_session_manager:
    telegram_handler = TelegramHandler(
        telegram_bot, app.logger, llm_handler, bible_parser, telegram_session_manager
    )


def get_default_bible_version():
    """Detect default Bible version from browser language preferences."""
    accept_lang = request.headers.get("Accept-Language", "").lower()
    return "szit" if "hu" in accept_lang else "kjv"


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

        # Get Bible version from payload or detect from browser
        bible_version = api.payload.get("version", get_default_bible_version())

        # Store version in session for consistency
        session["bible_version"] = bible_version

        result, status_code = llm_handler.get_llm_bible_reference(
            session, user_query, bible_version
        )

        if status_code != 200:
            app.logger.error(
                f"LLM query failed (status {status_code}), falling back to random Psalm."
            )
            # Create version-specific parser for fallback
            from bible_parser import BibleParser

            fallback_parser = BibleParser(app.logger, bible_version=bible_version)
            passage_text = fallback_parser.get_random_psalm_passage()
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
        # Get Bible version from query parameter or detect from browser
        bible_version = request.args.get("version", get_default_bible_version())

        # Store version in session for consistency
        session["bible_version"] = bible_version

        # Create version-specific parser
        from bible_parser import BibleParser

        version_parser = BibleParser(app.logger, bible_version=bible_version)
        passage_text = version_parser.get_random_psalm_passage()
        if passage_text is None:
            fallback_verse = (
                "For God so loved the world, that he gave his only begotten Son, "
                "that whosoever believeth in him should not perish, but have everlasting life. – John 3:16"
            )
            return {"response": fallback_verse, "score": None}, 200
        return {"response": passage_text, "score": None}, 200

    @api.expect(version_model)
    @api.marshal_with(PassageResponseModel)
    def post(self):
        """Get a random curated powerful Psalm (POST version for consistency)"""
        # Get Bible version from payload or detect from browser
        bible_version = (
            api.payload.get("version", get_default_bible_version())
            if api.payload
            else get_default_bible_version()
        )

        # Store version in session for consistency
        session["bible_version"] = bible_version

        # Create version-specific parser
        from bible_parser import BibleParser

        version_parser = BibleParser(app.logger, bible_version=bible_version)
        passage_text = version_parser.get_random_psalm_passage()
        if passage_text is None:
            fallback_verse = (
                "For God so loved the world, that he gave his only begotten Son, "
                "that whosoever believeth in him should not perish, but have everlasting life. – John 3:16"
            )
            return {"response": fallback_verse, "score": None}, 200
        return {"response": passage_text, "score": None}, 200


# Telegram webhook endpoints
@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    """Handle incoming Telegram webhook updates"""
    if not telegram_handler:
        app.logger.error("Telegram handler not initialized")
        return "Telegram bot not configured", 503

    try:
        # Get the update from Telegram
        update_data = request.get_json()
        if not update_data:
            return "No data received", 400

        # Create Update object
        update = Update.de_json(update_data, telegram_bot)
        if not update:
            return "Invalid update format", 400

        # Process the update asynchronously
        asyncio.create_task(telegram_handler.process_message(update))

        return "OK", 200

    except Exception as e:
        app.logger.error(f"Error processing Telegram webhook: {e}")
        return "Error processing update", 500


@app.route("/telegram/set-webhook", methods=["POST"])
def set_telegram_webhook():
    """Set webhook URL for Telegram bot (for development/deployment)"""
    if not telegram_bot:
        return jsonify({"error": "Telegram bot not configured"}), 503

    try:
        webhook_url = request.json.get("webhook_url")
        if not webhook_url:
            return jsonify({"error": "webhook_url required"}), 400

        # Set the webhook
        asyncio.create_task(telegram_bot.set_webhook(url=webhook_url))

        return (
            jsonify({"success": True, "message": f"Webhook set to {webhook_url}"}),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error setting webhook: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/telegram/webhook-info", methods=["GET"])
def get_webhook_info():
    """Get current webhook information"""
    if not telegram_bot:
        return jsonify({"error": "Telegram bot not configured"}), 503

    try:

        async def get_info():
            return await telegram_bot.get_webhook_info()

        webhook_info = asyncio.run(get_info())

        return (
            jsonify(
                {
                    "url": webhook_info.url,
                    "has_custom_certificate": webhook_info.has_custom_certificate,
                    "pending_update_count": webhook_info.pending_update_count,
                    "last_error_date": (
                        webhook_info.last_error_date.isoformat()
                        if webhook_info.last_error_date
                        else None
                    ),
                    "last_error_message": webhook_info.last_error_message,
                    "max_connections": webhook_info.max_connections,
                    "allowed_updates": webhook_info.allowed_updates,
                }
            ),
            200,
        )

    except Exception as e:
        app.logger.error(f"Error getting webhook info: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
