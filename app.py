import os

# import requests # No longer needed
import json
import re  # For parsing Bible references
import random  # For selecting a random reference
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
)  # OpenAI SDK

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

# Load Bible data and create a lookup map
BIBLE_DATA = []
BOOK_MAP = {}
try:
    # Adjust the path if your data directory is elsewhere relative to app.py
    bible_file_path = os.path.join(os.path.dirname(__file__), "data", "en_kjv.json")
    if not os.path.exists(bible_file_path):
        # Fallback for common execution from project root if app is in a subdirectory
        bible_file_path_alt = os.path.join(os.getcwd(), "data", "en_kjv.json")
        if os.path.exists(bible_file_path_alt):
            bible_file_path = bible_file_path_alt
        else:
            raise FileNotFoundError(
                f"Bible data file not found at {bible_file_path} or {bible_file_path_alt}"
            )

    with open(bible_file_path, "r", encoding="utf-8") as f:
        BIBLE_DATA = json.load(f)

    for i, book_data_item in enumerate(BIBLE_DATA):
        BOOK_MAP[book_data_item["name"].lower()] = i
        BOOK_MAP[book_data_item["abbrev"].lower()] = i
        # Example: if abbrev is "psa", also map "psalm" and "psalms" if name is "Psalms"
        if book_data_item["name"].lower() == "psalms":
            BOOK_MAP["psalm"] = i


except FileNotFoundError as e:
    app.logger.error(f"Bible data file (data/en_kjv.json) not found. {e}")
except json.JSONDecodeError:
    app.logger.error("Error decoding Bible data JSON (data/en_kjv.json).")
except Exception as e:
    app.logger.error(f"An unexpected error occurred loading Bible data: {e}")


@app.route("/")
def index():
    return render_template("index.html")


def parse_bible_reference(reference_str):
    """
    Parses a Bible reference string into its components.
    Handles "Book Chapter:Verse", "Book Chapter:Verse-Verse", "Book Chapter".
    """
    # Regex to capture book name (can include numbers and spaces), chapter, start_verse, and optional end_verse
    match = re.match(
        r"^(.*?)\s*(\d+)(?:\s*:\s*(\d+)(?:\s*-\s*(\d+))?)?$", reference_str.strip()
    )

    if not match:
        app.logger.info(f"Could not parse reference string: {reference_str}")
        return None

    book_name_str = match.group(1).strip()
    chapter_str = match.group(2)
    start_verse_str = match.group(3)
    end_verse_str = match.group(4)

    try:
        parsed_ref = {
            "book_name": book_name_str,
            "chapter": int(chapter_str),
            "start_verse": int(start_verse_str) if start_verse_str else None,
            "end_verse": (
                int(end_verse_str)
                if end_verse_str
                else (int(start_verse_str) if start_verse_str else None)
            ),
        }
        # If only chapter is given, start_verse and end_verse will be None.
        # If only start_verse is given (e.g. "John 3:16"), end_verse is set to start_verse.
        return parsed_ref
    except ValueError:  # Should not happen if regex matches digits correctly
        app.logger.error(f"ValueError parsing numbers in reference: {reference_str}")
        return None


