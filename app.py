import os # Still needed for FLASK_SECRET_KEY and os.urandom
# json and re are no longer directly needed at the top level of app.py
import random  # For random.choices in /query, random.seed is now in RandomSeeder
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
)  # OpenAI SDK
from random_seeder import RandomSeeder
from bible_parser import BibleParser # Import the new class

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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/query", methods=["POST"])
def query_llm():
    if not client:  # Check if OpenAI client was initialized
        app.logger.error("OpenAI client not initialized. Check OPENROUTER_API_KEY.")
        return jsonify({"error": "LLM service is not configured on the server."}), 500

    user_query = request.json.get("query")
    if not user_query:
        return jsonify({"error": "No query provided."}), 400

    base_prompt_text = """You are a Bible reference guide trained to help people find direct, relevant verses from the Bible that speak to people's questions, challenges, or sins. You do not paraphrase, interpret, or soften God’s Word.

Your role is to return a JSON object only. This object must contain a single key: "references". The value of "references" must be a list of up to 3 objects. Each object must contain:

1. "reference": A string containing a valid Bible verse or passage (e.g., "Proverbs 3:5–6" or "Matthew 10:34").
2. "relevance_score": An integer from 1 (low) to 10 (high), indicating how directly this verse addresses the user's input.
3. "helpfulness_score": An integer from 1 (low) to 10 (high), indicating how spiritually effective this verse is for confronting, correcting, or encouraging the person according to Scripture.

**Only assign 10/10 in both fields if the verse is an extremely direct and spiritually powerful match. This should be rare.** Verses with both scores as 10 should be highlighted by being placed first in the list.

You must not include any commentary or explanation. No text should appear outside the JSON object.

Assume the user is seeking real truth, not comfort or compromise. Prioritize verses that reflect:
- The **fear of the Lord**
- **Repentance**, **conviction**, and **God’s justice**
- **Faith**, **wisdom**, and **obedience**
- **Boldness**, **self-denial**, and **spiritual warfare**

If the input is vague, return verses that expose the likely spiritual root.

Use only Scripture. Avoid emotional reassurance, vague spirituality, or modern therapeutic language. The Bible is sufficient.

### Example:

**Input:** "I feel like giving up."
**Output:**
{
  "references": [
    {"reference": "Galatians 6:9", "relevance_score": 9, "helpfulness_score": 9},
    {"reference": "Isaiah 40:31", "relevance_score": 8, "helpfulness_score": 9},
    {"reference": "2 Corinthians 4:16–18", "relevance_score": 7, "helpfulness_score": 8}
  ]
}

**Input:** "Is homosexuality really a sin?"
**Output:**
{
  "references": [
    {"reference": "Romans 1:26–27", "relevance_score": 10, "helpfulness_score": 10},
    {"reference": "1 Corinthians 6:9–10", "relevance_score": 10, "helpfulness_score": 9},
    {"reference": "Leviticus 18:22", "relevance_score": 9, "helpfulness_score": 8}
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
    # The 'current_history' list serves as the base messages payload.

    max_retries = 3
    raw_llm_output = None
    last_failed_output_for_reprompt = None  # Store problematic output for re-prompting

    for attempt in range(max_retries):
        messages_for_api_call = list(
            current_history
        )  # Start with the base history for this attempt

        if attempt > 0 and last_failed_output_for_reprompt is not None:
            reprompt_instruction_content = (
                f"Your previous response was not in the correct JSON format or was empty. "
                f"Please ensure your output is a valid JSON object as specified in the initial system instructions. "
                f'The expected structure is: {{"references": [{{"reference": "Book C:V-V", "relevance_score": N, "helpfulness_score": N}}, ...]}}. '
                f"Your previous problematic response was: ```\n{last_failed_output_for_reprompt}\n```. "
                f"Please provide the corrected response based on the original query and context."
            )
            messages_for_api_call.append(
                {"role": "user", "content": reprompt_instruction_content}
            )
            app.logger.info("Added re-prompt instruction for formatting correction.")

        try:
            app.logger.info(
                f"Attempt {attempt + 1} for query: '{user_query}'. Messages length for API: {len(messages_for_api_call)}"
            )

            completion = client.chat.completions.create(
                model="deepseek/deepseek-r1-distill-qwen-32b:free",  # Or your chosen model
                messages=messages_for_api_call,  # Use the potentially augmented message list
                # temperature=0.7, # Optional: Adjust creativity
            )

            raw_llm_output = (
                completion.choices[0].message.content if completion.choices else ""
            )

            if not raw_llm_output or not raw_llm_output.strip():
                app.logger.warn(
                    f"LLM returned empty content on attempt {attempt + 1} for query: '{user_query}'. Raw response: '{raw_llm_output}'"
                )
                last_failed_output_for_reprompt = raw_llm_output  # Store for re-prompt
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    session["conversation_history"] = current_history  # Save user query
                    if raw_llm_output is not None:
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
                    last_failed_output_for_reprompt = (
                        raw_llm_output  # Store for re-prompt
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
                    last_failed_output_for_reprompt = (
                        raw_llm_output  # Store for re-prompt
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
                # Weighted random selection
                # random.choices returns a list, so get the first element
                selected_index = random.choices(
                    range(len(valid_references_for_selection)), weights=weights, k=1
                )[0]
                passage_reference = valid_references_for_selection[selected_index]
                selected_weight = weights[
                    selected_index
                ]  # This is the combined score (relevance + helpfulness)

                app.logger.info(
                    f"Weighted randomly selected reference: '{passage_reference}' (score: {selected_weight}) from LLM output for query: '{user_query}'. Weights: {weights}, Options: {valid_references_for_selection}"
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
                    return jsonify({"response": passage_text, "score": selected_weight})

            except json.JSONDecodeError:
                app.logger.warn(
                    f"LLM response was not valid JSON on attempt {attempt + 1}. Query: '{user_query}'. Raw output: '{raw_llm_output}'"
                )
                last_failed_output_for_reprompt = raw_llm_output  # Store for re-prompt
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


@app.route("/random_psalm", methods=["GET"])
def random_psalm():
    passage_text = bible_parser.get_random_psalm_passage()

    # Check if get_random_psalm_passage returned an error string
    if passage_text.startswith("Error:"):
        app.logger.error(f"Failed to get random Psalm: {passage_text}")
        # Return the error message from the parser, or a generic one
        # For consistency, let's use the message from the parser if it's user-friendly enough
        # or map specific internal errors to user-friendly messages.
        # For now, just pass it through if it's a known error type.
        if "Bible data not available" in passage_text or "Book of Psalms not found" in passage_text or "No Psalms available" in passage_text:
             return jsonify({"error": passage_text}), 500 # Or a more generic "Could not retrieve Psalm"
        return jsonify({"error": "Could not retrieve a random Psalm at this moment."}), 500
    
    # If no error, passage_text contains the Psalm
    # The logger message for success is now inside BibleParser.get_random_psalm_passage()
    return jsonify(
        {"response": passage_text, "score": None}
    )  # Score is null as it's not an LLM eval


if __name__ == "__main__":
    app.run(debug=True)
