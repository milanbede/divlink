import os
import requests
import json
import re  # For parsing Bible references
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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
    if not OPENROUTER_API_KEY:
        app.logger.error("OPENROUTER_API_KEY not configured.")
        return jsonify({"error": "API key not configured on the server."}), 500

    user_query = request.json.get("query")
    if not user_query:
        return jsonify({"error": "No query provided."}), 400

    prompt = (
        f"For the query: '{user_query}', identify the single most relevant Bible passage. "
        "Respond ONLY with a JSON object containing a single key 'reference', "
        'where the value is the passage reference as a string (e.g., {"reference": "John 3:16"} or {"reference": "Genesis 1:1-5"}). '
        "Do not include any other text, explanations, or apologies."
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            app.logger.info(f"Attempt {attempt + 1} for query: {user_query}")
            api_response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",  # Optional: Replace with your actual site URL
                    "X-Title": "Bible Terminal",  # Optional: Replace with your app name
                },
                json={
                    "model": "qwen/qwen3-0.6b-04-28:free",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            api_response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            data = api_response.json()

            raw_llm_output = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            if not raw_llm_output.strip():
                app.logger.warn(
                    f"LLM returned empty content on attempt {attempt + 1} for query: {user_query}. Raw response: {data}"
                )
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    return jsonify(
                        {
                            "response": "LLM returned an empty response after multiple attempts. Please try rephrasing."
                        }
                    )

            try:
                # Attempt to parse the LLM output as JSON
                parsed_json = json.loads(raw_llm_output)
                passage_reference = parsed_json.get("reference")

                if not passage_reference or not isinstance(passage_reference, str):
                    app.logger.warn(
                        f"LLM response JSON did not contain a valid 'reference' string on attempt {attempt + 1}. Query: {user_query}. Raw output: {raw_llm_output}"
                    )
                    if attempt < max_retries - 1:
                        continue  # Retry
                    else:
                        return jsonify(
                            {
                                "response": "Could not extract a valid passage reference from LLM after multiple attempts. Please try again."
                            }
                        )

                # Successfully got passage_reference from LLM, now parse it and get text
                parsed_ref = parse_bible_reference(passage_reference)
                if not parsed_ref:
                    app.logger.warn(
                        f"Could not parse LLM reference: '{passage_reference}' for query: {user_query}"
                    )
                    # Retry if LLM output is unparseable as a reference
                    if attempt < max_retries - 1:
                        continue
                    return jsonify(
                        {
                            "response": f"Could not understand the Bible reference: '{passage_reference}'. Please try rephrasing your query."
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
                        f"Bible lookup error for LLM reference '{passage_reference}': {passage_text}"
                    )
                    # Do not retry LLM here. The reference was parseable but invalid for lookup.
                    return jsonify(
                        {
                            "response": "I received a Bible reference, but it appears to be invalid (e.g., chapter or verse out of range). Please try rephrasing your query."
                        }
                    )
                else:
                    # Successfully retrieved passage text
                    return jsonify({"response": passage_text})

            except json.JSONDecodeError:
                app.logger.warn(
                    f"LLM response was not valid JSON on attempt {attempt + 1}. Query: {user_query}. Raw output: {raw_llm_output}"
                )
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    return jsonify(
                        {
                            "response": "LLM did not return the expected JSON format after multiple attempts. Please try again."
                        }
                    )

        except requests.exceptions.HTTPError as http_err:
            # For HTTP errors, we typically don't retry unless it's a specific transient error.
            # For simplicity here, we'll log and return error as before, not retrying on HTTP errors.
            app.logger.error(f"HTTP error occurred: {http_err} - {api_response.text}")
            error_message = "Error communicating with the LLM service."
            try:
                err_details = (
                    api_response.json()
                    .get("error", {})
                    .get("message", api_response.text)
                )
                error_message = f"LLM service error: {err_details}"
            except ValueError:  # if response is not JSON
                pass
            return jsonify({"error": error_message}), api_response.status_code
        except requests.exceptions.RequestException as e:
            # Network-level errors, usually not retried here without more sophisticated backoff.
            app.logger.error(f"Request exception occurred: {e}")
            return jsonify({"error": "Failed to connect to the LLM service."}), 503
        except (IndexError, KeyError) as e:
            # This error means the structure of the API response itself is unexpected (e.g. no 'choices')
            # This is less about LLM content and more about API contract.
            app.logger.error(
                f"Error parsing LLM API structure: {e}. Raw response: {data if 'data' in locals() else 'N/A'}"
            )
            # Not retrying this type of error as it's unlikely to be fixed by a simple retry.
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