def get_passage_from_json(parsed_ref):
    """
    Retrieves and formats Bible passage text from the loaded JSON data.
    """
    if not BIBLE_DATA or not BOOK_MAP:
        return "Error: Bible data not loaded on the server."

    book_name_key = parsed_ref["book_name"].lower()
    book_index = BOOK_MAP.get(book_name_key)

    # Simple fuzzy matching for book names
    if book_index is None:
        if book_name_key.endswith("s") and BOOK_MAP.get(book_name_key[:-1]) is not None:
            book_index = BOOK_MAP.get(book_name_key[:-1])
        elif (
            not book_name_key.endswith("s")
            and BOOK_MAP.get(book_name_key + "s") is not None
        ):
            book_index = BOOK_MAP.get(book_name_key + "s")

        if book_index is None:  # Still not found
            return f"Book '{parsed_ref['book_name']}' not found. Please check spelling or try a standard abbreviation (e.g., Gen, Exo, Psa, Mat, Rom)."

    book_data = BIBLE_DATA[book_index]

    chapter_num = parsed_ref["chapter"]
    chapter_index = chapter_num - 1  # Adjust for 0-based list index

    if not (0 <= chapter_index < len(book_data["chapters"])):
        return f"Chapter {chapter_num} not found in {book_data['name']} (max: {len(book_data['chapters'])})."

    chapter_verses_list = book_data["chapters"][chapter_index]

    start_verse = parsed_ref["start_verse"]
    end_verse = parsed_ref["end_verse"]

    passage_texts = []
    output_reference_display = f"{book_data['name']} {chapter_num}"

    if start_verse is None:  # Whole chapter
        for i, verse_text in enumerate(chapter_verses_list):
            cleaned_verse_text = re.sub(r"\{.*?\}", "", verse_text).strip()
            passage_texts.append(f"{i+1} {cleaned_verse_text}")
    else:
        start_verse_index = start_verse - 1  # Adjust for 0-based list index
        end_verse_index = (
            (end_verse - 1) if end_verse is not None else start_verse_index
        )

        if not (0 <= start_verse_index < len(chapter_verses_list)):
            return f"Start verse {start_verse} not found in {book_data['name']} chapter {chapter_num} (max: {len(chapter_verses_list)})."
        if (
            not (0 <= end_verse_index < len(chapter_verses_list))
            or end_verse_index < start_verse_index
        ):
            return f"End verse {end_verse} is invalid for {book_data['name']} chapter {chapter_num}."

        for i in range(start_verse_index, end_verse_index + 1):
            verse_text = chapter_verses_list[i]
            cleaned_verse_text = re.sub(r"\{.*?\}", "", verse_text).strip()
            passage_texts.append(f"{i+1} {cleaned_verse_text}")

        if start_verse == end_verse:
            output_reference_display += f":{start_verse}"
        else:
            output_reference_display += f":{start_verse}-{end_verse}"

    if not passage_texts:
        return f"No verses found for '{parsed_ref['book_name']} {chapter_num}:{start_verse if start_verse else ''}{'-'+str(end_verse) if end_verse and end_verse != start_verse else ''}'."

    full_passage_text = "\n".join(passage_texts)
    return f"{output_reference_display}\n{full_passage_text}"


