import logging
from main import app  # Import the Flask app instance
from x_poster import XPoster # Import XPoster to ensure it's initialized if needed, though main.py already does this.
from dotenv import load_dotenv

# Configure basic logging for the job
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def trigger_verse_of_the_day_and_post():
    '''
    Makes a request to the /api/verse_of_the_day endpoint
    to trigger the verse fetching and X posting logic.
    '''
    logger.info("Starting daily job: Fetch verse and post to X.")

    # Load environment variables from .env file for local execution
    # In Cloud Run, these will be set in the service configuration
    load_dotenv()

    # The XPoster is initialized when main.py is imported (and thus app is created).
    # We can directly use the test client to simulate a request.
    with app.test_client() as client:
        try:
            logger.info("Making GET request to /api/verse_of_the_day")
            response = client.get('/api/verse_of_the_day') # Make sure this path is correct based on your Flask-RESTX prefix

            if response.status_code == 200:
                logger.info(f"Successfully called /verse_of_the_day endpoint. Status: {response.status_code}")
                # The endpoint itself now handles logging for X posting success/failure.
                # response.json will contain the verse data.
                logger.info(f"Response data: {response.json}")
            else:
                logger.error(f"Failed to call /verse_of_the_day endpoint. Status: {response.status_code}, Response: {response.data}")
        except Exception as e:
            logger.error(f"An error occurred during the job: {e}", exc_info=True)

    logger.info("Daily job finished.")

if __name__ == '__main__':
    trigger_verse_of_the_day_and_post()
