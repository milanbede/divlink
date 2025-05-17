import os
import requests
import json  # Moved from inside the function
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


@app.route("/")
def index():
    return render_template("index.html")


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

                return jsonify({"response": passage_reference})  # Success

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
