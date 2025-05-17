import requests
import json
import random


class RandomSeeder:
    def __init__(self, logger):
        self.logger = logger

    def _get_drand_seed(self):
        """Fetches randomness from drand and returns it as an integer seed."""
        try:
            response = requests.get(
                "https://drand.cloudflare.com/public/latest", timeout=5
            )
            response.raise_for_status()
            data = response.json()
            randomness_hex = data.get("randomness")
            if randomness_hex:
                self.logger.info(
                    f"Successfully fetched seed from drand. Round: {data.get('round')}"
                )
                return int(randomness_hex, 16)
            else:
                self.logger.error("Drand response did not contain 'randomness' field.")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Could not fetch seed from drand: {e}.")
            return None
        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f"Error processing drand response: {e}.")
            return None

    def _get_nist_seed(self):
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
                self.logger.info("Successfully fetched seed from NIST beacon.")
                return int(randomness_hex, 16)
            else:
                self.logger.error(
                    "NIST beacon JSON response did not contain 'pulse.outputValue' field or it was empty."
                )
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Could not fetch seed from NIST beacon: {e}.")
            return None
        except (
            json.JSONDecodeError,
            ValueError,
            TypeError,
            KeyError,
        ) as e:  # Updated exception handling
            self.logger.error(f"Error processing NIST beacon JSON response: {e}.")
            return None

    def initialize_seeding(self):
        """Initializes the random number generator using seeds from drand and NIST."""
        drand_seed = self._get_drand_seed()
        nist_seed = self._get_nist_seed()

        final_seed = None

        if drand_seed is not None and nist_seed is not None:
            # Combine seeds if both are available (e.g., XOR)
            final_seed = drand_seed ^ nist_seed
            self.logger.info("Combined seeds from drand and NIST.")
        elif drand_seed is not None:
            final_seed = drand_seed
            self.logger.info("Using seed from drand only.")
        elif nist_seed is not None:
            final_seed = nist_seed
            self.logger.info("Using seed from NIST only.")
        else:
            self.logger.error(
                "Failed to fetch seed from both drand and NIST. Using default random seed."
            )

        if final_seed is not None:
            random.seed(final_seed)
            self.logger.info(
                "Random number generator seeded with value derived from external beacons."
            )
        else:
            # Python's random module is seeded by default if random.seed() is not called.
            self.logger.info(
                "Random number generator using default (time-based or OS-specific) seed."
            )
