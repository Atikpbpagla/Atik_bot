# This file is executed in bot.py's shared namespace.
# It intentionally uses shared bot globals (bot, types, ADMIN_IDS, load_json, etc.).

# ── Buy Service ───────────────────────────────────────────────────────────────
BUY_SERVICE_FILE = "buy_service_settings.json"
_buy_service_settings = load_json(BUY_SERVICE_FILE, {
    "premium_prices": {"3M": 0, "6M": 0, "1Y": 0},
    "vpn_services": [
        {"id": "nord_7d",       "emoji_id": "5334944492300573096", "name": "NORD",       "duration": "7D",    "price": 20},
        {"id": "express_7d",    "emoji_id": "5346335574498251610", "name": "EXPRESS",    "duration": "7D",    "price": 20},
        {"id": "ipvanish_7d",   "emoji_id": "5352597830089347330", "name": "IP VANISH",  "duration": "7D",    "price": 20},
        {"id": "surfshark_7d",  "emoji_id": "5190447043545438788", "name": "SURFSHARK",  "duration": "7D",    "price": 20},
        {"id": "hma_7d",        "emoji_id": "5346134750417403743", "name": "HMA",        "duration": "7D",    "price": 20},
        {"id": "pia_7d",        "emoji_id": "5328064671951896068", "name": "PIA",        "duration": "7D",    "price": 20},
        {"id": "proton_14d",    "emoji_id": "5348390922507817684", "name": "PROTON",     "duration": "14D",   "price": 30},
        {"id": "express_30d",   "emoji_id": "5346335574498251610", "name": "EXPRESS 30D","duration": "30D",   "price": 45},
        {"id": "hma_30d",       "emoji_id": "5346134750417403743", "name": "HMA 30D",    "duration": "30D",   "price": 45},
        {"id": "9proxy_1gb",    "emoji_id": "5336983442125001376", "name": "9 PROXY",    "duration": "1GB",   "price": 100},
        {"id": "owlproxy_200mb","emoji_id": "5334530732331143967", "name": "OWL PROXY",  "duration": "200MB", "price": 10},
    ],
    "binance_id": "1138284235",
    "bkash_number": "01340670062",
    "bkash_emoji_id": "5348469219761626211",
    "binance_emoji_id": "5431815433011736909",
    "nagad_number": "01320750520",
    "nagad_emoji_id": "6190392842544748430",
    "dollar_rate": 128,
})

def save_buy_service_settings():
    save_json(BUY_SERVICE_FILE, _buy_service_settings)

# ── Migrate: ensure every VPN entry has a unique id ──────────────────────────
def _migrate_vpn_ids():
    vpns = _buy_service_settings.get("vpn_services", [])
    changed = False
    seen_ids = set()
    for i, v in enumerate(vpns):
        vid = v.get("id", "")
        if not vid or vid in seen_ids:
            v["id"] = f"vpn_{int(time.time() * 1000)}_{i}"
            changed = True
        seen_ids.add(v["id"])
    if changed:
        save_buy_service_settings()

_migrate_vpn_ids()

# {uid: {"type": "premium|vpn", "label": "...", "price": N}}
_buy_pending: dict = {}
# {uid: {"file_id": ..., "pending": {...}}} — screenshot saved, waiting for TG username
_buy_screenshot_pending: dict = {}
# {admin_uid: target_uid}
_admin_dmu_state: dict = {}
# Admin buy service step state
_buy_admin_state: dict = {}


def _update_buy_order_status(order_id, status, completed_by=None):
    """Update a payment order's status without failing the Telegram callback."""
    if not order_id:
        return False
    try:
        import json as _json_order, os as _os_order
        order_file = "buy_orders_log.json"
        if not _os_order.path.exists(order_file):
            return False
        with open(order_file, "r") as _order_f:
            orders = _json_order.load(_order_f)
        if not isinstance(orders, list):
            return False
        updated = False
        for order in orders:
            if isinstance(order, dict) and order.get("order_id") == order_id:
                order["status"] = status
                order["status_updated_at"] = time.time()
                if completed_by is not None:
                    order["completed_by"] = int(completed_by)
                updated = True
                break
        if updated:
            with open(order_file, "w") as _order_f:
                _json_order.dump(orders, _order_f, ensure_ascii=False)
        return updated
    except Exception as _order_status_error:
        print(f"[BUY-ORDER] Could not update order status: {_order_status_error}")
        return False


