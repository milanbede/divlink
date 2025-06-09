import os
import tweepy
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class XPoster:
    def __init__(self):
        self.consumer_key = os.getenv("X_CONSUMER_KEY")
        self.consumer_secret = os.getenv("X_CONSUMER_SECRET")
        self.access_token = os.getenv("X_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        if not all([self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret]):
            logger.error("X API credentials not found in environment variables.")
            self.client = None
        else:
            try:
                self.client = tweepy.Client(
                    consumer_key=self.consumer_key,
                    consumer_secret=self.consumer_secret,
                    access_token=self.access_token,
                    access_token_secret=self.access_token_secret,
                    wait_on_rate_limit=True
                )
                logger.info("X API client initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing X API client: {e}")
                self.client = None

    def post_tweet(self, text: str) -> bool:
        if not self.client:
            logger.error("X API client not initialized. Cannot post tweet.")
            return False

        if not text:
            logger.error("Tweet text cannot be empty.")
            return False

        # Truncate text if it's too long for X (currently 280 characters)
        # X API might handle this, but good to be proactive.
        max_length = 280
        if len(text) > max_length:
            logger.warning(f"Tweet text exceeds {max_length} characters. Truncating.")
            text = text[:max_length]

        try:
            response = self.client.create_tweet(text=text)
            if response.data and response.data.get('id'):
                logger.info(f"Tweet posted successfully! Tweet ID: {response.data['id']}")
                return True
            else:
                logger.error(f"Failed to post tweet. Response: {response.errors}")
                return False
        except tweepy.TweepyException as e:
            logger.error(f"Error posting tweet: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while posting tweet: {e}")
            return False

if __name__ == '__main__':
    # This is for basic testing of the module directly.
    # Ensure X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET are set in your environment.
    logger.info("Testing XPoster module...")
    poster = XPoster()
    if poster.client:
        test_tweet_text = "Hello from my new X bot! This is a test tweet. #Python #XAPI"
        logger.info(f"Attempting to post test tweet: '{test_tweet_text}'")
        if poster.post_tweet(test_tweet_text):
            logger.info("Test tweet posted successfully via XPoster.")
        else:
            logger.error("Failed to post test tweet via XPoster.")
    else:
        logger.error("XPoster client not available for testing. Check credentials.")
