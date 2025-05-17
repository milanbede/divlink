import os
import requests
import json
import re  # For parsing Bible references

# import xml.etree.ElementTree as ET # No longer needed for NIST
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


def get_drand_seed():
    """Fetches randomness from drand and returns it as an integer seed."""
    try:
        response = requests.get("https://drand.cloudflare.com/public/latest", timeout=5)
        response.raise_for_status()
        data = response.json()
        randomness_hex = data.get("randomness")
        if randomness_hex:
            app.logger.info(
                f"Successfully fetched seed from drand. Round: {data.get('round')}"
            )
            return int(randomness_hex, 16)
        else:
            app.logger.error("Drand response did not contain 'randomness' field.")
            return None
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Could not fetch seed from drand: {e}.")
        return None
    except (ValueError, TypeError, KeyError) as e:
        app.logger.error(f"Error processing drand response: {e}.")
        return None


def get_nist_seed():
    """Fetches randomness from NIST beacon and returns it as an integer seed."""
    try:
        response = requests.get(
            "https://beacon.nist.gov/beacon/2.0/pulse/last", timeout=5
        )
        response.raise_for_status()
        data = response.json()  # NIST beacon v2.0 returns JSON

        # Access the outputValue from the nested structure
        randomness_hex = data.get("pulse", {}).get("outputValue")

        if randomness_hex:
            app.logger.info("Successfully fetched seed from NIST beacon.")
            return int(randomness_hex, 16)
        else:
            app.logger.error(
                "NIST beacon JSON response did not contain 'pulse.outputValue' field or it was empty."
            )
            return None
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Could not fetch seed from NIST beacon: {e}.")
        return None
    except (
        json.JSONDecodeError,
        ValueError,
        TypeError,
        KeyError,
    ) as e:  # Updated exception handling
        app.logger.error(f"Error processing NIST beacon JSON response: {e}.")
        return None


def initialize_random_seeding():
    """Initializes the random number generator using seeds from drand and NIST."""
    drand_seed = get_drand_seed()
    nist_seed = get_nist_seed()

    final_seed = None

    if drand_seed is not None and nist_seed is not None:
        # Combine seeds if both are available (e.g., XOR)
        # Ensure they are integers for XOR
        final_seed = drand_seed ^ nist_seed
        app.logger.info("Combined seeds from drand and NIST.")
    elif drand_seed is not None:
        final_seed = drand_seed
        app.logger.info("Using seed from drand only.")
    elif nist_seed is not None:
        final_seed = nist_seed
        app.logger.info("Using seed from NIST only.")
    else:
        app.logger.error(
            "Failed to fetch seed from both drand and NIST. Using default random seed."
        )

    if final_seed is not None:
        random.seed(final_seed)
        app.logger.info(
            "Random number generator seeded with value derived from external beacons."
        )
    else:
        # Python's random module is seeded by default if random.seed() is not called.
        # This path means we explicitly acknowledge we are using that default.
        app.logger.info(
            "Random number generator using default (time-based or OS-specific) seed."
        )


# Initialize the random number generator at application startup
initialize_random_seeding()

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

    divine_name_pattern = re.compile(r"\b(LORD|Lord)\b")

    if start_verse is None:  # Whole chapter
        for i, verse_text in enumerate(chapter_verses_list):
            cleaned_verse_text = re.sub(r"\{.*?\}", "", verse_text).strip()
            # Wrap divine names
            cleaned_verse_text_highlighted = divine_name_pattern.sub(r'<span class="divine-name">\1</span>', cleaned_verse_text)
            passage_texts.append(f"{i+1} {cleaned_verse_text_highlighted}")
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
            # Wrap divine names
            cleaned_verse_text_highlighted = divine_name_pattern.sub(r'<span class="divine-name">\1</span>', cleaned_verse_text)
            passage_texts.append(f"{i+1} {cleaned_verse_text_highlighted}")

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

Your role is to return a JSON object. This object must contain a single key "references". The value of "references" should be a list of objects. Each object in the list must represent a single Bible reference and contain three keys:
1.  "reference": A string with the Bible reference (e.g., "Proverbs 3:5-6" or "Matthew 10:34").
2.  "relevance_score": A numerical score from 1 (low) to 10 (high) indicating how relevant this specific verse is to the user's query.
3.  "helpfulness_score": A numerical score from 1 (low) to 10 (high) indicating how helpful this specific verse would be in addressing the spiritual root of the query, according to the principles outlined below.

Provide up to 3 such reference objects. Do not include any commentary or other text outside the JSON object.

Assume the person is seeking real truth, not feel-good platitudes. Prioritize verses that reflect:
	•	The fear of the Lord
	•	Repentance, conviction, and God’s justice
	•	Faith, wisdom, and obedience
	•	Boldness, self-denial, and spiritual warfare

Use only Scripture. Avoid emotional reassurance or modern therapeutic language. The Bible is sufficient. If the input is unclear, choose verses that most directly address the spiritual root of the query.

Example:

