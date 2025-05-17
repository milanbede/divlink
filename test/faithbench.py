import unittest
from unittest.mock import MagicMock
import os
import time  # Added for latency measurement
from dotenv import load_dotenv
from openai import OpenAI
import matplotlib.pyplot as plt  # Added for radar chart
import numpy as np  # Added for radar chart

from concurrent.futures import ThreadPoolExecutor, as_completed

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
        "meta-llama/llama-4-maverick:free",
        "meta-llama/llama-4-scout:free",
        "meta-llama/llama-3.3-8b-instruct:free",
        "microsoft/phi-4-reasoning-plus:free",
        "deepseek/deepseek-chat-v3-0324:free",
        "deepseek/deepseek-r1:free",
        "qwen/qwen3-235b-a22b:free",
        "google/gemma-3-27b-it:free",
        "google/gemma-3-12b-it:free",
        "mistralai/mistral-nemo:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "qwen/qwen3-30b-a3b:free",
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
        overall_model_metrics = {}

        # Run model tests in parallel threads for faster execution
        def run_model(model_name):
            handler = LLMHandler(
                client=self.openai_client,
                logger=self.mock_logger,
                bible_parser=self.bible_parser,
                model_name=model_name,
            )

            model_total_latency = 0.0
            model_prompt_count_for_latency = 0
            model_specific_success_count = 0
            category_success_counts = {cat: 0 for cat in all_test_data_sources}
            category_total_counts = {cat: 0 for cat in all_test_data_sources}

            for case in all_test_cases:
                category = case["category"]
                category_total_counts[category] += 1

                start = time.time()
                result, status_code = handler.get_llm_bible_reference(
                    session={}, user_query=case["prompt"]
                )
                latency = time.time() - start
                model_total_latency += latency
                model_prompt_count_for_latency += 1

                # Basic response checks
                assert status_code == 200
                assert "response" in result

                returned = (
                    result["response"].splitlines()[0].strip()
                    if result["response"]
                    else ""
                )
                # Check if any expected reference matches
                found = False
                for exp in case["expected_references"]:
                    ref_obj = self.bible_parser.parse_reference(exp)
                    if ref_obj:
                        passage = self.bible_parser.get_passage(ref_obj)
                        header = (
                            passage.splitlines()[0].strip()
                            if not passage.startswith("Error")
                            else ""
                        )
                        if header == returned:
                            found = True
                            break
                    if returned == exp:
                        found = True
                        break

                if found:
                    model_specific_success_count += 1
                    category_success_counts[category] += 1

            avg_latency = (
                (model_total_latency / model_prompt_count_for_latency)
                if model_prompt_count_for_latency
                else 0
            )
            success_rate = (
                (model_specific_success_count / len(all_test_cases)) * 100
                if all_test_cases
                else 0
            )
            category_rates = {
                c: (
                    category_success_counts[c] / category_total_counts[c] * 100
                    if category_total_counts[c]
                    else 0
                )
                for c in all_test_data_sources
            }

            return model_name, {
                "overall_success_rate": success_rate,
                "avg_latency_sec": avg_latency,
                "category_success_rates": category_rates,
                "total_prompts_tested": len(all_test_cases),
                "total_successful": model_specific_success_count,
                "detailed_results": [],
                "cost_usd": "N/A",
            }

        # Execute model tests concurrently
        with ThreadPoolExecutor(
            max_workers=min(len(self.MODELS_TO_TEST), 5)
        ) as executor:
            futures = {executor.submit(run_model, m): m for m in self.MODELS_TO_TEST}
            for future in as_completed(futures):
                mdl = futures[future]
                try:
                    name, metrics = future.result()
                except AssertionError as ae:
                    self.fail(f"Model {mdl} assertion failed: {ae}")
                except Exception as e:
                    self.fail(f"Model {mdl} failed with exception: {e}")
                else:
                    overall_model_metrics[name] = metrics

        # After concurrent execution, produce summary
        print("\n--- FaithBench Overall Comparative Summary ---")
        header = "| Model                                  | Overall Success Rate | Avg Latency (s/prompt) | Avg Cost (USD) |"
        print(header)
        print("|" + "-" * (len(header) - 2) + "|")
        for model_name_key, metrics in overall_model_metrics.items():
            # Truncate or pad model name for table display
            display_model_name = (
                (model_name_key[:36] + "..")
                if len(model_name_key) > 38
                else model_name_key.ljust(38)
            )
            print(
                f"| {display_model_name} | "
                f"{metrics['overall_success_rate']:>19.2f}% | "
                f"{metrics['avg_latency_sec']:>21.4f} | "
                f"{metrics['cost_usd']:>14} |"
            )
        print(
            "----------------------------------------------------------------------------------------------------------\n"
        )

        categories_for_chart = list(all_test_data_sources.keys())
        if categories_for_chart:  # Ensure there are categories before trying to plot
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
            values = [
                metrics_data["category_success_rates"].get(cat, 0) for cat in categories
            ]
            values += values[:1]  # Complete the loop for values
            ax.plot(angles, values, linewidth=2, linestyle="solid", label=model_name)
            ax.fill(angles, values, alpha=0.25)

        ax.set_yticks(np.arange(0, 101, 20))  # Y-axis ticks from 0 to 100, every 20%
        ax.set_ylim(0, 100)  # Y-axis limit
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)

        # Move title and legend
        plt.title("Model Performance by Category (Success Rate %)", size=16, y=1.12)
        ax.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, -0.15),
            ncol=min(3, len(model_metrics)),
        )  # Adjust legend position

        chart_filename = "faithbench_radar_chart.png"
        try:
            plt.tight_layout(pad=2.0)  # Add padding
            plt.savefig(chart_filename)
            self.mock_logger.info(f"Radar chart saved to {chart_filename}")
            print(f"Radar chart saved to {chart_filename}")
        except Exception as e:
            self.mock_logger.error(f"Failed to save radar chart: {e}")
            print(f"Failed to save radar chart: {e}")
        plt.close(fig)  # Close the figure to free memory


if __name__ == "__main__":
    unittest.main()
