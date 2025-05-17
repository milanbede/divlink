import os
import requests
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

    try:
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
                f"LLM returned empty content for query: {user_query}. Raw response: {data}"
            )
            return jsonify(
                {"response": "LLM returned an empty response. Please try rephrasing."}
            )

        try:
            # Attempt to parse the LLM output as JSON
            import json

            parsed_json = json.loads(raw_llm_output)
            passage_reference = parsed_json.get("reference")

            if not passage_reference or not isinstance(passage_reference, str):
                app.logger.warn(
                    f"LLM response JSON did not contain a valid 'reference' string. Query: {user_query}. Raw output: {raw_llm_output}"
                )
                return jsonify(
                    {
                        "response": "Could not extract a valid passage reference from LLM. Please try again."
                    }
                )

            return jsonify({"response": passage_reference})

        except json.JSONDecodeError:
            app.logger.warn(
                f"LLM response was not valid JSON. Query: {user_query}. Raw output: {raw_llm_output}"
            )
            # Fallback: if it's not JSON, maybe it's just the reference directly (less likely with the new prompt)
            # Or, it could be a refusal or other text. For now, we'll return it as is if it's not JSON.
            # A stricter approach would be to return an error here.
            # For now, let's assume if it's not JSON, it might be a direct answer or an error message from the LLM.
            # However, the prompt strongly requests JSON. If it's not JSON, it's likely an issue.
            return jsonify(
                {
                    "response": "LLM did not return the expected JSON format. Please try again."
                }
            )

    except requests.exceptions.HTTPError as http_err:
        app.logger.error(f"HTTP error occurred: {http_err} - {api_response.text}")
        error_message = "Error communicating with the LLM service."
        try:
            err_details = (
                api_response.json().get("error", {}).get("message", api_response.text)
            )
            error_message = f"LLM service error: {err_details}"
        except ValueError:  # if response is not JSON
            pass  # use default error_message
        return jsonify({"error": error_message}), api_response.status_code
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request exception occurred: {e}")
        return jsonify({"error": "Failed to connect to the LLM service."}), 503
    except (IndexError, KeyError) as e:
        app.logger.error(
            f"Error parsing LLM response: {e}. Raw response: {data if 'data' in locals() else 'N/A'}"
        )
        return (
            jsonify(
                {
                    "error": "Received an unexpected response format from the LLM service."
                }
            ),
            500,
        )


if __name__ == "__main__":
    app.run(debug=True)