Input: "I feel like giving up."
Output:
{
  "references": [
    {"reference": "Galatians 6:9", "relevance_score": 9, "helpfulness_score": 8},
    {"reference": "Isaiah 40:31", "relevance_score": 8, "helpfulness_score": 9},
    {"reference": "2 Corinthians 4:16-18", "relevance_score": 7, "helpfulness_score": 7}
  ]
}

Input: "Is homosexuality really a sin?"
Output:
{
  "references": [
    {"reference": "Romans 1:26-27", "relevance_score": 10, "helpfulness_score": 9},
    {"reference": "1 Corinthians 6:9-10", "relevance_score": 9, "helpfulness_score": 10},
    {"reference": "Leviticus 18:22", "relevance_score": 8, "helpfulness_score": 8}
  ]
}

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
                # Attempt to extract JSON from raw_llm_output, possibly wrapped in markdown
                json_match = re.search(
                    r"```json\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*?\})",
                    raw_llm_output,
                    re.DOTALL,
                )

                extracted_json_str = None
                if json_match:
                    # Prioritize the content within ```json ... ``` if present
                    extracted_json_str = (
                        json_match.group(1)
                        if json_match.group(1)
                        else json_match.group(2)
                    )

                if not extracted_json_str:
                    # If regex didn't find a clear JSON block, or if raw_llm_output itself might be JSON
                    # This case handles if the LLM *only* returned JSON without wrappers.
                    # Or if the regex failed but it might still be parsable.
                    # We will let json.loads try on raw_llm_output if extracted_json_str is None.
                    # However, if raw_llm_output is clearly not starting with { then it's unlikely to be JSON.
                    # For safety, if regex fails, we'll try raw_llm_output only if it looks like JSON.
                    if raw_llm_output.strip().startswith(
                        "{"
                    ) and raw_llm_output.strip().endswith("}"):
                        extracted_json_str = raw_llm_output
                    else:
                        # If regex fails and it doesn't look like JSON, trigger JSONDecodeError path
                        raise json.JSONDecodeError(
                            "No valid JSON block found in LLM output.",
                            raw_llm_output,
                            0,
                        )

                parsed_json = json.loads(extracted_json_str)
                references_data_list = parsed_json.get("references")

                if not isinstance(references_data_list, list):
                    app.logger.warn(
                        f"LLM response JSON 'references' is not a list on attempt {attempt + 1}. Query: '{user_query}'. Raw output: '{raw_llm_output}'"
                    )
                    if attempt < max_retries - 1:
                        continue  # Retry
                    else:
                        # Save problematic response and return error
                        session["conversation_history"] = current_history
                        session["conversation_history"].append(
                            {"role": "assistant", "content": raw_llm_output}
                        )
                        session.modified = True
                        return jsonify(
                            {
                                "response": "LLM did not return the expected list format. Please try again."
                            }
                        )

                valid_references_for_selection = []
                weights = []

                for item in references_data_list:
                    if not isinstance(item, dict):
                        app.logger.warn(
                            f"Item in 'references' list is not a dictionary: {item}. Skipping."
                        )
                        continue

                    ref_str = item.get("reference")
                    rel_score = item.get("relevance_score")
                    help_score = item.get("helpfulness_score")

                    if not isinstance(ref_str, str) or not ref_str.strip():
                        app.logger.warn(
                            f"Invalid or missing 'reference' string in item: {item}. Skipping."
                        )
                        continue

                    # Ensure scores are numbers, default to 0 if not or if invalid type
                    try:
                        rel_score_num = float(
                            rel_score if isinstance(rel_score, (int, float)) else 0
                        )
                        help_score_num = float(
                            help_score if isinstance(help_score, (int, float)) else 0
                        )
                    except (ValueError, TypeError):
                        app.logger.warn(
                            f"Invalid score types in item: {item}. Defaulting scores to 0 for this item."
                        )
                        rel_score_num = 0
                        help_score_num = 0

                    # Scores should be positive for weighting, ensure at least a minimal weight if scores are 0 or negative
                    combined_score = rel_score_num + help_score_num
                    # Ensure weight is at least 1 to be included in random.choices if all scores are 0
                    weight = max(1, combined_score)

                    valid_references_for_selection.append(ref_str)
                    weights.append(weight)

                if not valid_references_for_selection:
                    app.logger.warn(
                        f"No valid references with scores found after parsing LLM output on attempt {attempt + 1}. Query: '{user_query}'. Raw output: '{raw_llm_output}'"
                    )
                    if attempt < max_retries - 1:
                        continue  # Retry
                    else:
                        session["conversation_history"] = current_history
                        session["conversation_history"].append(
                            {"role": "assistant", "content": raw_llm_output}
                        )
                        session.modified = True
                        return jsonify(
                            {
                                "response": "LLM did not provide any usable Bible references after multiple attempts. Please try rephrasing."
                            }
                        )

                # Weighted random selection
                passage_reference = random.choices(
                    valid_references_for_selection, weights=weights, k=1
                )[0]
                app.logger.info(
                    f"Weighted randomly selected reference: '{passage_reference}' from LLM output for query: '{user_query}'. Weights: {weights}, Options: {valid_references_for_selection}"
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
