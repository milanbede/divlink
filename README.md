# Bible Terminal

A terminal-style web application for querying Bible passages using an LLM.

## Features

- Query Bible passages using natural language.
- Leverages Large Language Models (LLMs) for understanding queries.
- Provides relevant Bible verses based on user input.
- Terminal-style web interface.
- Random Psalm feature.

## Requirements

- Python 3.x
- Flask
- python-dotenv
- openai
- requests

See `requirements.txt` for specific versions.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-directory-name>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the root directory of the project and add your API keys and any other configurations:
    ```env
    OPENROUTER_API_KEY=your_openrouter_api_key_here
    # FLASK_APP=main.py (Optional, can be set if not using `python main.py`)
    # FLASK_DEBUG=True (Optional, for development)
    ```
    Replace `your_openrouter_api_key_here` with your actual OpenRouter API key.

## Usage

1.  **Ensure your environment variables are set** (see Setup step 4).

2.  **Run the Flask application:**
    From the project's root directory:
    ```bash
    python main.py
    ```
    Alternatively, if you have `FLASK_APP` set in your `.env` or environment:
    ```bash
    flask run
    ```

3.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the address shown in your terminal).

## TODO

- [ ] Implement soft throttling for API requests.
- [ ] Improve model selection (e.g., allow user choice or dynamic selection based on query).
- [ ] Add caching for LLM responses and/or Bible passages to reduce API calls and improve speed.
- [ ] Implement username Easter Eggs for a bit of fun.

## License

The source code of this project is licensed under the terms described in `LICENSE.txt`.  
The King James Version (KJV) Bible texts included in the `data/books` directory are in the public domain and are not subject to the terms of this license.
