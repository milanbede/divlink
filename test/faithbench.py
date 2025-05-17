import unittest
from unittest.mock import MagicMock
import os
import time # Added for latency measurement
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
import matplotlib.pyplot as plt # Added for radar chart
import numpy as np # Added for radar chart
from math import pi # Added for radar chart

from llm_handler import LLMHandler
from bible_parser import BibleParser

# Import test cases from individual category files
from .faithbench_anger import ANGER_TEST_CASES
from .faithbench_apathy import APATHY_TEST_CASES
from .faithbench_despair import DESPAIR_TEST_CASES
from .faithbench_gluttony import GLUTTONY_TEST_CASES
from .faithbench_greed import GREED_TEST_CASES
from .faithbench_lust import LUST_TEST_CASES
from .faithbench_pride import PRIDE_TEST_CASES
from .faithbench_vanity import VANITY_TEST_CASES

# Load environment variables from .env file for API Key
load_dotenv()

# Skip integration tests if OPENROUTER_API_KEY is not set
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


@unittest.skipIf(
    not OPENROUTER_API_KEY, "OPENROUTER_API_KEY not set, skipping integration tests."
)
class TestFaithBenchIntegration(unittest.TestCase):
    MODELS_TO_TEST = [
        "deepseek/deepseek-r1-distill-qwen-32b:free",
        # Add other model identifiers from OpenRouter here, e.g.:
        # "mistralai/mistral-7b-instruct:free",
        # "anthropic/claude-3-haiku-20240307:beta",
        # "google/gemma-7b-it:free",
    ]

    def setUp(self):
        self.mock_logger = MagicMock()

        self.bible_parser = BibleParser(logger=self.mock_logger)
        self.assertTrue(
            self.bible_parser.is_data_loaded(),
            "Bible data (data/en_kjv.json) failed to load for tests. "
            "Ensure tests are run from the project root and the data file exists at 'data/en_kjv.json'.",
        )

        # Initialize real OpenAI client for OpenRouter
        self.openai_client = OpenAI(
            api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1"
        )

        # LLMHandler will be initialized per model in the test method
        self.llm_handler = None

    def test_faithbench_prompts_integration(self):
        # Aggregate all test cases and add category information
        all_test_data_sources = {
            "anger": ANGER_TEST_CASES,
            "apathy": APATHY_TEST_CASES,
            "despair": DESPAIR_TEST_CASES,
            "gluttony": GLUTTONY_TEST_CASES,
            "greed": GREED_TEST_CASES,
            "lust": LUST_TEST_CASES,
            "pride": PRIDE_TEST_CASES,
            "vanity": VANITY_TEST_CASES,
        }

        all_test_cases = []
        for category, cases_list in all_test_data_sources.items():
            if cases_list:  # Ensure the list is not None or empty
                for case_content in cases_list:
                    case_copy = case_content.copy()
                    case_copy["category"] = category
                    all_test_cases.append(case_copy)
            else:
                self.mock_logger.warning(
                    f"No test cases found for category: {category}"
                )

        if not all_test_cases:
            self.skipTest(
                "No FaithBench test cases were loaded from category files. Skipping integration test."
            )

        overall_model_metrics = {} # Stores metrics for all models

        for model_name in self.MODELS_TO_TEST:
            self.mock_logger.info(f"\n--- Testing Model: {model_name} ---")
            self.llm_handler = LLMHandler(
                client=self.openai_client,
                logger=self.mock_logger,
                bible_parser=self.bible_parser,
                model_name=model_name,
            )

            model_specific_success_count = 0
            model_total_latency = 0.0
            model_prompt_count_for_latency = 0
            model_results_summary_lines = []
            
            category_success_counts = {category: 0 for category in all_test_data_sources.keys()}
            category_total_counts = {category: 0 for category in all_test_data_sources.keys()}

            for i, case in enumerate(tqdm(all_test_cases, desc=f"FaithBench ({model_name})")):
                with self.subTest(model=model_name, category=case["category"], prompt=case["prompt"]):
                    current_category = case['category']
                    category_total_counts[current_category] += 1
                    
                    mock_session = {}  # Simulate Flask session

                    self.mock_logger.info(
                        f"Model: {model_name}, Test Case {i+1}/{len(all_test_cases)}: Category: {current_category}, Prompt: '{case['prompt']}'"
                    )

                    start_time = time.time()
                    result, status_code = self.llm_handler.get_llm_bible_reference(
                        session=mock_session, user_query=case["prompt"]
                    )
                    end_time = time.time()
                    latency = end_time - start_time
                    model_total_latency += latency
                    model_prompt_count_for_latency += 1

                    self.assertEqual(
                        status_code,
                        200,
                        f"Model '{model_name}', Prompt '{case['prompt']}': Expected status 200, got {status_code}. Result: {result}",
                    )
                    self.assertIn(
                        "response",
                        result,
                        f"Model '{model_name}', Prompt '{case['prompt']}': Result missing 'response' key. Result: {result}",
                    )

                    passage_text = result.get("response", "")
                    returned_reference_line = (
                        passage_text.splitlines()[0].strip() if passage_text else ""
                    )

                    is_expected_reference_found = False
                    matched_reference = None
                    for expected_ref in case["expected_references"]:
                        parsed_expected_ref_obj = self.bible_parser.parse_reference(expected_ref)
                        canonical_expected_ref_header = ""
                        if parsed_expected_ref_obj:
                            passage_or_error = self.bible_parser.get_passage(parsed_expected_ref_obj)
                            if not (passage_or_error.startswith("Error:") or 
                                    passage_or_error.startswith("Book '") or 
                                    passage_or_error.startswith("Chapter ") or 
                                    passage_or_error.startswith("No verses found")):
                                canonical_expected_ref_header = passage_or_error.splitlines()[0].strip()
                            else:
                                self.mock_logger.warning(
                                    f"Model '{model_name}': Could not form canonical header for expected_ref '{expected_ref}'. Error: {passage_or_error}"
                                )
                                if returned_reference_line == expected_ref.strip():
                                    is_expected_reference_found = True
                                    matched_reference = expected_ref
                                    break
                                continue
                        
                        if returned_reference_line == canonical_expected_ref_header:
                            is_expected_reference_found = True
                            matched_reference = expected_ref
                            break
                        elif not canonical_expected_ref_header and returned_reference_line == expected_ref.strip():
                            is_expected_reference_found = True
                            matched_reference = expected_ref
                            break
                    
                    if is_expected_reference_found:
                        model_specific_success_count += 1
                        category_success_counts[current_category] += 1
                        model_results_summary_lines.append(
                            f"PASS ({current_category}): Prompt: \"{case['prompt']}\" -> Matched: \"{matched_reference}\" (Returned: \"{returned_reference_line}\")"
                        )
                        self.mock_logger.info(
                            f"Model '{model_name}' PASS ({current_category}): Prompt: \"{case['prompt']}\" -> Matched: \"{matched_reference}\""
                        )
                    else:
                        model_results_summary_lines.append(
                            f"FAIL ({current_category}): Prompt: \"{case['prompt']}\" -> Expected one of {case['expected_references']}, Got: \"{returned_reference_line}\""
                        )
                        self.mock_logger.warning(
                            f"Model '{model_name}' FAIL ({current_category}): Prompt: \"{case['prompt']}\" -> Expected {case['expected_references']}, Got: \"{returned_reference_line}\""
                        )

                    self.assertTrue(
                        is_expected_reference_found,
                        f"Model '{model_name}': LLM did not return a passage for one of the expected references "
                        f"{case['expected_references']}.\n"
                        f"Prompt: '{case['prompt']}'\n"
                        f"LLMHandler returned passage starting with: '{returned_reference_line}'\n"
                        f"Full passage returned (first 200 chars): '{passage_text[:200]}...'",
                    )
            
            # After all prompts for the current model
            avg_latency = model_total_latency / model_prompt_count_for_latency if model_prompt_count_for_latency > 0 else 0
            overall_success_rate_model = (model_specific_success_count / len(all_test_cases)) * 100 if len(all_test_cases) > 0 else 0
            
            category_success_rates_model = {}
            for cat, count in category_success_counts.items():
                total_in_cat = category_total_counts[cat]
                category_success_rates_model[cat] = (count / total_in_cat) * 100 if total_in_cat > 0 else 0

            overall_model_metrics[model_name] = {
                "overall_success_rate": overall_success_rate_model,
                "avg_latency_sec": avg_latency,
                "category_success_rates": category_success_rates_model,
                "total_prompts_tested": len(all_test_cases),
                "total_successful": model_specific_success_count,
                "detailed_results": model_results_summary_lines,
                "cost_usd": "N/A (Cost calculation not yet implemented)" # Placeholder for cost
            }

            print(f"\n--- Summary for Model: {model_name} ---")
            for res_line in model_results_summary_lines:
                print(res_line)
            print(f"Overall Success Rate: {model_specific_success_count}/{len(all_test_cases)} ({overall_success_rate_model:.2f}%)")
            print(f"Average Latency: {avg_latency:.4f} seconds per prompt")
            print("Category Success Rates:")
            for cat, rate in category_success_rates_model.items():
                count = category_success_counts[cat]
                total = category_total_counts[cat]
                print(f"  {cat}: {rate:.2f}% ({count}/{total})")
            print("-----------------------------------------\n")

        # After all models have been tested
        print("\n--- FaithBench Overall Comparative Summary ---")
        header = "| Model                                  | Overall Success Rate | Avg Latency (s/prompt) | Avg Cost (USD) |"
        print(header)
        print("|" + "-" * (len(header) - 2) + "|")
        for model_name_key, metrics in overall_model_metrics.items():
            # Truncate or pad model name for table display
            display_model_name = (model_name_key[:36] + '..') if len(model_name_key) > 38 else model_name_key.ljust(38)
            print(
                f"| {display_model_name} | "
                f"{metrics['overall_success_rate']:>19.2f}% | "
                f"{metrics['avg_latency_sec']:>21.4f} | "
                f"{metrics['cost_usd']:>14} |"
            )
        print("----------------------------------------------------------------------------------------------------------\n")

        categories_for_chart = list(all_test_data_sources.keys())
        if categories_for_chart: # Ensure there are categories before trying to plot
             self._generate_radar_chart(overall_model_metrics, categories_for_chart)
        else:
            self.mock_logger.warning("No categories found for radar chart generation.")


    def _generate_radar_chart(self, model_metrics, categories):
        num_vars = len(categories)
        if num_vars == 0:
            self.mock_logger.warning("Cannot generate radar chart with no categories.")
            return

        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]  # Complete the loop for a closed shape

        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

        # Plot each model's data
        for model_name, metrics_data in model_metrics.items():
            values = [metrics_data['category_success_rates'].get(cat, 0) for cat in categories]
            values += values[:1] # Complete the loop for values
            ax.plot(angles, values, linewidth=2, linestyle='solid', label=model_name)
            ax.fill(angles, values, alpha=0.25)

        ax.set_yticks(np.arange(0, 101, 20)) # Y-axis ticks from 0 to 100, every 20%
        ax.set_ylim(0, 100) # Y-axis limit
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        
        # Move title and legend
        plt.title('Model Performance by Category (Success Rate %)', size=16, y=1.12)
        ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.15), ncol=min(3, len(model_metrics))) # Adjust legend position

        chart_filename = "faithbench_radar_chart.png"
        try:
            plt.tight_layout(pad=2.0) # Add padding
            plt.savefig(chart_filename)
            self.mock_logger.info(f"Radar chart saved to {chart_filename}")
            print(f"Radar chart saved to {chart_filename}")
        except Exception as e:
            self.mock_logger.error(f"Failed to save radar chart: {e}")
            print(f"Failed to save radar chart: {e}")
        plt.close(fig) # Close the figure to free memory


if __name__ == "__main__":
    unittest.main()
