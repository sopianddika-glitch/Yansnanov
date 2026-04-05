# Yansnanov Bot

Yansnanov Bot is a production-ready Telegram bot built with Python, `python-telegram-bot` v20, Gemini AI, and the Binance public API. The project uses a clean modular structure, async Telegram handlers, centralized logging, and a Railway-ready worker deployment setup.

## Features

- `/start` displays a welcome message and command list
- `/ai <prompt>` sends a prompt to Gemini and returns the generated response
- `/price <symbol>` fetches the latest Binance `USDT` spot price for a token such as `BTC` or `ETH`
- `/warn` adds a reply-based warning count for community moderation
- Centralized logging and a global error handler for safer production behavior

## Project Structure

```text
Yansnanov/
|-- main.py
|-- config.py
|-- requirements.txt
|-- Procfile
|-- README.md
|-- handlers/
|   |-- start.py
|   |-- ai.py
|   |-- market.py
|   |-- community.py
|   |-- errors.py
|-- services/
|   |-- ai_service.py
|   |-- market_service.py
|-- utils/
|   |-- logger.py
|   |-- middleware.py
```

## Installation

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Export the required environment variables.
5. Run the bot.

```bash
git clone <your-repository-url>
cd Yansnanov
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="your-telegram-bot-token"
export AI_KEY="your-gemini-api-key"
python main.py
```

On Windows PowerShell, use:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
$env:BOT_TOKEN="your-telegram-bot-token"
$env:AI_KEY="your-gemini-api-key"
pip install -r requirements.txt
python main.py
```

## Environment Variables

The bot requires these variables at startup:

- `BOT_TOKEN`: Telegram BotFather token
- `AI_KEY`: Gemini API key used by `google-genai`

The application fails fast if either variable is missing.

## Commands

- `/start`
- `/ai <prompt>`
- `/price <symbol>`
- `/warn` used as a reply to another user's message, optionally followed by a reason

Examples:

```text
/ai Explain Bitcoin market cycles in simple terms
/price btc
/warn Please keep the chat respectful
```

## Railway Deployment

1. Push this project to GitHub.
2. Create a new Railway project and connect the GitHub repository.
3. In Railway, add these environment variables:
   - `BOT_TOKEN`
   - `AI_KEY`
4. Ensure the project is deployed as a worker service.
5. Railway will use the `Procfile` entry below to start the bot:

```text
worker: python3 main.py
```

## Notes

- The warning system stores counts in memory, so warnings reset when the process restarts.
- Binance prices are pulled from the public ticker endpoint and do not require authentication.
- Gemini responses are generated through the Google Gen AI SDK with Gemini Flash models.