def _find_buy_order(order_id):
    """Return one saved order without exposing credentials to persistent state."""
    try:
        orders = load_json("buy_orders_log.json", [])
        if isinstance(orders, list):
            for order in reversed(orders):
                if isinstance(order, dict) and order.get("order_id") == order_id:
                    return dict(order)
    except Exception as _order_read_error:
        print(f"[BUY-ORDER] Could not read order {order_id}: {_order_read_error}")
    return None


def _buy_emoji_tag(emoji_id, fallback):
    """Build a Telegram custom-emoji tag from a configured ID."""
    import html as _html
    value = str(emoji_id or "").strip()
    if not value:
        return fallback
    return f'<tg-emoji emoji-id="{_html.escape(value)}">{fallback}</tg-emoji>'


def _buy_success_message(order, gmail, password):
    """Render the editable VPN delivery template with runtime values."""
    import html as _html

    service_name = order.get("service_name") or order.get("service") or "VPN"
    service_name = re.sub(r"^\s*VPN\s*[—:-]\s*", "", str(service_name), flags=re.I)
    if "|" in service_name:
        service_name = service_name.split("|", 1)[0].strip()
    duration = str(order.get("duration") or "")
    price = order.get("price", 0)
    try:
        price_text = str(int(price)) if float(price).is_integer() else f"{float(price):.2f}"
    except (TypeError, ValueError):
        price_text = str(price)

    with _custom_emoji_lock:
        balance_id = (
            _custom_emojis.get("buttons", {}).get("balance")
            or _BTN_DEFAULT_ICONS.get("balance")
        )

    values = {
        "service_emoji": _buy_emoji_tag(order.get("service_emoji_id"), "🔒"),
        "service_name": _html.escape(service_name),
        "balance_emoji": _buy_emoji_tag(balance_id, "💰"),
        "balance_emoji_id": _html.escape(str(balance_id or "")),
        "balance": _html.escape(price_text),
        "price": _html.escape(price_text),
        "currency": _html.escape(str(get_currency())),
        "duration": _html.escape(duration),
        "gmail": _html.escape(str(gmail)),
        "password": _html.escape(str(password)),
    }

    class _BuyTemplateValues(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    try:
        return get_template("buy_service_success").format_map(_BuyTemplateValues(values))
    except (ValueError, IndexError) as _template_error:
        print(f"[BUY-ORDER] Invalid VPN success template: {_template_error}")
        return (
            f'{values["service_emoji"]} <b>{values["service_name"]} VPN PURCHASE SUCCESSFULLY</b>\n\n'
            f'{values["balance_emoji"]} <b>BALANCE :</b> <code>{values["balance"]} BDT</code>\n'
            f'<b>DURATION:</b> <code>{values["duration"]}</code>\n'
            f'<b>GMAIL:</b> <code>{values["gmail"]}</code>\n'
            f'<b>PASSWORD:</b> <code>{values["password"]}</code>'
        )


def _is_vpn_buy_order(order):
    if not isinstance(order, dict):
        return False
    if str(order.get("order_type", "")).lower() == "vpn":
        return True
    return str(order.get("service", "")).strip().lower().startswith("vpn")


def _finish_buy_order(order_id, target_uid, admin_uid, gmail=None, password=None, state=None):
    """Complete an order and send delivery; credentials remain memory-only."""
    order = _find_buy_order(order_id) or {}
    if order.get("status") == "completed":
        return False
    if not _update_buy_order_status(order_id, "completed", completed_by=admin_uid):
        return False

    if state:
        try:
            bot.edit_message_reply_markup(
                state["admin_chat_id"], state["admin_message_id"], reply_markup=None
            )
        except Exception:
            pass

    try:
        bot.send_message(
            state["admin_chat_id"] if state else admin_uid,
            f"✅ <b>Order Complete</b>\n\n"
            f"🆔 Order: <code>{order_id}</code>\n"
            f"👤 User: <code>{target_uid}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    try:
        if _is_vpn_buy_order(order):
            delivery_text = _buy_success_message(order, gmail or "", password or "")
        else:
            delivery_text = (
                "✅ <b>Your order is complete.</b>\n"
                "Admin has delivered/processed your service."
            )
        bot.send_message(target_uid, delivery_text, parse_mode="HTML")
        return True
    except Exception as _delivery_error:
        print(f"[BUY-ORDER] User delivery failed for {target_uid}: {_delivery_error}")
        return False


def _start_vpn_credentials_prompt(call, target_uid, order_id):
    """Ask an admin for VPN credentials only; do not persist them."""
    uid = call.from_user.id
    _buy_admin_state[uid] = {
        "target_uid": target_uid,
        "order_id": order_id,
        "admin_chat_id": call.message.chat.id,
        "admin_message_id": call.message.message_id,
    }
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
    except Exception:
        pass
    prompt = bot.send_message(
        call.message.chat.id,
        "🔐 <b>VPN delivery</b>\n\n"
        "Step 1/2: Gmail/email পাঠান।\n"
        "এই credential bot save করবে না; শুধু user-কে পাঠিয়ে memory থেকে remove করবে।\n\n"
        "🔙 Cancel করতে Admin Panel চাপুন।",
        reply_markup=_back_admin_kb(),
        parse_mode="HTML",
    )
    bot.register_next_step_handler(prompt, _buy_vpn_gmail_step)


def _buy_vpn_gmail_step(message):
    uid = message.from_user.id
    state = _buy_admin_state.get(uid)
    if not state:
        return
    if _is_back(message.text) or _intercept_menu_btn(message):
        _buy_admin_state.pop(uid, None)
        _go_admin_panel(message)
        return
    gmail = (message.text or "").strip()
    if not gmail:
        prompt = bot.send_message(
            message.chat.id, "❌ Gmail/email খালি রাখা যাবে না। আবার পাঠান:",
            reply_markup=_back_admin_kb()
        )
        bot.register_next_step_handler(prompt, _buy_vpn_gmail_step)
        return
    state["gmail"] = gmail
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass
    prompt = bot.send_message(
        message.chat.id,
        "Step 2/2: VPN password পাঠান।\n"
        "Password message input নেওয়ার পর delete করা হবে।",
        reply_markup=_back_admin_kb(),
    )
    bot.register_next_step_handler(prompt, _buy_vpn_password_step)


def _buy_vpn_password_step(message):
    uid = message.from_user.id
    state = _buy_admin_state.pop(uid, None)
    if not state:
        return
    if _is_back(message.text) or _intercept_menu_btn(message):
        _go_admin_panel(message)
        return
    password = (message.text or "").strip()
    if not password:
        _buy_admin_state[uid] = state
        prompt = bot.send_message(
            message.chat.id, "❌ Password খালি রাখা যাবে না। আবার পাঠান:",
            reply_markup=_back_admin_kb()
        )
        bot.register_next_step_handler(prompt, _buy_vpn_password_step)
        return
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass
    _finish_buy_order(
        state["order_id"],
        state["target_uid"],
        uid,
        gmail=state.get("gmail", ""),
        password=password,
        state=state,
    )


# ── Buy Service helper handlers ─────────────────────────────────────────────
def _show_buy_service_admin(message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💎 Set Premium Price", "➕ Add VPN Service")
    markup.add("💰 Set VPN Price", "🗑️ Remove VPN")
    markup.add("📨 Send User Message")
    markup.add("🔙 𝗔𝗗𝗠𝗜𝗡 𝗣𝗔𝗡𝗘𝗟")
    prices = _buy_service_settings["premium_prices"]
    rate = _buy_service_settings.get("dollar_rate", 128)
    vpn_count = len(_buy_service_settings.get("vpn_services", []))
    bot.send_message(
        message.chat.id,
        f"🛒 <b>Buy Service Admin Panel</b>\n\n"
        f"💎 Premium Prices:\n"
        f"  • 3 Month: <b>{prices.get('3M', 0)} BDT</b>\n"
        f"  • 6 Month: <b>{prices.get('6M', 0)} BDT</b>\n"
        f"  • 1 Year:  <b>{prices.get('1Y', 0)} BDT</b>\n"
        f"  • Dollar Rate: <b>1$ = {rate} BDT</b>\n\n"
        f"🔒 VPN Services: <b>{vpn_count}</b> ta\n\n"
        f"Choose an option from below:",
        reply_markup=markup,
        parse_mode="HTML",
    )


def _show_vpn_remove_list(message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS:
        return
    vpns = _buy_service_settings.get("vpn_services", [])
    if not vpns:
        bot.send_message(message.chat.id, "❌ Kono VPN service nei.")
        _show_buy_service_admin(message)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, v in enumerate(vpns):
        emoji_id = v.get("emoji_id", "")
        name = v.get("name", "")
        dur = v.get("duration", "")
        price = v.get("price", 0)
        vid = v.get("id") or str(i)
        label = f"{name} | {dur} | {price} BDT"
        btn_kwargs = {"icon_custom_emoji_id": emoji_id} if emoji_id else {}
        markup.add(types.InlineKeyboardButton(
            f"🗑️ {label}", callback_data=f"buy_del_vpn:{vid}", style="danger", **btn_kwargs
        ))
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="buy_del_vpn:cancel"))
    bot.send_message(
        message.chat.id,
        "🗑️ <b>Remove VPN Service</b>\n\nKonTa remove korbe?",
        reply_markup=markup,
        parse_mode="HTML",
    )


def _show_vpn_price_list(message):
    """Show each VPN separately so an admin can edit one price at a time."""
    if message.from_user.id not in ADMIN_IDS:
        return
    vpns = _buy_service_settings.get("vpn_services", [])
    if not vpns:
        bot.send_message(message.chat.id, "❌ Kono VPN service nei.")
        _show_buy_service_admin(message)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, vpn in enumerate(vpns):
        vid = str(vpn.get("id") or i)
        emoji_id = vpn.get("emoji_id", "")
        label = (
            f"{vpn.get('name', 'VPN')} | {vpn.get('duration', '')} | "
            f"{vpn.get('price', 0)} BDT"
        )
        btn_kwargs = {"icon_custom_emoji_id": emoji_id} if emoji_id else {}
        markup.add(types.InlineKeyboardButton(
            f"💰 {label}",
            callback_data=f"buy_set_vpn_price:{vid}",
            style="primary",
            **btn_kwargs,
        ))
    markup.add(types.InlineKeyboardButton(
        "❌ Cancel", callback_data="buy_set_vpn_price:cancel", style="danger"
    ))
    bot.send_message(
        message.chat.id,
        "💰 <b>Set VPN Price</b>\n\nKon VPN service-er price change korbe?",
        reply_markup=markup,
        parse_mode="HTML",
    )


def _buy_set_premium_step(message):
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    if _intercept_menu_btn(message):
        return
    parts = (message.text or "").strip().split()
    if len(parts) < 3:
        msg = bot.send_message(message.chat.id,
            "❌ Wrong format! Enter 3 values (3M 6M 1Y BDT):\n"
            "<i>Example: <code>650 1200 2000</code></i>",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _buy_set_premium_step)
        return
    try:
        p3m = int(parts[0]); p6m = int(parts[1]); p1y = int(parts[2])
        rate = int(parts[3]) if len(parts) >= 4 else _buy_service_settings.get("dollar_rate", 128)
    except ValueError:
        msg = bot.send_message(message.chat.id,
            "❌ Enter numbers only!\n<i>Example: <code>650 1200 2000</code></i>",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _buy_set_premium_step)
        return
    _buy_service_settings["premium_prices"] = {"3M": p3m, "6M": p6m, "1Y": p1y}
    _buy_service_settings["dollar_rate"] = rate
    save_buy_service_settings()
    bot.send_message(message.chat.id,
        f"✅ <b>Premium prices updated!</b>\n\n"
        f"• 3 Month: <b>{p3m} BDT</b>\n"
        f"• 6 Month: <b>{p6m} BDT</b>\n"
        f"• 1 Year:  <b>{p1y} BDT</b>\n"
        f"• Dollar Rate: <b>1$ = {rate} BDT</b>",
        parse_mode="HTML")
    _show_buy_service_admin(message)


def _buy_set_vpn_price_step(message, vpn_id):
    """Validate and persist the price for the selected VPN only."""
    if message.from_user.id not in ADMIN_IDS:
        return
    if _is_back(message.text):
        _show_buy_service_admin(message)
        return
    if _intercept_menu_btn(message):
        return
    raw_price = (message.text or "").strip()
    try:
        price = int(raw_price)
        if price < 0:
            raise ValueError
    except ValueError:
        prompt = bot.send_message(
            message.chat.id,
            "❌ Price must be a whole number (0 or more BDT):",
            reply_markup=_back_admin_kb(),
        )
        bot.register_next_step_handler(
            prompt, lambda m, vid=vpn_id: _buy_set_vpn_price_step(m, vid)
        )
        return

    selected = None
    for vpn in _buy_service_settings.get("vpn_services", []):
        if str(vpn.get("id", "")) == str(vpn_id):
            selected = vpn
            break
    if selected is None:
        bot.send_message(
            message.chat.id,
            "❌ Ei VPN service-ti আর নেই. List abar open korun.",
        )
        _show_buy_service_admin(message)
        return

    selected["price"] = price
    save_buy_service_settings()
    bot.send_message(
        message.chat.id,
        f"✅ <b>{selected.get('name', 'VPN')}</b> price updated: "
        f"<b>{price} BDT</b>",
        parse_mode="HTML",
    )
    _show_buy_service_admin(message)


def _buy_add_vpn_step(message):
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    if _intercept_menu_btn(message):
        return
    parts = (message.text or "").strip().split()
    if len(parts) < 4:
        msg = bot.send_message(message.chat.id,
            "❌ Wrong format!\n"
            "<code>EMOJI_ID NAME DURATION PRICE_BDT</code>\n"
            "<i>Example: <code>5334944492300573096 NORD 7D 300</code></i>",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _buy_add_vpn_step)
        return
    try:
        emoji_id = parts[0]
        price = int(parts[-1])
        duration = parts[-2]
        name = " ".join(parts[1:-2])
    except ValueError:
        msg = bot.send_message(message.chat.id,
            "❌ Price must be numbers only!",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _buy_add_vpn_step)
        return
    # Validate: emoji_id must be numeric (Telegram custom emoji ID)
    if not emoji_id.strip().isdigit():
        msg = bot.send_message(message.chat.id,
            "❌ <b>Wrong format!</b> EMOJI_ID must be numbers only (Telegram custom emoji ID).\n\n"
            "Sothik format:\n"
            "<code>EMOJI_ID NAME DURATION PRICE_BDT</code>\n\n"
            "Example:\n"
            "<code>5334944492300573096 NORD 7D 300</code>\n\n"
            "⚠️ The first value should be the Emoji ID (digits only), then name, duration, price.",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _buy_add_vpn_step)
        return
    if not name.strip():
        msg = bot.send_message(message.chat.id,
            "❌ VPN name daw!",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _buy_add_vpn_step)
        return
    vpn_id = f"vpn_{int(time.time() * 1000)}"
    new_svc = {"id": vpn_id, "emoji_id": emoji_id, "name": name, "duration": duration, "price": price}
    _buy_service_settings.setdefault("vpn_services", []).append(new_svc)
    save_buy_service_settings()
    bot.send_message(message.chat.id,
        f"✅ <b>VPN added!</b>\n"
        f"Name: <b>{name}</b> | Duration: <b>{duration}</b> | Price: <b>{price} BDT</b>",
        parse_mode="HTML")
    _show_buy_service_admin(message)


def _buy_send_ask_uid_step(message):
    uid = message.from_user.id
    if _is_back(message.text):
        _go_admin_panel(message)
        return
    if _intercept_menu_btn(message):
        return
    raw = re.sub(r"\D", "", (message.text or "").strip())
    if not raw:
        msg = bot.send_message(message.chat.id,
            "❌ Enter a valid Chat ID (only numbers).",
            reply_markup=_back_admin_kb(), parse_mode="HTML")
        bot.register_next_step_handler(msg, _buy_send_ask_uid_step)
        return
    target_uid = int(raw)
    _admin_dmu_state[uid] = target_uid
    msg = bot.send_message(
        message.chat.id,
        f"✅ Target: <code>{target_uid}</code>\n\n"
        f"📝 Now send the message content (text, photo, video all accepted):\n"
        f"To use a custom emoji, write the emoji ID in the message.\n\n"
        f"🔙 Back: Press the <b>Admin Panel</b> button.",
        reply_markup=_back_admin_kb(), parse_mode="HTML")
    bot.register_next_step_handler(msg, _buy_send_msg_step)


def _buy_send_msg_step(message):
    uid = message.from_user.id
    if _is_back(message.text):
        _admin_dmu_state.pop(uid, None)
        _go_admin_panel(message)
        return
    if _intercept_menu_btn(message):
        _admin_dmu_state.pop(uid, None)
        return
    target_uid = _admin_dmu_state.pop(uid, None)
    if not target_uid:
        _go_admin_panel(message)
        return

    def _resolve_custom_emoji_in_text(text):
        """Replace bare 18-19 digit IDs in text with tg-emoji tags."""
        import re as _re2
        def _repl(m):
            eid = m.group(1)
            return f'<tg-emoji emoji-id="{eid}">⭐</tg-emoji>'
        return _re2.sub(r'(?<![/\d])(\d{18,19})(?![\d])', _repl, text or "")

    try:
        if message.photo:
            cap = _resolve_custom_emoji_in_text(message.caption or "")
            bot.send_photo(target_uid, message.photo[-1].file_id,
                           caption=cap or None, parse_mode="HTML" if cap else None)
        elif message.video:
            cap = _resolve_custom_emoji_in_text(message.caption or "")
            bot.send_video(target_uid, message.video.file_id,
                           caption=cap or None, parse_mode="HTML" if cap else None)
        elif message.document:
            cap = _resolve_custom_emoji_in_text(message.caption or "")
            bot.send_document(target_uid, message.document.file_id,
                              caption=cap or None, parse_mode="HTML" if cap else None)
        elif message.sticker:
            bot.send_sticker(target_uid, message.sticker.file_id)
        elif message.voice:
            bot.send_voice(target_uid, message.voice.file_id)
        elif message.animation:
            cap = _resolve_custom_emoji_in_text(message.caption or "")
            bot.send_animation(target_uid, message.animation.file_id,
                               caption=cap or None, parse_mode="HTML" if cap else None)
        elif message.text:
            txt_out = _resolve_custom_emoji_in_text(message.text)
            bot.send_message(target_uid, txt_out, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "❌ Ei content type support hoi na.")
            return
        bot.send_message(message.chat.id,
            f"✅ Message sent to <code>{target_uid}</code>!", parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Pathano jay ni: <code>{e}</code>", parse_mode="HTML")
    _show_buy_service_admin(message)


@bot.message_handler(content_types=["photo"])
def photo_handler(message):
    uid = message.from_user.id
    # Screenshot from user who is awaiting payment confirmation
    if uid in _buy_pending:
        pending = _buy_pending.pop(uid)
        svc_type = pending.get("type", "")
        file_id = message.photo[-1].file_id

        if svc_type == "premium":
            # For Telegram Premium: ask which account will receive it
            _buy_screenshot_pending[uid] = {"file_id": file_id, "pending": pending}
            msg = bot.send_message(
                message.chat.id,
                '<tg-emoji emoji-id="5314504236132747481">✅</tg-emoji> <b>Screenshot peyechi!</b> <tg-emoji emoji-id="5314504236132747481">✅</tg-emoji>\n\n'
                '<tg-emoji emoji-id="5269215244810491516">📲</tg-emoji> Kon Telegram account-e Premium nibe?\n'
                "<b>Username or Phone number:</b>\n\n"
                "<i>Example: <code>@username</code> or <code>+8801XXXXXXXXX</code></i>",
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, _buy_premium_tg_username_step)
        else:
            # For VPN: notify admins directly
            _notify_admins_screenshot(uid, message.from_user, file_id, pending, tg_target=None)
        return
    # If admin, ignore
    if uid in ADMIN_IDS:
        return


def _notify_admins_screenshot(uid, from_user, file_id, pending, tg_target):
    """Send payment screenshot — guaranteed delivery to PRIMARY_BUY_ADMIN with retry."""
    PRIMARY_BUY_ADMIN = 6664150885  # Must NEVER miss this inbox

    uname = from_user.username
    fname = from_user.first_name or ""
    user_info = f"@{uname}" if uname else fname or str(uid)
    service_label = pending.get("label", "Unknown")
    price = pending.get("price", 0)
    order_id = f"order_{int(time.time() * 1000)}_{uid}"

    tg_line = f"📲 Premium For: <b>{tg_target}</b>\n" if tg_target else ""
    caption = (
        f"📸 <b>PAYMENT SCREENSHOT</b>\n\n"
        f"👤 User: {user_info}\n"
        f"🆔 Chat ID: <code>{uid}</code>\n"
        f"📦 Service: <b>{service_label}</b>\n"
        f"💰 Price: <b>{price} BDT</b>\n"
        f"{tg_line}"
        f"✅ Verify korar por user-ke service pathao."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "📨 Send Message to User",
        callback_data=f"admin_dmu:{uid}",
        style="primary",
    ))
    markup.add(types.InlineKeyboardButton(
        "✅ Order Complete",
        callback_data=f"order_complete:{uid}:{order_id}",
        style="success",
    ))

    # ── Save order to backup log (disk) so no order is ever lost ──────────────
    try:
        _order_log = "buy_orders_log.json"
        _orders = load_json(_order_log, [])
        if not isinstance(_orders, list):
            _orders = []
        _orders.append({
            "order_id": order_id,
            "ts": time.time(),
            "user_id": uid,
            "user_info": user_info,
            "service": service_label,
            "price": price,
            "tg_target": tg_target,
            "file_id": file_id,
            "status": "pending",
            "order_type": pending.get("order_type", pending.get("type", "")),
            "service_id": pending.get("service_id", ""),
            "service_name": pending.get("service_name", ""),
            "duration": pending.get("duration", ""),
            "service_emoji_id": pending.get("service_emoji_id", ""),
        })
        save_json(_order_log, _orders)
    except Exception as _log_err:
        print(f"[BUY-LOG] Could not write order log: {_log_err}")

    # ── Send to PRIMARY_BUY_ADMIN with 3 retries ───────────────────────────────
    _primary_ok = False
    for _attempt in range(1, 4):
        try:
            bot.send_photo(
                PRIMARY_BUY_ADMIN, file_id,
                caption=caption, parse_mode="HTML", reply_markup=markup,
            )
            _primary_ok = True
            print(f"[BUY-ORDER] ✅ Sent to primary admin {PRIMARY_BUY_ADMIN} (attempt {_attempt})")
            break
        except Exception as _e:
            print(f"[BUY-ORDER] ❌ Attempt {_attempt}/3 failed for primary admin {PRIMARY_BUY_ADMIN}: {_e}")
            if _attempt < 3:
                time.sleep(2)

    # ── If photo failed all 3 times, send text fallback ───────────────────────
    if not _primary_ok:
        try:
            fallback_text = (
                f"⚠️ <b>NEW BUY ORDER (photo send failed — manual check needed)</b>\n\n"
                f"👤 User: {user_info}\n"
                f"🆔 Chat ID: <code>{uid}</code>\n"
                f"📦 Service: <b>{service_label}</b>\n"
                f"💰 Price: <b>{price} BDT</b>\n"
                f"{tg_line}"
                f"📎 File ID: <code>{file_id}</code>"
            )
            bot.send_message(PRIMARY_BUY_ADMIN, fallback_text, parse_mode="HTML", reply_markup=markup)
            print(f"[BUY-ORDER] ⚠️ Text fallback sent to primary admin {PRIMARY_BUY_ADMIN}")
        except Exception as _fe:
            print(f"[BUY-ORDER] 🚨 CRITICAL: Could not reach primary admin {PRIMARY_BUY_ADMIN} at all: {_fe}")

    # ── Send to other super admins (best-effort, no retry) ────────────────────
    for admin_uid in SUPER_ADMIN_IDS:
        if admin_uid == PRIMARY_BUY_ADMIN:
            continue
        try:
            bot.send_photo(
                admin_uid, file_id,
                caption=caption, parse_mode="HTML", reply_markup=markup,
            )
        except Exception as _e:
            print(f"[BUY-ORDER] Could not send to secondary admin {admin_uid}: {_e}")

    bot.send_message(
        uid,
        '<tg-emoji emoji-id="5395695537687123235">✅</tg-emoji> <b>Screenshot sent!</b> <tg-emoji emoji-id="5395695537687123235">✅</tg-emoji>\n\n'
        '<tg-emoji emoji-id="5253742260054409879">✅</tg-emoji> Admin will review and send the service soon. Thank you! <tg-emoji emoji-id="5379643836152684738">🙏</tg-emoji>',
        parse_mode="HTML",
    )


def _buy_premium_tg_username_step(message):
    """Receive target Telegram username/phone for premium, then notify admins."""
    uid = message.from_user.id
    if _intercept_menu_btn(message):
        _buy_screenshot_pending.pop(uid, None)
        return
    raw = (message.text or "").strip()
    if not raw:
        msg = bot.send_message(
            message.chat.id,
            "❌ Username or Phone number:\n"
            "<i>Example: <code>@username</code> or <code>+8801XXXXXXXXX</code></i>",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, _buy_premium_tg_username_step)
        return
    saved = _buy_screenshot_pending.pop(uid, None)
    if not saved:
        return
    _notify_admins_screenshot(uid, message.from_user, saved["file_id"], saved["pending"], tg_target=raw)
