# AR OTP Bot — Railway deployment package

## Why the previous Railway build failed

The uploaded files had generated names such as `bot_...py`, `Procfile_...`,
and `requirements_...txt`. Railway therefore could not find the expected
`bot.py`, `Procfile`, or `requirements.txt` files.

This package has the correct root-level filenames:

- `bot.py` — bot runtime
- `firebase_store.py` — optional Firestore persistence
- `requirements.txt` — Python dependencies
- `Procfile` and `railway.json` — start configuration

## Deploy

1. Upload/extract the **contents of this folder** to the Railway service, or
   deploy the supplied ZIP without adding another nested folder.
2. In Railway → **Variables**, add `TELEGRAM_BOT_TOKEN`.
3. Optional: add `FIREBASE_SERVICE_ACCOUNT_JSON` with the complete Firebase
   service-account JSON on one line.
4. Optional Panel 3 variables: `P3_USER_NAME` and `P3_PASSWORD`.
5. Redeploy and check the deployment logs for:
   `AR OTP BOT is running`.

Do not put real tokens, Firebase JSON, or panel passwords in GitHub/source
files. The bot now stops with a clear error if `TELEGRAM_BOT_TOKEN` is absent.

## Firebase

If Firebase variables are not configured, the bot uses local JSON persistence.
Railway's filesystem is not a permanent database, so configure Firestore if
users, balances, rewards, settings, and orders must survive restarts.