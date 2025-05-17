# Development Guide

This document covers setting up a local development environment, running tests, and contributing to Divine Link.

## Requirements

- Python 3.x
- Flask
- python-dotenv
- openai
- requests
- See `requirements.txt` for specific version pins.

## Setup

1. **Clone the repository**
   ```bash
   git clone <your-repository-url>
   cd <your-repository-directory-name>
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment variables**
   Create a `.env` file in the project root and add:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   # Optional:
   # FLASK_APP=main.py
   # FLASK_DEBUG=True
   ```

## Running the Application

- **Via Python**
  ```bash
  python main.py
  ```

- **Via Flask CLI**
  ```bash
  flask run
  ```

Once running, open your browser at `http://127.0.0.1:5000`.

## Testing

Run unit and integration tests with pytest. Tests requiring `OPENROUTER_API_KEY` will be skipped if the key is not set.

## Pre-commit Hooks

This project uses pre-commit for code style and linting.
Install and run:
