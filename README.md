# Yansnanov Bot

Yansnanov Bot is a modular Telegram trading and AI bot built with `python-telegram-bot` v20, `google-genai`, and a hybrid Binance plus Bybit market layer. The project is organized around thin async handlers, reusable services, centralized formatting helpers, and Railway-friendly startup behavior.

## Features

- Core utilities: `/start`, `/help`, `/id`, `/ping`, `/time`
- AI tools: `/ai`, `/summarize`, `/translate`
- Market intelligence: `/price`, `/market`, `/signal`, `/summary`, `/report`, `/scan`
- Alerting: `/alert`, `/alertset`, `/alertscan`
- Sentiment and news: `/sentiment`, `/news`
- Admin utilities: `/rules`, `/warn`, `/clean`, `/pin`
- Global error handling, centralized logging, and environment-based config loading

## Project Structure

```text
Yansnanov/
|-- main.py
|-- config.py
|-- requirements.txt
|-- Procfile
|-- README.md
|-- handlers/
|   |-- admin.py
|   |-- ai.py
|   |-- alert.py
|   |-- core.py
|   |-- errors.py
|   |-- market.py
|   |-- sentiment.py
|-- services/
|   |-- ai_service.py
|   |-- alert_engine.py
|   |-- alert_rules.py
|   |-- alert_service.py
|   |-- binance_service.py
|   |-- bybit_service.py
|   |-- data_binance.py
|   |-- data_bybit.py
|   |-- hybrid_service.py
|   |-- indicators.py
|   |-- market_engine.py
|   |-- news_service.py
|   |-- report_generator.py
|   |-- report_service.py
|   |-- sentiment_service.py
|-- utils/
|   |-- cache.py
|   |-- config_loader.py
|   |-- formatting.py
|   |-- logger.py
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
export AI_KEY="your-google-genai-key"
python main.py
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
$env:BOT_TOKEN="your-telegram-bot-token"
$env:AI_KEY="your-google-genai-key"
pip install -r requirements.txt
python main.py
```

## Environment Variables

Required:

- `BOT_TOKEN`
- `AI_KEY`

Optional:

- `BINANCE_KEY`
- `BINANCE_SECRET`
- `BYBIT_KEY`
- `BYBIT_SECRET`
- `NEWS_API_KEY`
- `APP_TIMEZONE`

## Commands

- `/start`
- `/help`
- `/id`
- `/ping`
- `/time`
- `/ai <prompt>`
- `/summarize <text>`
- `/translate <language> | <text>`
- `/price <symbol>`
- `/market <symbol>`
- `/signal <symbol>`
- `/summary <symbol>`
- `/report <symbol>`
- `/scan`
- `/alert <symbol>`
- `/alertset <symbol> <type>`
- `/alertscan`
- `/sentiment <symbol>`
- `/news [symbol]`
- `/rules`
- `/warn` as a reply
- `/clean` as a reply
- `/pin` as a reply

## Railway Deployment

1. Push this repository to GitHub.
2. Create a Railway project and connect the repository.
3. Add the required environment variables in Railway.
4. Deploy as a worker service.
5. Railway starts the bot with:

```text
worker: python3 main.py
```

## Notes

- Market reporting combines Binance spot context with Bybit futures metadata when available.
- News and sentiment services currently use a clean internal interface so external providers can be added without touching handlers.
- Alerts and warning counts are stored in memory, so they reset on restart unless you later add persistent storage.
