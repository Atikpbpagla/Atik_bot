# AR OTP Bot — split Railway package

## Files

- `bot.py` — main bot runtime, panels, OTP monitors, Telegram UI and polling
- `buy_service.py` — Buy Service state, order flow, admin workflow and handlers
- `firebase_store.py` — optional Firestore persistence with local JSON fallback
- `*.json` — bot configuration/state seed files
- `Procfile` and `railway.json` — Railway worker configuration
- `requirements.txt` — Python dependencies

`bot.py` loads `buy_service.py` into the bot's shared namespace before polling
starts. The Buy Service implementation is kept in its own source file while
retaining the existing shared-state behavior.

## Railway

1. Upload/extract this folder in Railway.
2. Set `TELEGRAM_BOT_TOKEN` as a Railway Secret.
3. Optionally set `FIREBASE_SERVICE_ACCOUNT_JSON` to enable Firestore durability.
4. Railway runs `python -u bot.py` using the included `Procfile`.

Never commit Telegram tokens or Firebase service-account JSON to source control.
