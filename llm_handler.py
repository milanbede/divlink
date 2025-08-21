import re
import json
import random
import time

from openai import (
    APIError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
)


class LLMHandler:
    def _build_system_prompt(self, available_books):
        """Build system prompt dynamically with available books list."""
        books_list = (
            ", ".join(available_books) if available_books else "No books available"
        )

        return f"""You are a Bible reference guide trained to help people find direct, relevant verses or passages from the Bible that speak to people's questions, challenges, or sins. You do not paraphrase, interpret, or soften God's Word.

Available books in this Bible version: {books_list}

IMPORTANT: Only use book names from the list above. Use the exact book names as provided.

Your role is to return a JSON list only. This list must contain up to 3 objects. Each object must contain:

1. "ref": A string containing a valid Bible verse or passage (e.g., "Proverbs 3:5–6" or "Matthew 10:34"). The book name must be from the available books list above.
2. "relevance": An integer from 1 (low) to 10 (high), indicating how directly this verse or passage addresses the user's input.
3. "helpfulness": An integer from 1 (low) to 10 (high), indicating how spiritually effective this verse or passage is for confronting, correcting, or encouraging the person according to Scripture.

You may refer to full passages (multiple verses) if they are contextually richer and more helpful than short quotes. Avoid quoting isolated verses that seem harsh or absolute unless the surrounding context supports that conclusion. If nearby verses clarify God's mercy, grace, or power, prefer including them.

**Only assign 10/10 in both fields if the passage is an extremely direct and spiritually powerful match. This should be rare.**

You must not include any commentary or explanation. No text should appear outside the JSON list.

Assume the user is seeking real truth, not comfort or compromise. Prioritize verses that reflect:
- The **fear of the Lord**
- **Repentance**, **conviction**, and **God's justice**
- **Faith**, **wisdom**, and **obedience**
- **Boldness**, **self-denial**, and **spiritual warfare**
- And where helpful, **hope**, **joy**, and **God's steadfast love**

Favor responses that uplift through truth. Avoid shallow optimism or merely therapeutic sentimentality.

If the input is vague, return verses that expose the likely spiritual root.

Use only Scripture. Avoid emotional reassurance, vague spirituality, or modern therapeutic language. The Bible is sufficient.

Begin."""

    MAX_HISTORY_PAIRS = 5  # Number of user/assistant message pairs
    MAX_RETRIES = 3

    def __init__(
        self, client, logger, bible_parser, model_name, fallback_model_name=None
    ):
        self.client = client
        self.logger = logger
        self.bible_parser = bible_parser
        self.model_name = model_name
        self.fallback_model_name = fallback_model_name
        # Cache bible parsers by version to avoid recreating them
        self._cached_parsers = {}
        # Pre-populate with the provided parser
        self._cached_parsers[bible_parser.bible_version] = bible_parser

    def _get_cached_parser(self, bible_version):
        """Get a cached BibleParser for the specified version, creating if needed."""
        if bible_version not in self._cached_parsers:
            from bible_parser import BibleParser

            self._cached_parsers[bible_version] = BibleParser(
                self.logger, bible_version=bible_version
            )
            self.logger.info(
                f"Created new cached BibleParser for version: {bible_version}"
            )
        return self._cached_parsers[bible_version]

    def _get_english_book_names(self):
        """Always get English book names for LLM prompt, regardless of user's version."""
        english_parser = self._get_cached_parser("kjv")
        return english_parser.get_available_books()

    def _get_conversation_history(self, session):
        if "conversation_history" not in session:
            # Build system prompt with English book names for LLM consistency
            english_books = self._get_english_book_names()
            system_prompt = self._build_system_prompt(english_books)
            session["conversation_history"] = [
                {"role": "system", "content": system_prompt}
            ]
        return list(session["conversation_history"])  # Return a copy

    def _update_conversation_history(
        self,
        session,
        current_history,
        user_query,
        assistant_response=None,
        printed_passage=None,
    ):
        if assistant_response is not None:
            current_history.append({"role": "assistant", "content": assistant_response})

        # Trim history if it's too long
        if len(current_history) > (
            self.MAX_HISTORY_PAIRS * 2 + 1
        ):  # +1 for system prompt
            current_history = [current_history[0]] + current_history[
                -(self.MAX_HISTORY_PAIRS * 2) :
            ]

        session["conversation_history"] = current_history

        # Track printed passages, limiting to last MAX_HISTORY_PAIRS
        if printed_passage is not None:
            if "printed_passages" not in session:
                session["printed_passages"] = []
            session["printed_passages"].append(printed_passage)
            # Trim printed_passages to last MAX_HISTORY_PAIRS items
            if len(session["printed_passages"]) > self.MAX_HISTORY_PAIRS:
                session["printed_passages"] = session["printed_passages"][
                    -self.MAX_HISTORY_PAIRS :
                ]

        session["modified"] = True

    def _extract_json_from_llm_output(self, raw_llm_output):
        """
        Extracts and cleans a JSON string from the LLM output.
        Strips code fences (``` or ```json) and normalizes common unicode issues.
        """
        content = raw_llm_output.strip()

        # Remove code fences if present (handles ```json ... ``` or ``` ... ```)
        fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.DOTALL)
        match = fence_pattern.search(content)
        if match:
            content = match.group(1).strip()

        # Extract the first JSON list or object block
        json_block_pattern = re.compile(r"(\[.*?\]|\{.*?\})", re.DOTALL)
        match = json_block_pattern.search(content)
        if match:
            content = match.group(1).strip()
        else:
            raise json.JSONDecodeError(
                "No valid JSON list or object found in LLM response.",
                raw_llm_output,
                0,
            )

        # Normalize problematic unicode characters
        content = content.replace("\u00a0", " ")
        content = content.replace("\u200b", "")
        content = content.replace("\ufeff", "")
        content = content.replace("–", "-")
        content = content.replace("—", "-")

        return content

    def _parse_llm_references_data(self, references_data_list):
        valid_references_for_selection = []
        weights = []
        for item in references_data_list:
            if not isinstance(item, dict):
                self.logger.warn(
                    f"Item in 'references' list is not a dictionary: {item}. Skipping."
                )
                continue
            ref_str = item.get("ref")
            rel_score = item.get("relevance")
            help_score = item.get("helpfulness")

            if not isinstance(ref_str, str) or not ref_str.strip():
                self.logger.warn(
                    f"Invalid or missing 'ref' string in item: {item}. Skipping."
                )
                continue
            try:
                rel_score_num = float(
                    rel_score if isinstance(rel_score, (int, float)) else 0
                )
                help_score_num = float(
                    help_score if isinstance(help_score, (int, float)) else 0
                )
            except (ValueError, TypeError):
                self.logger.warn(
                    f"Invalid score types in item: {item}. Defaulting scores to 0."
                )
                rel_score_num = 0
                help_score_num = 0

            combined_score = rel_score_num + help_score_num
            weight = max(1, combined_score)  # Ensure weight is at least 1
            valid_references_for_selection.append(ref_str)
            weights.append(weight)

        if not valid_references_for_selection:
            return None, None  # Indicate no valid references found
        return valid_references_for_selection, weights

    def _call_llm_api(self, model_name, messages, user_query, attempt):
        """Make a single API call to the LLM."""
        self.logger.info(
            f"LLM API Call Attempt {attempt + 1} for query: '{user_query}'. Model: '{model_name}'. Messages length: {len(messages)}"
        )
        start_time = time.monotonic()
        completion = self.client.chat.completions.create(
            model=model_name, messages=messages
        )
        end_time = time.monotonic()
        latency_ms = (end_time - start_time) * 1000

        raw_llm_output = (
            completion.choices[0].message.content if completion.choices else ""
        )
        prompt_tokens = completion.usage.prompt_tokens if completion.usage else 0
        completion_tokens = (
            completion.usage.completion_tokens if completion.usage else 0
        )

        return {
            "raw_output": raw_llm_output,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def _try_model_with_retries(self, model_name, session, user_query, current_history):
        """Try a single model with retries, return success or failure."""
        last_failed_output_for_reprompt = None

        for attempt in range(self.MAX_RETRIES):
            messages_for_api_call = list(current_history)

            if attempt > 0 and last_failed_output_for_reprompt is not None:
                reprompt_instruction_content = (
                    f"Your previous response was not in the correct JSON format or was empty. "
                    f"Please ensure your output is a valid JSON list as specified in the initial system instructions. "
                    f'The expected structure is: [{{"ref": "Book C:V-V", "relevance": N, "helpfulness": N}}, ...]. Please ensure the output is a JSON list, not a JSON object containing a list. '
                    f"Your previous problematic response was: ```\n{last_failed_output_for_reprompt}\n```."
                )
                messages_for_api_call.append(
                    {"role": "user", "content": reprompt_instruction_content}
                )
                self.logger.info(
                    "Added re-prompt instruction for formatting correction."
                )

            try:
                api_result = self._call_llm_api(
                    model_name, messages_for_api_call, user_query, attempt
                )
                raw_llm_output = api_result["raw_output"]

                if not raw_llm_output or not raw_llm_output.strip():
                    self.logger.warn(
                        f"LLM returned empty content on attempt {attempt + 1}. Raw: '{raw_llm_output}'"
                    )
                    last_failed_output_for_reprompt = raw_llm_output
                    if attempt < self.MAX_RETRIES - 1:
                        continue
                    return {"error": "empty_content", "raw_output": raw_llm_output}

                extracted_json_str = self._extract_json_from_llm_output(raw_llm_output)
                self.logger.debug(f"Attempting to parse JSON: <{extracted_json_str}>")
                references_data_list = json.loads(extracted_json_str)

                if not isinstance(references_data_list, list):
                    self.logger.warn(
                        f"LLM output is not a list as expected. Attempt {attempt + 1}. Raw: '{raw_llm_output}'"
                    )
                    last_failed_output_for_reprompt = raw_llm_output
                    if attempt < self.MAX_RETRIES - 1:
                        continue
                    return {"error": "not_list", "raw_output": raw_llm_output}

                valid_refs, weights = self._parse_llm_references_data(
                    references_data_list
                )

                if not valid_refs:
                    self.logger.warn(
                        f"No valid references found after parsing LLM output. Attempt {attempt + 1}. Raw: '{raw_llm_output}'"
                    )
                    last_failed_output_for_reprompt = raw_llm_output
                    if attempt < self.MAX_RETRIES - 1:
                        continue
                    return {"error": "no_valid_refs", "raw_output": raw_llm_output}

                # Success! Return the result
                return {
                    "success": True,
                    "valid_refs": valid_refs,
                    "weights": weights,
                    "raw_output": raw_llm_output,
                    "api_result": api_result,
                }

            except json.JSONDecodeError as e:
                self.logger.warn(
                    f"LLM response not valid JSON. Attempt {attempt + 1}. Error: {e}. Raw: '{raw_llm_output}'"
                )
                last_failed_output_for_reprompt = raw_llm_output
                if attempt < self.MAX_RETRIES - 1:
                    continue
                return {"error": "invalid_json", "raw_output": raw_llm_output}

            except APIConnectionError as e:
                self.logger.error(
                    f"OpenAI APIConnectionError on attempt {attempt + 1}: {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    continue
                return {"error": "connection_error", "exception": e}
            except RateLimitError as e:
                self.logger.error(f"OpenAI RateLimitError: {e}")
                return {"error": "rate_limit", "exception": e}
            except APITimeoutError as e:
                self.logger.error(f"OpenAI APITimeoutError on attempt {attempt+1}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    continue
                return {"error": "timeout", "exception": e}
            except APIError as e:
                self.logger.error(
                    f"OpenAI APIError: Status: {e.status_code}, Msg: {e.message}"
                )
                return {"error": "api_error", "exception": e}
            except (IndexError, KeyError) as e:
                self.logger.error(f"Error parsing LLM SDK response: {e}.")
                if attempt < self.MAX_RETRIES - 1:
                    continue
                return {"error": "parsing_error", "exception": e}

        return {"error": "max_retries_exceeded"}

    def get_llm_bible_reference(self, session, user_query, bible_version="kjv"):
        """Main method to get Bible references from LLM with fallback model support."""
        if not self.client:
            self.logger.error(
                "OpenAI client not initialized. LLM functionality disabled."
            )
            return {"error": "LLM service is not configured on the server."}, 500

        # Get cached bible parser for this version
        bible_parser = self._get_cached_parser(bible_version)

        # Initialize our list of already‐printed passages
        if "printed_passages" not in session:
            session["printed_passages"] = []

        # Get conversation history with consistent English system prompt
        if (
            "conversation_history" not in session
            or session.get("bible_version") != bible_version
        ):
            # Build system prompt with English book names for LLM consistency
            english_books = self._get_english_book_names()
            system_prompt = self._build_system_prompt(english_books)
            session["conversation_history"] = [
                {"role": "system", "content": system_prompt}
            ]
            session["bible_version"] = bible_version

        current_history = list(session["conversation_history"])
        current_history.append({"role": "user", "content": user_query})

        # Build list of models to try
        models_to_try = [self.model_name]
        if self.fallback_model_name:
            models_to_try.append(self.fallback_model_name)

        # Try each model
        for model_idx, model_name in enumerate(models_to_try):
            if model_idx > 0:
                self.logger.info(f"Falling back to model: {model_name}")
            else:
                self.logger.info(f"Trying primary model: {model_name}")

            result = self._try_model_with_retries(
                model_name, session, user_query, current_history
            )

            if result.get("success"):
                # Success! Process the result
                valid_refs = result["valid_refs"]
                weights = result["weights"]
                raw_llm_output = result["raw_output"]
                api_result = result["api_result"]

                # If we've already shown a passage, penalize its helpfulness by 3
                for idx, ref in enumerate(valid_refs):
                    if ref in session["printed_passages"]:
                        weights[idx] = max(1, weights[idx] - 3)

                # Prefer perfect relevance/helpfulness (10/10) if present
                perfect_indices = [i for i, w in enumerate(weights) if w == 20]
                if perfect_indices:
                    selected_index = random.choice(perfect_indices)
                else:
                    selected_index = random.choices(
                        range(len(valid_refs)), weights=weights, k=1
                    )[0]

                passage_reference = valid_refs[selected_index]
                selected_weight = weights[selected_index]

                self.logger.info(
                    f"Selected reference: '{passage_reference}' (score: {selected_weight}). Query: '{user_query}'. Model: '{model_name}'"
                )

                parsed_bible_ref = bible_parser.parse_reference(passage_reference)
                if not parsed_bible_ref:
                    self.logger.warn(
                        f"Could not parse selected LLM reference: '{passage_reference}' from model '{model_name}'. Raw LLM: '{raw_llm_output}'"
                    )
                    # Try next model if available
                    if model_idx < len(models_to_try) - 1:
                        self.logger.info(
                            f"Trying next model due to invalid reference from {model_name}"
                        )
                        continue
                    self._update_conversation_history(
                        session, current_history, user_query, raw_llm_output
                    )
                    return {
                        "error": f"Could not parse LLM reference: '{passage_reference}'."
                    }, 500

                passage_text = bible_parser.get_passage(parsed_bible_ref)

                if passage_text is None:
                    self.logger.error(
                        f"Bible lookup failed for LLM reference: '{passage_reference}' from model '{model_name}'. Query: '{user_query}', LLM Raw: '{raw_llm_output}'"
                    )
                    # Try next model if available
                    if model_idx < len(models_to_try) - 1:
                        self.logger.info(
                            f"Trying next model due to failed Bible lookup from {model_name}"
                        )
                        continue
                    self._update_conversation_history(
                        session, current_history, user_query, raw_llm_output
                    )
                    return {
                        "error": f"Bible lookup failed for reference '{passage_reference}'."
                    }, 500

                self._update_conversation_history(
                    session,
                    current_history,
                    user_query,
                    raw_llm_output,
                    printed_passage=passage_reference,
                )
                return {
                    "response": passage_text,
                    "score": selected_weight,
                    "model_used": model_name,
                    "latency_ms": api_result["latency_ms"],
                    "prompt_tokens": api_result["prompt_tokens"],
                    "completion_tokens": api_result["completion_tokens"],
                }, 200

            # Handle errors - try fallback model if available, otherwise stop
            elif result.get("error") == "rate_limit":
                e = result["exception"]
                self.logger.error(f"OpenAI RateLimitError for {model_name}: {e}")
                # Try next model if available
                if model_idx < len(models_to_try) - 1:
                    self.logger.info(
                        f"Rate limited on {model_name}, trying fallback model"
                    )
                    continue
                # No more models to try
                self._update_conversation_history(
                    session,
                    current_history,
                    user_query,
                    "Error: Rate limit exceeded with all available LLM services.",
                )
                return {
                    "error": "Error: Rate limit exceeded with all available LLM services. Please try again later."
                }, 429
            elif result.get("error") == "api_error":
                e = result["exception"]
                self.logger.error(f"OpenAI APIError for {model_name}: {e}")
                # Try next model if available
                if model_idx < len(models_to_try) - 1:
                    self.logger.info(
                        f"API error on {model_name}, trying fallback model"
                    )
                    continue
                # No more models to try
                error_message = f"LLM service error: {e.message}"
                self._update_conversation_history(
                    session, current_history, user_query, f"Error: {error_message}"
                )
                return {"error": error_message}, e.status_code or 500

            # For other errors, try next model if available
            self.logger.warn(
                f"Model {model_name} failed with error: {result.get('error')}"
            )

        # All models failed
        final_error = (
            "Failed to get a valid response from LLM after trying all available models."
        )
        self._update_conversation_history(
            session,
            current_history,
            user_query,
            final_error,
        )
        return {"error": final_error}, 500
