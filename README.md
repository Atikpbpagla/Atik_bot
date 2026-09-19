# AR OTP Bot — Railway two-file package

## Source files

- `bot.py` — complete bot runtime, panels, OTP, Telegram UI, and polling
- `buy_service.py` — buy-service configuration, VPN/Premium order callbacks,
  payment instructions, screenshot handling, and admin workflow

The buy-service module is loaded before the first callback handler and before
polling starts. This prevents the Buy VPN button from becoming unresponsive.

## Railway

1. Upload/extract this folder in Railway.
2. Add `TELEGRAM_BOT_TOKEN` as a Railway Secret.
3. Add `FIREBASE_SERVICE_ACCOUNT_JSON` as a Railway Secret. Its value should
   be the complete Firebase service-account JSON from Firebase Console →
   Project settings → Service accounts → Generate new private key.
4. Enable Firestore Database in the Firebase console. The bot stores its JSON
   state in the `bot_state` collection and keeps local JSON files as a cache.
5. Railway runs `python -u bot.py` using the included `Procfile`.

Do not place the real token in a file or commit it to source control.
Do not place the Firebase service-account JSON in the project either.

## Firebase behavior

Firebase is optional at startup. Without `FIREBASE_SERVICE_ACCOUNT_JSON`, the
bot uses the original local JSON files. With it configured, existing JSON files
are imported on first run and later reads/writes use Firestore first, so users,
balances, rewards, settings, dynamic panels, and buy orders survive Railway
restarts.

The Rabbi1_FD panel at `168.119.13.175/ints/agent/SMSCDRStats` is configured as
the Panel 3 SMSCDR source. Keep its login in Replit Secrets as `P3_USER_NAME`
and `P3_PASSWORD`; credentials are not kept in the source.

Buy-order screenshots are delivered asynchronously to every configured admin.
Clicking **Send Message to User** on a pending VPN order now asks for Gmail and
password, renders the saved VPN success template, sends it to that buyer, and
completes the order. Those credentials remain transient and are never saved in
the order log or Firestore.

## VPN order delivery

When an admin presses **Order Complete** on a VPN order, the bot asks for the
Gmail/email and password, sends the editable success message to the buyer, and
does not save those credentials in JSON or Firestore. Proxy and Telegram
Premium orders do not ask for VPN credentials.

The success message can be edited from the bot's existing **Message Edit**
admin menu. Available variables include:
`{service_emoji}`, `{service_name}`, `{balance}`, `{duration}`, `{gmail}`,
`{password}`, and `{balance_emoji}`.
