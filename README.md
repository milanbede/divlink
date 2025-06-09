# Divine Link

Find hope, comfort, and guidance in the Word of God.

Divine Link is your personalized gateway to Scripture, crafted to bring solace to the brokenhearted, answers to the curious, and encouragement to all seeking spiritual connection. Whether you're navigating life's challenges or simply exploring faith, Divine Link offers:

-[x] Intuitive natural language search: Ask in your own words and discover relevant Bible passages.
-[x] Random Psalm: Draw daily inspiration from the timeless poetry of the Psalms.
-[x] Lightweight, hassle-free experience: No installation—just open your browser and begin your journey.
-[ ] ~~Interpretation of God's word by a machine.~~ No, just the Word itself.
-[x] API for integration into third-party sites.
-[ ] Semantic caching to speed it up.
-[ ] Offline version to avoid sending data.
-[ ] Apps for Android/iOS.

### [Live Demo](https://bible.vibefare.com)

## How It Works
1. Pour out your heart: Type in your thoughts, struggles, or questions.
2. Receive guidance: Our AI-powered guide connects you to the most meaningful verses.
3. Reflect and grow: Meditate on the passages that resonate with you.

## Get Started Now
Visit the Live Demo, share what’s on your mind, and let Divine Link illuminate your path.

## Contribute & Develop
For setup instructions, contribution guidelines, and detailed developer notes, see DEVELOPMENT.md.

## License
This project is licensed under the terms described in LICENSE.txt. King James Version (KJV) texts included here are in the public domain.

## X Poster Cloud Run Job

This project includes a feature to post a "Verse of the Day" to X (formerly Twitter) using a scheduled Google Cloud Run job.

### Prerequisites

1.  **X Developer Account & App**:
    *   You need an X developer account.
    *   Create a new App within a Project in the X Developer Portal.
    *   Generate the following credentials for your App (ensure you have OAuth 1.0a read and write permissions):
        *   API Key (Consumer Key)
        *   API Key Secret (Consumer Secret)
        *   Access Token
        *   Access Token Secret

2.  **Google Cloud Project**:
    *   A Google Cloud Project with billing enabled.
    *   The Cloud Run API and Cloud Scheduler API must be enabled.
    *   Google Cloud SDK (gcloud CLI) installed and configured locally if you plan to deploy from your machine.

### Setup and Deployment

1.  **Environment Variables for X API**:
    *   The application reads X API credentials from environment variables:
        *   `X_CONSUMER_KEY`
        *   `X_CONSUMER_SECRET`
        *   `X_ACCESS_TOKEN`
        *   `X_ACCESS_TOKEN_SECRET`
    *   For local testing, you can create a `.env` file in the project root and add these variables:
        ```
        X_CONSUMER_KEY="YOUR_X_CONSUMER_KEY"
        X_CONSUMER_SECRET="YOUR_X_CONSUMER_SECRET"
        X_ACCESS_TOKEN="YOUR_X_ACCESS_TOKEN"
        X_ACCESS_TOKEN_SECRET="YOUR_X_ACCESS_TOKEN_SECRET"
        # You might also need OPENROUTER_API_KEY for the verse fetching
        OPENROUTER_API_KEY="YOUR_OPENROUTER_API_KEY"
        FLASK_SECRET_KEY="any_random_strong_key"
        ```
    *   **Important**: Replace placeholder values with your actual credentials. Do not commit the `.env` file with real credentials to version control if it's not already in `.gitignore`.

2.  **Build the Docker Image**:
    *   Navigate to the project's root directory (where the `Dockerfile` is located).
    *   Build the Docker image and tag it appropriately. Replace `[PROJECT_ID]` with your Google Cloud Project ID and `[JOB_NAME]` with your desired job name (e.g., `verse-poster`).
        ```bash
        docker build -t gcr.io/[PROJECT_ID]/[JOB_NAME]:latest .
        ```

3.  **Push the Docker Image to Google Container Registry (GCR)**:
    *   (Ensure Docker is configured to authenticate with GCR: `gcloud auth configure-docker`)
        ```bash
        docker push gcr.io/[PROJECT_ID]/[JOB_NAME]:latest
        ```
    *   Alternatively, you can use Artifact Registry. Adjust the image path accordingly (e.g., `us-central1-docker.pkg.dev/[PROJECT_ID]/[REPO_NAME]/[JOB_NAME]:latest`).

4.  **Deploy to Google Cloud Run as a Job**:
    *   Deploy the container image as a Cloud Run job. Replace `[JOB_NAME]`, `[IMAGE_PATH]` (e.g., `gcr.io/[PROJECT_ID]/[JOB_NAME]:latest`), and `[REGION]` with your specific values.
    *   You will also need to set the X API environment variables during deployment.
        ```bash
        gcloud run jobs deploy [JOB_NAME] \
            --image [IMAGE_PATH] \
            --region [REGION] \
            --set-env-vars X_CONSUMER_KEY="YOUR_X_CONSUMER_KEY" \
            --set-env-vars X_CONSUMER_SECRET="YOUR_X_CONSUMER_SECRET" \
            --set-env-vars X_ACCESS_TOKEN="YOUR_X_ACCESS_TOKEN" \
            --set-env-vars X_ACCESS_TOKEN_SECRET="YOUR_X_ACCESS_TOKEN_SECRET" \
            # Add OPENROUTER_API_KEY and FLASK_SECRET_KEY as well if needed by the job execution context
            --set-env-vars OPENROUTER_API_KEY="YOUR_OPENROUTER_API_KEY" \
            --set-env-vars FLASK_SECRET_KEY="your_flask_secret_key_for_job_context"
            # Adjust other parameters like memory, CPU, tasks as needed
        ```
    *   Note: `FLASK_SECRET_KEY` is used by Flask sessions; while `run_daily_job.py` uses `app.test_client()`, which might initialize parts of Flask that expect it, it's less critical for a non-interactive job but good to set. `OPENROUTER_API_KEY` is crucial for fetching the verse.

5.  **Schedule the Job with Google Cloud Scheduler**:
    *   Create a Cloud Scheduler job to trigger the Cloud Run job periodically (e.g., once a day).
    *   **Target Type**: `HTTP` (to invoke the Cloud Run job execution endpoint) or `Cloud Run Job` (newer integration). The `Cloud Run Job` target is preferred.
    *   **Frequency**: Use a cron expression (e.g., `0 9 * * *` for 9 AM daily).
    *   **Cloud Run Job**: Select the job you deployed in the previous step.
    *   Refer to the [Google Cloud Scheduler documentation](https://cloud.google.com/scheduler/docs/creating) and [Triggering Cloud Run jobs with Cloud Scheduler](https://cloud.google.com/run/docs/triggering/using-scheduler) for detailed instructions.

    Example gcloud command to create a scheduler job (ensure you have necessary permissions and the service account for the scheduler has rights to invoke the Cloud Run job):
    ```bash
    gcloud scheduler jobs create run [SCHEDULER_JOB_NAME] \
        --schedule "0 9 * * *" \ # Example: 9 AM daily
        --location [REGION] \
        --run-job-name [CLOUD_RUN_JOB_NAME] \
        --run-job-region [REGION] \
        --description "Triggers the Verse of the Day X Poster job."
        # Ensure the service account used by Cloud Scheduler has 'run.jobs.run' permission
    ```

### Local Testing of the Job Script
You can test the `run_daily_job.py` script locally if you have Python and the dependencies installed, and the `.env` file is configured:
```bash
python run_daily_job.py
```
This will attempt to fetch a verse and post it to X, using the credentials in your `.env` file. Check the console output for logs.