@app.route("/query", methods=["POST"])
def query_llm():
    if not client:  # Check if OpenAI client was initialized
        app.logger.error("OpenAI client not initialized. Check OPENROUTER_API_KEY.")
        return jsonify({"error": "LLM service is not configured on the server."}), 500

    user_query = request.json.get("query")
    if not user_query:
        return jsonify({"error": "No query provided."}), 400

    base_prompt_text = """You are a Bible reference guide trained to help people find direct, relevant verses from the Bible that speak to their questions, challenges, or sins. You do not paraphrase, interpret, or soften God’s Word.

Your role is to return a JSON object containing a list of specific Bible references. The JSON object should have a single key "references", and its value should be a list of strings, where each string is a Bible reference (e.g., "Proverbs 3:5-6" or "Matthew 10:34"). Provide up to 3 relevant references. Do not include any commentary or other text outside the JSON object.

Assume the person is seeking real truth, not feel-good platitudes. Prioritize verses that reflect:
	•	The fear of the Lord
	•	Repentance, conviction, and God’s justice
	•	Faith, wisdom, and obedience
	•	Boldness, self-denial, and spiritual warfare

Use only Scripture. Avoid emotional reassurance or modern therapeutic language. The Bible is sufficient. If the input is unclear, choose verses that most directly address the spiritual root of the query.

Example:

Input: "I feel like giving up."
Output:
{"references": ["Galatians 6:9", "Isaiah 40:31", "2 Corinthians 4:16-18"]}

Input: "Is homosexuality really a sin?"
Output:
{"references": ["Romans 1:26-27", "1 Corinthians 6:9-10", "Leviticus 18:22"]}

Begin."""

    # Initialize or retrieve conversation history from session
    if "conversation_history" not in session:
        session["conversation_history"] = [
            {"role": "system", "content": base_prompt_text}
        ]

    # Add current user query to history
    # Simple cap on history length to prevent it from growing too large
    MAX_HISTORY_PAIRS = 5  # Number of user/assistant message pairs
    current_history = list(session["conversation_history"])  # Work with a copy
    current_history.append({"role": "user", "content": user_query})

    if len(current_history) > (MAX_HISTORY_PAIRS * 2 + 1):  # +1 for system prompt
        # Keep system prompt and last MAX_HISTORY_PAIRS exchanges
        current_history = [current_history[0]] + current_history[
            -(MAX_HISTORY_PAIRS * 2) :
        ]

    # The 'prompt' variable is no longer directly used for the API call messages.
    # The 'current_history' list serves as the messages payload.

    max_retries = 3
    raw_llm_output = (
        None  # Initialize to ensure it's defined for history append on failure
    )

    for attempt in range(max_retries):
        try:
            app.logger.info(
                f"Attempt {attempt + 1} for query: '{user_query}'. History length: {len(current_history)}"
            )

            completion = client.chat.completions.create(
                model="deepseek/deepseek-r1-distill-qwen-32b:free",  # Or your chosen model
                messages=current_history,
                # temperature=0.7, # Optional: Adjust creativity
            )

            raw_llm_output = (
                completion.choices[0].message.content if completion.choices else ""
            )

            if not raw_llm_output or not raw_llm_output.strip():
                app.logger.warn(
                    f"LLM returned empty content on attempt {attempt + 1} for query: '{user_query}'. Raw response: '{raw_llm_output}'"
                )
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    session["conversation_history"] = current_history  # Save user query
                    if raw_llm_output is not None:  # Check if raw_llm_output was set
                        session["conversation_history"].append(
                            {"role": "assistant", "content": raw_llm_output}
                        )  # Save empty assistant response
                    session.modified = True
                    return jsonify(
                        {
                            "response": "LLM returned an empty response after multiple attempts. Please try rephrasing."
                        }
                    )

            try:
                # Attempt to parse the LLM output as JSON
                parsed_json = json.loads(raw_llm_output)
                references_list = parsed_json.get("references")

                if (
                    not references_list
                    or not isinstance(references_list, list)
                    or not all(isinstance(ref, str) for ref in references_list)
                ):
                    app.logger.warn(
                        f"LLM response JSON did not contain a valid 'references' list of strings on attempt {attempt + 1}. Query: '{user_query}'. Raw output: '{raw_llm_output}'"
                    )
                    if attempt < max_retries - 1:
                        continue  # Retry
                    else:
                        session["conversation_history"] = (
                            current_history  # Save user query
                        )
                        session["conversation_history"].append(
                            {"role": "assistant", "content": raw_llm_output}
                        )  # Save problematic assistant response
                        session.modified = True
                        return jsonify(
                            {
                                "response": "Could not extract a valid list of passage references from LLM after multiple attempts. Please try again."
                            }
                        )

                if not references_list:  # Empty list of references
                    app.logger.warn(
                        f"LLM returned an empty list of references on attempt {attempt + 1}. Query: '{user_query}'. Raw output: '{raw_llm_output}'"
                    )
                    if attempt < max_retries - 1:
                        continue  # Retry
                    else:
                        session["conversation_history"] = (
                            current_history  # Save user query
                        )
                        session["conversation_history"].append(
                            {"role": "assistant", "content": raw_llm_output}
                        )  # Save empty list response
                        session.modified = True
                        return jsonify(
                            {
                                "response": "LLM did not provide any Bible references for your query after multiple attempts. Please try rephrasing."
                            }
                        )

                # Randomly select one reference from the list
                passage_reference = random.choice(references_list)
                app.logger.info(
                    f"Randomly selected reference: '{passage_reference}' from LLM output: {references_list} for query: '{user_query}'"
                )

                # Successfully got a passage_reference, now parse it and get text
                parsed_ref = parse_bible_reference(passage_reference)
                if not parsed_ref:
                    app.logger.warn(
                        f"Could not parse the selected LLM reference: '{passage_reference}' for query: '{user_query}'. LLM raw output: '{raw_llm_output}'"
                    )
                    session["conversation_history"] = current_history
                    session["conversation_history"].append(
                        {"role": "assistant", "content": raw_llm_output}
                    )  # Save original LLM output
                    session.modified = True
                    return jsonify(
                        {
                            "response": f"Could not understand the selected Bible reference: '{passage_reference}'. Please try rephrasing your query."
                        }
                    )

                passage_text = get_passage_from_json(parsed_ref)

                # Check if get_passage_from_json returned an error message
                lookup_error_prefixes = (
                    "Error: Bible data not loaded",
                    "Book '",
                    "Chapter ",  # e.g., "Chapter 5 not found..."
                    "Start verse ",
                    "End verse ",
                    "No verses found for '",
                )
                is_lookup_error = False
                if isinstance(
                    passage_text, str
                ):  # Ensure it's a string before checking prefixes
                    for prefix in lookup_error_prefixes:
                        if passage_text.startswith(prefix):
                            # More specific check for "Chapter ", "Start verse ", "End verse "
                            if prefix in ["Chapter ", "Start verse ", "End verse "]:
                                if (
                                    "not found" in passage_text
                                    or "is invalid" in passage_text
                                ):
                                    is_lookup_error = True
                                    break
                            else:  # For other prefixes, the prefix itself is enough
                                is_lookup_error = True
                                break

                if is_lookup_error:
                    app.logger.error(
                        f"Bible lookup error for LLM reference '{passage_reference}': {passage_text}. Query: '{user_query}'. LLM raw output: '{raw_llm_output}'"
                    )
                    session["conversation_history"] = current_history
                    session["conversation_history"].append(
                        {"role": "assistant", "content": raw_llm_output}
                    )  # Save original LLM output
                    session.modified = True
                    return jsonify(
                        {
                            "response": "I received a Bible reference, but it appears to be invalid (e.g., chapter or verse out of range). Please try rephrasing your query."
                        }
                    )
                else:
                    # Successfully retrieved passage text
                    session["conversation_history"] = current_history  # Save user query
                    session["conversation_history"].append(
                        {"role": "assistant", "content": raw_llm_output}
                    )  # Save successful LLM output
                    session.modified = True
                    return jsonify({"response": passage_text})

            except json.JSONDecodeError:
                app.logger.warn(
                    f"LLM response was not valid JSON on attempt {attempt + 1}. Query: '{user_query}'. Raw output: '{raw_llm_output}'"
                )
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    session["conversation_history"] = current_history
                    session["conversation_history"].append(
                        {"role": "assistant", "content": raw_llm_output}
                    )  # Save malformed JSON response
                    session.modified = True
                    return jsonify(
                        {
                            "response": "LLM did not return the expected JSON format after multiple attempts. Please try again."
                        }
                    )

        # OpenAI SDK specific error handling
        except APIConnectionError as e:
            app.logger.error(f"OpenAI APIConnectionError on attempt {attempt + 1}: {e}")
            # Potentially retry for connection errors if desired, or fail.
            if attempt < max_retries - 1:  # Example: retry connection errors
                continue
            failed_assistant_msg = "Error: Could not connect to the LLM service."
            session["conversation_history"] = current_history
            session["conversation_history"].append(
                {"role": "assistant", "content": failed_assistant_msg}
            )
            session.modified = True
            return jsonify({"error": failed_assistant_msg}), 503
        except RateLimitError as e:
            app.logger.error(f"OpenAI RateLimitError: {e}")
            failed_assistant_msg = "Error: Rate limit exceeded with the LLM service. Please try again later."
            session["conversation_history"] = current_history
            session["conversation_history"].append(
                {"role": "assistant", "content": failed_assistant_msg}
            )
            session.modified = True
            return jsonify({"error": failed_assistant_msg}), 429
        except APITimeoutError as e:
            app.logger.error(f"OpenAI APITimeoutError on attempt {attempt+1}: {e}")
            if attempt < max_retries - 1:
                continue  # Retry timeouts
            failed_assistant_msg = "Error: Request to LLM service timed out."
            session["conversation_history"] = current_history
            session["conversation_history"].append(
                {"role": "assistant", "content": failed_assistant_msg}
            )
            session.modified = True
            return jsonify({"error": failed_assistant_msg}), 504
        except APIError as e:  # Catch other OpenAI API errors
            app.logger.error(
                f"OpenAI APIError: Status Code: {e.status_code}, Message: {e.message}"
            )
            error_message = f"LLM service error: {e.message}"
            # Add the error as an assistant message to history
            session["conversation_history"] = current_history
            session["conversation_history"].append(
                {"role": "assistant", "content": f"Error: {error_message}"}
            )
            session.modified = True
            return jsonify({"error": error_message}), e.status_code or 500
        except (
            IndexError,
            KeyError,
        ) as e:  # For issues with parsing completion.choices structure
            app.logger.error(
                f"Error parsing LLM SDK response structure: {e}. Completion object: {completion if 'completion' in locals() else 'N/A'}"
            )
            failed_assistant_msg = (
                "Error: Received an unexpected response structure from the LLM service."
            )
            session["conversation_history"] = current_history
            session["conversation_history"].append(
                {"role": "assistant", "content": failed_assistant_msg}
            )
            session.modified = True
            return (
                jsonify(
                    {
                        "error": "Received an unexpected response structure from the LLM service."
                    }
                ),
                500,
            )

    # This part should ideally not be reached if logic above is correct,
    # but as a fallback if loop finishes without returning:
    return (
        jsonify(
            {"error": "Failed to get a valid response from LLM after multiple retries."}
        ),
        500,
    )


# The old try block content is now inside the loop in the REPLACE section above.
# This SEARCH block is to remove the old structure.
# The outer exception handlers (HTTPError, RequestException, etc.) are now part of the loop structure.

if __name__ == "__main__":
    app.run(debug=True)
