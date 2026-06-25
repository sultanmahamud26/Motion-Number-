import requests
import time
import json
import os
import uuid
import threading
import random
import re
import html
import pyotp
import phonenumbers
from collections import Counter 
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from datetime import datetime 
from urllib.parse import urljoin

# ==========================================
# Configuration (Token & Owner ID)
# ==========================================
TOKEN = "8520336415:AAE-e4IEIxzBVGCvFPNyIkYoFV7a5IpTDsQ"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
FILE_URL = f"https://api.telegram.org/file/bot{TOKEN}/"

OWNER_ID = 8348555334
BOT_USERNAME = "@motion_numbers_bot"
DB_FILE = "bot_data.json"

# ==========================================
# Premium Emoji Database
# ==========================================
PEM = {
    "ok": '<tg-emoji emoji-id="5352694861990501856">✅</tg-emoji>',
    "no": '<tg-emoji emoji-id="5420130255174145507">❌</tg-emoji>',
    "warn": '<tg-emoji emoji-id="5336944168944047463">⚠️</tg-emoji>',
    "admin": '<tg-emoji emoji-id="5353032893096567467">📊</tg-emoji>',
    "user": '<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji>',
    "file": '<tg-emoji emoji-id="5352721946054268944">📁</tg-emoji>',
    "rocket": '<tg-emoji emoji-id="5352597830089347330">🚀</tg-emoji>',
    "graph": '<tg-emoji emoji-id="5352877703043258544">📊</tg-emoji>',
    "money": '<tg-emoji emoji-id="5348469219761626211">💸</tg-emoji>',
    "gift": '<tg-emoji emoji-id="5420396762189831222">🎁</tg-emoji>',
    "msg": '<tg-emoji emoji-id="5337302974806922068">💬</tg-emoji>',
    "gear": '<tg-emoji emoji-id="5420155432272438703">⚙️</tg-emoji>',
    "link": '<tg-emoji emoji-id="5420517437885943844">🔗</tg-emoji>',
    "trash": '<tg-emoji emoji-id="5422557736330106570">🗑</tg-emoji>',
    "upload": '<tg-emoji emoji-id="5353001161878182134">📤</tg-emoji>',
    "world": '<tg-emoji emoji-id="5336972142066047577">🌐</tg-emoji>',
    "lock": '<tg-emoji emoji-id="5353022963132174959">🔐</tg-emoji>',
    "phone": '<tg-emoji emoji-id="5337132498965010628">📱</tg-emoji>',
    "num": '<tg-emoji emoji-id="5352862640592949843">🔢</tg-emoji>',
    "pin": '<tg-emoji emoji-id="5352922460897452503">📍</tg-emoji>',
    "star": '<tg-emoji emoji-id="5352552689983067014">✨</tg-emoji>',
    "hi": '<tg-emoji emoji-id="5353027129250453493">👋</tg-emoji>'
}

GLOBAL_BODY_EMOJIS = {
    "➖": "5870818207383686839", "🚫": "5334807341109908955", "😒": "5334763399299506604",
    "🖥": "5334880948259427772", "🌐": "5334590977837403844", "🌟": "5337102391244263212",
    "🕓": "5336983442125001376", "⌛": "5337172996211648018", "💬": "5337302974806922068",
    "🔐": "5337255927735163754", "🍏": "5337132498965010628", "❔": "5336850036145823599",
    "⚠️": "5336944168944047463", "🔥": "5337267511261960341", "💸": "5348469219761626211",
    "🥚": "5348390922507817684", "👨‍⚖": "5334763399299506604", "🐁": "5348494358205207761",
    "🧻": "5348486915026884464", "⚗": "5346311574221000149", "🛴": "5348075478634766440",
    "📊": "5353032893096567467", "🔢": "5352862640592949843", "👤": "5352861489541714456",
    "📁": "5352721946054268944", "🚀": "5352597830089347330", "💎": "5352838545826420397",
    "📍": "5352922460897452503", "👋": "5353027129250453493", "✅": "5352694861990501856",
    "1️⃣": "5352651766288652742", "2️⃣": "5355186458418257716", "3️⃣": "5352867219028091093",
    "4️⃣": "5352566657216714037", "5️⃣": "5353086880835474989", "6️⃣": "5354859211975071385",
    "7️⃣": "5352859127309707652", "8️⃣": "5352957533600389988", "9️⃣": "5353060913463204207",
    "🔤": "5352727417842606016", "📣": "5352980533150259581", "📤": "5353001161878182134",
    "✨": "5352552689983067014", "🔹": "5352638632278660622", "🎙": "5355102594886833928",
    "💴": "5352985330628730418", "📅": "5352585194295564660", "📴": "5352974971167611327",
    "✏️": "5395444784611480792", "📱": "5337132498965010628", "🔗": "5420517437885943844",
    "❌": "5420130255174145507", "⚙️": "5420155432272438703", "🫂": "5420145051336485498",
    "➕": "5420323438508155202", "🗑": "5422557736330106570", "🎁": "5420396762189831222",
    "➤": "5420618897898381296", "🏢": "5420156334215565595", "💳": "5190899075968441286",
    "📝": "5192739271886282680", "🛡": "5190447043545438788", "🤝": "5192805934073685937",
    "💰": "5190576863226933563", "👀": "5190645917711114179", "🕹": "5193100774988617665",
    "🟢": "5192812028632274956", "🧪": "5190781475468915802", "🎨": "5190751148704833975",
    "📂": "5257969839313526622", "🌍": "5780471598922337683", "📌": "5318986077455795572",
    "📢": "5789428375261023681", "🆔": "5352862640592949843", "📈": "5352877703043258544",
    "🔔": "5352980533150259581", "🏦": "5348469219761626211", "🧾": "5192739271886282680",
    "👨‍⚖️": "5334763399299506604", "🔍": "5463352748751753567",
    "🔑": "5197288647275071607"
}

DEFAULT_CUSTOM_MESSAGES = {
    "start": {"text": "╔═══════════╗\n       📊 NUMBER BOT\n╚═══════════╝\n🚀 Welcome to Number & OTP Service\n━━━━━━━━━━━━\n✅ Choose an option below\nto continue using the bot.\n━━━━━━━━━━━━\n💎 Premium OTP Service", "buttons": []},
    "get_number": {"text": f"{PEM['pin']} Select a service:", "buttons": []},
    "select_country": {"text": f"📌 Select a country for {{service}}:", "buttons": []}, 
    "search_number": {"text": "╔═══════════╗\n     🔍 <b>SEARCH NUMBER</b>\n╚═══════════╝\n✅ Enter 3 to 9 digits  \nto search for a number.\n━━━━━━━━━━━━━\n📝 Example:\n➥ 880\n➥ 9227373\n━━━━━━━━━━━━━\n🔍 Fast Number Lookup System", "buttons": []},
    "traffic": {"text": f"{PEM['graph']} <b>Traffic Overview</b>\n\n{PEM['ok']} Available Numbers: {{avail}}\n{PEM['rocket']} Assigned Numbers: {{assigned}}", "buttons": []},
    "refer": {"text": f"➖➖➖➖➖➖➖\n« {PEM['gift']} REFER & EARN »\n➖➖➖➖➖➖➖\n{PEM['link']} YOUR LINK:\n<code>{{ref_link}}</code>\n➖➖➖➖➖➖➖\n{PEM['user']} TOTAL REFERS: <b>{{total_ref}}</b>\n➖➖➖➖➖➖➖\n{PEM['money']} PER REFER: <b>{{ref_reward}} TK</b>\n➖➖➖➖➖➖➖", "buttons": []},
    "withdrawal": {"text": "➖➖➖➖➖➖➖\n《 😒 WITHDRAWAL 》\n➖➖➖➖➖➖➖\n👋 Total Otp: {total_otp}\n➖➖➖➖➖➖➖\n🫂 Total Reffer :{total_ref}\n➖➖➖➖➖➖➖\n📅 BALANCE: {bal}৳\n➖➖➖➖➖➖➖\n🔐 MINIMUM: {min_w} ৳\n➖➖➖➖➖➖➖\nSELECT METHOD:", "buttons": []},
    "support": {"text": f"{PEM['msg']} Contact us for any help:", "buttons": []}
}

# Firebase removed - local only
db = None


bot_settings = {
    "admins": [OWNER_ID],
    "panels": [], 
    "fw_groups": [], 
    "otp_link": "https://t.me/your_otp_group",
    "withdraw_on": True,
    "not_earn_services": [],
    "bonus_rate_global": 0.0,
    "min_withdraw": 30.0,
    "otp_reward": 0.1,
    "refer_reward": 0.2,
    "refer_per_otp": 0.0,        # per-OTP referral bonus (0 = disabled)
    "refer_max_otps": 50,        # max OTPs to count for referral
    "cooldown": 10,
    "num_req": 3,
    "num_share": 1, 
    "support_link": "https://t.me/your_support",
    "w_methods": ["bKash", "Nagad"],
    "w_group": "", 
    "services": [],              # Admin-added service list for upload
    "num_used_mode": "classic",  # "classic" = allocate=used | "modern" = OTP received=used
    "fj_on": False,
    "fj_channels": [], 
    "search_countries": [],
    "premium_flags": {
        "1": {"char": "🇺🇸", "iso": "US", "name": "United States", "id": "5913463998522592692"},
        "880": {"char": "🇧🇩", "iso": "BD", "name": "Bangladesh", "id": "5911365056594973179"},
        "91": {"char": "🇮🇳", "iso": "IN", "name": "India", "id": "5913754823643107921"},
        "92": {"char": "🇵🇰", "iso": "PK", "name": "Pakistan", "id": "5913705895375672082"},
        "44": {"char": "🇬🇧", "iso": "GB", "name": "United Kingdom", "id": "5913443365499703513"}
    },
    "premium_apps": {
        "FACEBOOK":  {"char": "📘", "id": "5389064576333527180", "name": "Facebook"},
        "INSTAGRAM": {"char": "📸", "id": "5364310996179503764", "name": "Instagram"},
        "TIKTOK":    {"char": "🎵", "id": "5391044040860906456", "name": "TikTok"},
        "TELEGRAM":  {"char": "✈️", "id": "5364125616801073577", "name": "Telegram"},
        "WHATSAPP":  {"char": "💬", "id": "5233354831984353090", "name": "WhatsApp"},
        "TWITTER":   {"char": "🐦", "id": "5233376087777501917", "name": "Twitter/X"},
        "THREADS":   {"char": "🧵", "id": "5233449944035123527", "name": "Threads"},
        "VIBER":     {"char": "📳", "id": "5235445265581755428", "name": "Viber"},
        "DISCORD":   {"char": "🎮", "id": "5233582387941630314", "name": "Discord"},
        "REDDIT":    {"char": "🤖", "id": "5319276623403458717", "name": "Reddit"},
        "PINTEREST": {"char": "📌", "id": "5368456936700263949", "name": "Pinterest"},
        "LINKEDIN":  {"char": "💼", "id": "5321272434576355870", "name": "LinkedIn"},
        "GITHUB":    {"char": "🐱", "id": "5319084384962248505", "name": "GitHub"},
        "CHATGPT":   {"char": "🤖", "id": "5310259124817134249", "name": "ChatGPT"},
        "GROK":      {"char": "🧠", "id": "5319288443153445517", "name": "Grok"},
        "CLAUDE":    {"char": "🧡", "id": "5321196473784773037", "name": "Claude"},
        "GOOGLE":    {"char": "🔍", "id": "5321244246705989720", "name": "Google"},
        "ADOBE":     {"char": "🎨", "id": "5355325791452281549", "name": "Adobe"},
        "APPLE":     {"char": "🍎", "id": "5318795767454923927", "name": "Apple"},
        "NETFLIX":   {"char": "🎬", "id": "5366477429223209600", "name": "Netflix"},
        "AMAZON":    {"char": "📦", "id": "5319204558147188648", "name": "Amazon"},
        "BINANCE":   {"char": "💛", "id": "5388622778817589921", "name": "Binance"},
        "PAYPAL":    {"char": "💰", "id": "5388595952451859597", "name": "PayPal"},
    },
    "custom_messages": DEFAULT_CUSTOM_MESSAGES.copy()
}

FS_KEYS = [
    "admins", "panels", "fw_groups", "otp_link", "withdraw_on", 
    "min_withdraw", "otp_reward", "refer_reward", "refer_per_otp", "refer_max_otps",
    "cooldown", "num_req", "num_share", "support_link", "w_methods", "w_group",
    "services", "search_countries", "fj_on", "fj_channels"
]

number_batches = {}
used_numbers_list = []
NEXA_BASE_URL = "http://nexaotpservice.com"
total_uploaded_stats = 0
total_assigned_stats = 0
processed_otps = {}   # unique_id → timestamp (TTL-based, replaces plain set)
recent_traffic = []
user_banned_cache = {}

# Active HTTP sessions for Auto Captcha Panels
panel_sessions = {}

# 🌟 sAjaxSource (AJAX/DataTable) এবং Fallback HTML Parser Helper Function
def fetch_cpt_panel_cdrs(p, session, check_url):
    res = session.get(check_url, timeout=15)
    html_text = res.text
    
    # সেশন শেষ হয়েছে বা লগইন পেজে রিডাইরেক্ট করেছে কি না তা চেক করা
    if "login" in html_text.lower() or "signin" in html_text.lower() or any(x in html_text for x in ["Sign in to your account", "Please sign in", "Welcome back!"]):
        raise Exception("Session expired")
        
    soup = BeautifulSoup(html_text, 'html.parser')
    s_ajax_source = ""
    for script in soup.find_all("script"):
        script_text = script.string or ""
        match = re.search(r'sAjaxSource":\s*"([^"]+)"', script_text)
        if match:
            s_ajax_source = match.group(1)
            break
            
    results = []
    
    n_col_name = p.get("num_col_name", "number").lower()
    m_col_name = p.get("msg_col_name", "message").lower()
    n_idx = int(p.get("num_col_idx", 1)) - 1 if p.get("num_col_idx") else 1
    m_idx = int(p.get("msg_col_idx", 2)) - 1 if p.get("msg_col_idx") else 2

    # ৫.১ যদি sAjaxSource AJAX লিংক পাওয়া যায়
    if s_ajax_source:
        baseUrl = p.get("login_url", "").split("/client")[0].split("/login")[0].strip()
        if not baseUrl.startswith("http"):
            baseUrl = "http://" + baseUrl
            
        full_ajax_url = ""
        if s_ajax_source.startswith("http"):
            full_ajax_url = s_ajax_source
        elif s_ajax_source.startswith("/"):
            full_ajax_url = f"{baseUrl}{s_ajax_source}"
        else:
            last_slash_idx = check_url.rfind("/")
            current_dir = check_url[:last_slash_idx]
            full_ajax_url = f"{current_dir}/{s_ajax_source}"

        if "iDisplayLength" not in full_ajax_url:
            query_params = "sEcho=1&iColumns=7&iDisplayStart=0&iDisplayLength=250&sSearch=&iSortingCols=1&iSortCol_0=0&sSortDir_0=desc"
            divider = "&" if "?" in full_ajax_url else "?"
            full_ajax_url += f"{divider}{query_params}"

        ajax_headers = {
            "Referer": check_url,
            "X-Requested-With": "XMLHttpRequest"
        }
        
        ajax_res = session.get(full_ajax_url, headers=ajax_headers, timeout=15)
        data_dict = ajax_res.json()
        rows = data_dict.get("aaData", [])
        for row_val in rows:
            if not isinstance(row_val, list):
                continue
                
            if len(row_val) < max(n_idx, m_idx) + 1:
                continue
                
            num_val = row_val[n_idx] if (0 <= n_idx < len(row_val)) else row_val[2]
            msg_val = row_val[m_idx] if (0 <= m_idx < len(row_val)) else row_val[4]
            
            clean_num = re.sub(r'\D', '', str(num_val))
            if clean_num and 5 <= len(clean_num) <= 18:
                otp = extract_otp_code(msg_val)
                if otp and len(msg_val) > 4:
                    results.append({"number": clean_num, "message": msg_val, "otp": otp})
                    
    else:
        # ৫.২ ডাইরেক্ট HTML টেবিল থেকে রিড করার ব্যাকআপ লজিক
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if not rows: continue
            
            final_n_idx = n_idx
            final_m_idx = m_idx
            
            header_cells = rows[0].find_all(['th', 'td'])
            for i, cell in enumerate(header_cells):
                c_text = cell.get_text(strip=True).lower()
                if n_col_name in c_text: final_n_idx = i
                if m_col_name in c_text: final_m_idx = i

            for row in rows:
                cols = row.find_all(['td', 'th'])
                if all(c.name == 'th' for c in cols): continue
                
                if len(cols) > max(final_n_idx, final_m_idx):
                    num_text = cols[final_n_idx].get_text(separator=" ", strip=True)
                    msg_text = cols[final_m_idx].get_text(separator=" ", strip=True)
                    
                    clean_num = re.sub(r'\D', '', num_text)
                    if clean_num and 5 <= len(clean_num) <= 18:
                        otp = extract_otp_code(msg_text)
                        if otp and len(msg_text) > 4:
                            results.append({"number": clean_num, "message": msg_text, "otp": otp})
                            
    return results, html_text

# Track active number sessions to expire them automatically
user_active_sessions = {}

USERS_FILE = "users_data.json"

def _load_users_db():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {}

def _save_users_db(data):
    try:
        tmp = USERS_FILE + ".tmp"
        with open(tmp, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, USERS_FILE)
    except: pass

# ─── Thread-safe lock for all balance operations ───
import threading as _threading
_balance_lock = _threading.Lock()

def load_db():
    global bot_settings, number_batches, used_numbers_list, total_uploaded_stats, total_assigned_stats, recent_traffic, processed_otps
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                saved_settings = data.get("bot_settings", {})
                for key, val in saved_settings.items():
                    if key == "custom_messages":
                        for m_key, m_val in val.items():
                            bot_settings["custom_messages"][m_key] = m_val
                    else:
                        bot_settings[key] = val
                        
                for m_key, m_val in DEFAULT_CUSTOM_MESSAGES.items():
                    if m_key not in bot_settings["custom_messages"]:
                        bot_settings["custom_messages"][m_key] = m_val
                        
                number_batches = data.get("number_batches", {})
                used_numbers_list = data.get("used_numbers_list", [])
                total_uploaded_stats = data.get("total_uploaded_stats", 0)
                total_assigned_stats = data.get("total_assigned_stats", 0)
                recent_traffic = data.get("recent_traffic", [])
                # ── processed_otps রিস্টোর (dedup state, TTL 1hr বেশি পুরনো হলে বাদ) ──
                _saved_processed = data.get("processed_otps", {})
                _now_load = time.time()
                processed_otps = {k: v for k, v in _saved_processed.items() if _now_load - v < 3600}
            print("✅ Local DB Loaded Successfully!")
        except Exception as e:
            print(f"❌ Error loading local DB: {e}")

_db_lock = threading.Lock()

def save_local_db():
    local_data = {
        "bot_settings": bot_settings,
        "number_batches": number_batches,
        "used_numbers_list": used_numbers_list,
        "total_uploaded_stats": total_uploaded_stats,
        "total_assigned_stats": total_assigned_stats,
        "recent_traffic": recent_traffic,
        "processed_otps": processed_otps
    }
    with _db_lock:
        try:
            tmp = DB_FILE + ".tmp"
            with open(tmp, "w", encoding='utf-8') as f:
                json.dump(local_data, f, indent=4)
            os.replace(tmp, DB_FILE)
        except Exception as e:
            pass

def save_db():
    save_local_db()

load_db()

user_states = {}
temp_data = {}
user_cooldowns = {}
pending_withdrawals = {}

# ─── Thread-safe lock for number_batches mutations ───
_batch_lock = threading.Lock()

def _safe_temp(chat_id, *keys):
    """temp_data এর key safely পড়া — missing হলে None return করে, crash করে না।"""
    d = temp_data.get(chat_id, {})
    if len(keys) == 1:
        return d.get(keys[0])
    return tuple(d.get(k) for k in keys)

def _require_temp(chat_id, *keys):
    """temp_data এ সব keys আছে কিনা check করে। না থাকলে False return করে।"""
    d = temp_data.get(chat_id, {})
    return all(k in d for k in keys)

def _cleanup_state(chat_id):
    """State ও temp_data একসাথে clean করা।"""
    user_states.pop(chat_id, None)
    temp_data.pop(chat_id, None)

# ─── Persist pending_withdrawals to disk so bot restart doesn't lose them ───
_PENDING_W_FILE = "pending_withdrawals.json"

def _load_pending_withdrawals():
    if os.path.exists(_PENDING_W_FILE):
        try:
            with open(_PENDING_W_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def _save_pending_withdrawals():
    try:
        tmp = _PENDING_W_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(pending_withdrawals, f, indent=2)
        os.replace(tmp, _PENDING_W_FILE)
    except: pass

pending_withdrawals = _load_pending_withdrawals()

# ==========================================
# Telegram API & Helpers
# ==========================================
tg_session = requests.Session() # 🌟 Keep-Alive Connection (Makes bot 10x faster)

def api_call(method, payload=None):
    url = f"{BASE_URL}/{method}"
    try:
        # 🌟 Added timeout to prevent hanging!
        res = tg_session.post(url, json=payload, timeout=15)
        return res.json()
    except Exception as e:
        return {}

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    return api_call("sendMessage", payload)

def send_photo(chat_id, photo_url_or_file_id, caption="", reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "photo": photo_url_or_file_id, "caption": caption, "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    return api_call("sendPhoto", payload)

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode, "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    return api_call("editMessageText", payload)

def delete_message(chat_id, message_id):
    return api_call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

def answer_callback(callback_id, text="", show_alert=False):
    api_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text, "show_alert": show_alert})

def send_document(chat_id, filename, text_content):
    url = f"{BASE_URL}/sendDocument"
    files = {'document': (filename, text_content)}
    data = {'chat_id': chat_id}
    try: requests.post(url, data=data, files=files)
    except: pass

def generate_emoji_txt(mode):
    """
    'flags' হলে premium_flags ডিকশনারি থেকে, 'apps' হলে premium_apps ডিকশনারি থেকে
    আগের আপলোড-করা txt ফরম্যাটেই (যেমন: (880)(BD)🇧🇩 Bangladesh {"emoji":..., "id":...}) টেক্সট জেনারেট করে।
    এই ফাংশনটা আগে কোথাও define করা ছিল না, তাই Download Flags/Services বাটন কাজ করছিল না।
    """
    lines = []
    if mode == "flags":
        flags_db = bot_settings.get("premium_flags", {})
        for iso, data in sorted(flags_db.items(), key=lambda x: x[1].get("name", x[0])):
            dial_code = data.get("dial_code", "")
            name = data.get("name", iso)
            char = data.get("char", "")
            eid = data.get("id", "")
            if not (dial_code and char and eid):
                continue
            json_part = json.dumps({"emoji": char, "id": int(eid) if str(eid).isdigit() else eid}, ensure_ascii=False)
            lines.append(f"({dial_code})({iso}){char} {name} {json_part}")
    elif mode == "apps":
        apps_db = bot_settings.get("premium_apps", {})
        for key, data in sorted(apps_db.items()):
            name = data.get("name", key)
            char = data.get("char", "")
            eid = data.get("id", "")
            if not (char and eid):
                continue
            json_part = json.dumps({"emoji": char, "id": int(eid) if str(eid).isdigit() else eid}, ensure_ascii=False)
            lines.append(f"{char} {name} {json_part}")

    if not lines:
        return None
    return "\n".join(lines)

# 🌟 Local User List to completely remove Firebase Read Costs!
all_known_users = set()

def sync_users_list():
    global all_known_users
    try:
        users_db = _load_users_db()
        all_known_users = set(users_db.keys())
    except: pass

threading.Thread(target=sync_users_list, daemon=True).start()

def _save_users_list():
    try:
        with open("users_list.json", "w") as f:
            json.dump(list(all_known_users), f)
    except: pass

def register_user_local(uid):
    uid_str = str(uid)
    if uid_str not in all_known_users:
        all_known_users.add(uid_str)
def _update_user_otp_count(user_id):
    """Update user's total OTP count and daily stats - called inside _balance_lock"""
    # NOTE: এই function সবসময় _balance_lock ধরার পরে call করতে হবে
    # কারণ এটা আলাদা read/write করে না — caller update_balance_and_otp() থেকে ডাকা হয়
    uid_str = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    return uid_str, today  # caller নিজেই update করবে



def broadcast_copymessage(from_chat_id, msg_id):
    success = 0
    failed = 0
    users = list(all_known_users)
    
    # 🌟 Dedicated Connection Pool for Broadcast (Fixes Port Exhaustion & Network Lag)
    b_session = requests.Session()
    url = f"{BASE_URL}/copyMessage"
    
    for user_id in users:
        payload = {"chat_id": user_id, "from_chat_id": from_chat_id, "message_id": msg_id}
        try:
            res = b_session.post(url, json=payload, timeout=5).json()
            if res.get("ok"): success += 1
            else: failed += 1
        except:
            failed += 1
        time.sleep(0.035) # Safe speed (28 msgs/sec) to prevent Telegram Ban
        
    send_message(from_chat_id, render_body_text(f"📢 <b>Broadcast Completed!</b>\n✅ Success: {success}\n❌ Failed: {failed}\n👥 Total Sent: {len(users)}"))

def render_body_text(text):
    if not text: return str(text)
    parts = re.split(r'(<tg-emoji.*?</tg-emoji>)', str(text))
    for i in range(len(parts)):
        if not parts[i].startswith('<tg-emoji'):
            for normal_emj, prem_id in GLOBAL_BODY_EMOJIS.items():
                if normal_emj in parts[i]:
                    parts[i] = parts[i].replace(normal_emj, f'<tg-emoji emoji-id="{prem_id}">{normal_emj}</tg-emoji>')
    return "".join(parts)

def extract_premium_html(msg):
    text = msg.get("text", msg.get("caption", ""))
    entities = msg.get("entities", msg.get("caption_entities", []))
    if not entities: return text
    try:
        b_text = text.encode('utf-16-le')
        c_entities = [e for e in entities if e.get("type") == "custom_emoji"]
        c_entities.sort(key=lambda x: x["offset"], reverse=True)
        for ent in c_entities:
            offset = ent["offset"] * 2
            length = ent["length"] * 2
            eid = ent["custom_emoji_id"]
            emoji_char = b_text[offset:offset+length].decode('utf-16-le')
            html_tag = f'<tg-emoji emoji-id="{eid}">{emoji_char}</tg-emoji>'
            replacement = html_tag.encode('utf-16-le')
            b_text = b_text[:offset] + replacement + b_text[offset+length:]
        return b_text.decode('utf-16-le')
    except Exception as e:
        return text 

def get_flag_info_from_num(num):
    """
    নাম্বার থেকে দেশ ডিটেক্ট করার জন্য Google-এর libphonenumber (phonenumbers লাইব্রেরি) ব্যবহার করা হয়।
    এটা +1 / +44 / +7 এর মতো শেয়ার্ড dial code এর ক্ষেত্রেও area code দেখে সঠিক দেশ বের করে।
    premium_flags ডিকশনারি এখন ISO কোড (যেমন "BD", "MG") দিয়ে key করা — তাই কোনো prefix collision হয় না।
    """
    clean = num.replace(" ", "").replace("-", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    iso = None
    try:
        parsed = phonenumbers.parse(clean, None)
        iso = phonenumbers.region_code_for_number(parsed)
    except phonenumbers.NumberParseException:
        iso = None

    flags_db = bot_settings.get("premium_flags", {})

    if iso:
        data = flags_db.get(iso.upper())
        if data:
            char = data.get("char") or data.get("flag", "🌍")
            return char, iso.upper(), data.get("id")
        # ISO ধরা পড়েছে কিন্তু এই দেশের জন্য কোনো প্রিমিয়াম ইমোজি আপলোড করা নেই
        return "🌍", iso.upper(), None

    return "🌍", "XX", None

def get_flag_and_code(num):
    char, iso, _ = get_flag_info_from_num(num)
    return char, iso

def get_flag_char(num):
    char, _ = get_flag_and_code(num)
    return char

def get_iso_code(num):
    _, iso = get_flag_and_code(num)
    return iso or "XX"

# ── Modern OTP Layout (exact reference bot style) ────────────────────────────
UI_EMOJI = {
    "lock":     "5310278924616356636",
    "phone":    "6319056439096644016",
    "channel":  "5201691993775818138",
    "verified": "5044126248029128166",
    "lang_end": "6091471714129023698",
    "dev_end":  "6204087066595171188",
    "copy_sms": "6091617910520812331",
}

def _u16(s: str) -> int:
    """UTF-16-LE length (in code units) — needed for Telegram entity offsets."""
    return len(s.encode("utf-16-le")) // 2

def _fmt_otp(otp: str) -> str:
    otp = str(otp)
    if len(otp) == 6:  return f"{otp[:3]}-{otp[3:]}"
    if len(otp) == 8:  return f"{otp[:4]}-{otp[4:]}"
    if len(otp) == 4:  return f"{otp[:2]}-{otp[2:]}"
    return otp

def build_modern_otp_message(num: str, otp: str, raw_msg: str, service_name: str, fw: dict):
    """
    Build the exact reference-bot modern layout.
    Returns (text, entities, keyboard_dict) for raw Telegram API call.
    """
    # Flag & country code
    flag_char, iso = get_flag_and_code(num)
    masked = mask_number(num if num.startswith("+") else "+" + num)
    lang_tag = detect_language(raw_msg) if raw_msg else "#English"

    # Short → Full form mapping for modern layout
    LANG_FULL = {
        "#EN": "#English", "#AR": "#Arabic", "#BN": "#Bengali", "#HI": "#Hindi",
        "#PA": "#Punjabi", "#GU": "#Gujarati", "#OR": "#Odia", "#TA": "#Tamil",
        "#TE": "#Telugu", "#KN": "#Kannada", "#ML": "#Malayalam", "#SI": "#Sinhala",
        "#TH": "#Thai", "#LO": "#Lao", "#BO": "#Tibetan", "#MY": "#Burmese",
        "#AM": "#Amharic", "#KM": "#Khmer", "#KA": "#Georgian", "#HY": "#Armenian",
        "#HE": "#Hebrew", "#EL": "#Greek", "#RU": "#Russian", "#ZH": "#Chinese",
        "#JA": "#Japanese", "#KO": "#Korean", "#ID": "#Indonesian", "#MS": "#Malay",
        "#VN": "#Vietnamese", "#TL": "#Filipino", "#ES": "#Spanish", "#PT": "#Portuguese",
        "#FR": "#French", "#DE": "#German", "#IT": "#Italian", "#TR": "#Turkish",
        "#PL": "#Polish", "#NL": "#Dutch", "#RO": "#Romanian", "#UK": "#Ukrainian",
        "#CS": "#Czech", "#SK": "#Slovak", "#HU": "#Hungarian", "#SV": "#Swedish",
        "#NO": "#Norwegian", "#DA": "#Danish", "#FI": "#Finnish", "#FA": "#Persian",
        "#UR": "#Urdu",
    }
    lang_tag = LANG_FULL.get(lang_tag, lang_tag)
    otp_fmt = _fmt_otp(otp)

    # Service premium emoji ID
    svc_emoji_id = "5341498088408234504"  # default
    for app_key, app_data in bot_settings.get("premium_apps", {}).items():
        if service_name.upper() in app_key.upper() or app_key.upper() in service_name.upper():
            if "id" in app_data:
                svc_emoji_id = app_data["id"]
                break

    # Country flag premium emoji ID
    country_emoji_id = "5780471598922337683"  # default
    for fc, fd in bot_settings.get("premium_flags", {}).items():
        if fd.get("iso", "").upper() == iso.upper():
            if "id" in fd:
                country_emoji_id = fd["id"]
            break

    SLOT = "🌍"  # placeholder (2 UTF-16 units each)
    DEV_LABEL   = "ɴᴀʏᴇᴇᴍxᴛʏ"
    line1       = f"{SLOT} #{iso}  {SLOT}  {masked}  {lang_tag}{SLOT}"
    footer_pre  = f"{SLOT} ᴅᴇᴠᴇʟᴏᴘᴇᴅ ʙʏ "
    footer_dev  = DEV_LABEL
    footer_end  = SLOT
    footer_full = f"{footer_pre}{footer_dev} {footer_end}"
    text        = f"{line1}\n{footer_full}"

    # UTF-16 entity offsets
    flag_off        = 0
    flag_len        = _u16(SLOT)
    bold_cc_off     = _u16(f"{SLOT} ")
    bold_cc_len     = _u16(f"#{iso}")
    svc_off         = _u16(f"{SLOT} #{iso}  ")
    svc_len         = _u16(SLOT)
    masked_bold_off = _u16(f"{SLOT} #{iso}  {SLOT}  ")
    masked_bold_len = _u16(masked)
    lang_end_off    = _u16(f"{SLOT} #{iso}  {SLOT}  {masked}  {lang_tag}")
    lang_end_len    = _u16(SLOT)
    line2_start     = _u16(line1 + "\n")
    verified_off    = line2_start
    verified_len    = _u16(SLOT)
    italic_off      = line2_start
    italic_len      = _u16(footer_full)
    crush_off       = line2_start + _u16(footer_pre)
    crush_len       = _u16(footer_dev)
    dev_end_off     = line2_start + _u16(footer_pre + footer_dev + " ")
    dev_end_len     = _u16(SLOT)

    entities = [
        {"type": "custom_emoji", "offset": flag_off,        "length": flag_len,        "custom_emoji_id": country_emoji_id},
        {"type": "bold",         "offset": bold_cc_off,     "length": bold_cc_len},
        {"type": "custom_emoji", "offset": svc_off,         "length": svc_len,         "custom_emoji_id": svc_emoji_id},
        {"type": "bold",         "offset": masked_bold_off, "length": masked_bold_len},
        {"type": "custom_emoji", "offset": lang_end_off,    "length": lang_end_len,    "custom_emoji_id": UI_EMOJI["lang_end"]},
        {"type": "custom_emoji", "offset": verified_off,    "length": verified_len,    "custom_emoji_id": UI_EMOJI["verified"]},
        {"type": "italic",       "offset": italic_off,      "length": italic_len},
        {"type": "text_link",    "offset": crush_off,       "length": crush_len,       "url": "https://t.me/nayeemxty"},
        {"type": "custom_emoji", "offset": dev_end_off,     "length": dev_end_len,     "custom_emoji_id": UI_EMOJI["dev_end"]},
    ]

    # Buttons — row1 fixed, row2 configurable per group
    otp_copy_style = fw.get("otp_copy_style", "primary")
    btn1_text  = fw.get("btn1_text", "🤖 Number Bot")
    btn1_url   = fw.get("btn1_url",  bot_settings.get("otp_link", ""))
    btn2_text  = fw.get("btn2_text", "📫 Channel")
    btn2_url   = fw.get("btn2_url",  bot_settings.get("otp_link", ""))
    btn1_style = fw.get("btn1_style", "success")
    btn2_style = fw.get("btn2_style", "danger")

    keyboard = {"inline_keyboard": [
        [
            {"text": f"  {otp_fmt}", "copy_text": {"text": otp},
             "style": otp_copy_style, "icon_custom_emoji_id": UI_EMOJI["lock"]},
            {"text": "  ᴄᴏᴘʏ ꜱᴍꜱ", "copy_text": {"text": raw_msg or otp},
             "style": "primary", "icon_custom_emoji_id": UI_EMOJI["copy_sms"]},
        ],
        [
            {"text": btn1_text, "url": btn1_url, "style": btn1_style,
             "icon_custom_emoji_id": UI_EMOJI["phone"]},
            {"text": btn2_text, "url": btn2_url, "style": btn2_style,
             "icon_custom_emoji_id": UI_EMOJI["channel"]},
        ]
    ]}
    return text, entities, keyboard

def send_modern_otp_to_group(fw: dict, num: str, otp: str, raw_msg: str, service_name: str):
    """Send exact reference-bot modern layout to a group via raw Telegram API."""
    text, entities, keyboard = build_modern_otp_message(num, otp, raw_msg, service_name, fw)
    fw_chat_id = fw["chat_id"]
    payload = {
        "chat_id": fw_chat_id,
        "text": text,
        "entities": entities,
        "reply_markup": keyboard,
        "disable_web_page_preview": True,
        "link_preview_options": {"is_disabled": True},
    }
    if fw.get("topic_id"):
        payload["message_thread_id"] = int(fw["topic_id"])
    try:
        resp = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=15)
        return resp.json()
    except Exception:
        return None

def get_flag_info_html(num_or_iso):
    if len(num_or_iso) == 2:
        data = bot_settings.get("premium_flags", {}).get(num_or_iso.upper())
        if data:
            eid = data.get("id")
            char = data.get("char") or data.get("flag", "🌍")
            if eid: return f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
            return char
        return "🌍"
        
    char, _, eid = get_flag_info_from_num(num_or_iso)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
    return char

def get_service_info_html(service_name, sms_text=""):
    """Returns (full_name, html_emoji_tag) for a service."""
    apps_db = bot_settings.get("premium_apps", {})
    
    # 1. Try detect from SMS text
    detected = detect_service(sms_text) if sms_text else None
    if detected:
        svc_key = detected.upper()
    else:
        svc_key = service_name.upper().strip()

    # 2. Match in premium_apps
    full_name = svc_key.title()
    html_tag  = "📱"
    for app_key, app_data in apps_db.items():
        if (svc_key == app_key.upper() or
                svc_key in app_key.upper() or
                app_key.upper() in svc_key):
            full_name = app_data.get("name", app_key.title())
            eid   = app_data.get("id")
            char  = app_data.get("char", "📱")
            if eid:
                html_tag = f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
            else:
                html_tag = char
            break

    return full_name, html_tag

def mask_number(num):
    clean = num.replace("+", "").replace(" ", "")
    if len(clean) > 6: return f"{clean[:3]}XTY{clean[-3:]}"
    elif len(clean) > 2: return f"{clean[:1]}XTY{clean[-1:]}"
    return clean

# ==========================================
# 🌟 ADVANCED SERVICE & LANGUAGE DETECTION
# ==========================================

SERVICE_SMS_KEYWORDS = {
    "whatsapp": {
        "primary":   ["whatsapp", "whatsapp business", "whatsapp的", "whatsapp验证码"],
        "secondary": ["watsapp", "watsap", "wattsapp", "wa.me"],
        "multilang": ["واتساب", "واتساپ", "واٹس ایپ", "व्हाट्सएप", "वॉट्सऐप", "হোয়াটসঅ্যাপ",
                      "ватсап", "вотсап", "వాట్సాప్", "വാട്‌സ്ആപ്പ്", "வாட்ஸ்அப்", "ವಾಟ್ಸಾಪ್",
                      "วอตส์แอปป์", "ワッツアップ", "왓츠앱", "וואטסאפ", "γουάτσαπ", "ვოთсაپი"],
        "abbr": [],
    },
    "facebook": {
        "primary":   ["facebook", "facebook.com", "fb.com"],
        "secondary": ["fbook", "face book"],
        "multilang": ["فيسبوك", "فيس بوك", "ফেসবুক", "फ़ेसबुक", "フェイスブック", "페이스북", "脸书"],
        "abbr":      ["fb"],
    },
    "instagram": {
        "primary":   ["instagram", "instagram.com"],
        "secondary": ["instagramm", "instagrm"],
        "multilang": ["انستغرام", "انستقرام", "اینستاگرام", "인스타그램", "ইনস্টাগ্রাম"],
        "abbr":      ["insta", "ig"],
    },
    "telegram": {
        "primary":   ["telegram", "telegram.org", "t.me"],
        "secondary": ["telegrm", "telegramm"],
        "multilang": ["تيليجرام", "تلگرام", "Телеграм", "텔레그램", "テレグラム", "টেলিগ্রাম"],
        "abbr":      ["tg", "tele"],
    },
    "tiktok": {
        "primary":   ["tiktok", "tiktok.com", "tik tok"],
        "secondary": ["tikvideo", "tik-tok"],
        "multilang": ["تيك توك", "틱톡", "ティックトック", "تیک توک"],
        "abbr":      [],
    },
    "twitter": {
        "primary":   ["twitter", "twitter.com", "x.com"],
        "secondary": ["twiter", "twitt"],
        "multilang": ["تويتر", "ツイッター", "트위터", "توییتر", "টুইটার"],
        "abbr":      [],
    },
    "threads": {
        "primary":   ["threads", "threads.net"],
        "secondary": [],
        "multilang": ["ثريدز"],
        "abbr":      [],
    },
    "viber": {
        "primary":   ["viber", "viber.com"],
        "secondary": [],
        "multilang": ["فايبر", "فیبر", "바이버", "وایبر"],
        "abbr":      [],
    },
    "discord": {
        "primary":   ["discord", "discord.com", "discord.gg"],
        "secondary": ["discrod"],
        "multilang": ["ديسكورد", "디스코드", "ディスコード", "دیسکورد"],
        "abbr":      [],
    },
    "snapchat": {
        "primary":   ["snapchat", "snapchat.com"],
        "secondary": ["snap chat"],
        "multilang": ["سناب شات", "سناپ چت", "スナップチャット", "스냅챗"],
        "abbr":      ["snap"],
    },
    "reddit": {
        "primary":   ["reddit", "reddit.com"],
        "secondary": [],
        "multilang": ["ريديت", "레딧", "レディット"],
        "abbr":      [],
    },
    "pinterest": {
        "primary":   ["pinterest", "pinterest.com"],
        "secondary": [],
        "multilang": ["بينتيريست", "핀터레스트"],
        "abbr":      [],
    },
    "linkedin": {
        "primary":   ["linkedin", "linkedin.com"],
        "secondary": ["linked in", "linked-in"],
        "multilang": ["لينكد إن", "링크드인", "لینکدین"],
        "abbr":      [],
    },
    "github": {
        "primary":   ["github", "github.com"],
        "secondary": ["git hub"],
        "multilang": ["گیت‌هاب", "깃허브"],
        "abbr":      [],
    },
    "chatgpt": {
        "primary":   ["chatgpt", "chat gpt", "openai", "chatgpt.com", "openai.com"],
        "secondary": [],
        "multilang": ["چت جی پی تی", "챗지피티"],
        "abbr":      [],
    },
    "grok": {
        "primary":   ["grok", "grok.x.ai"],
        "secondary": [],
        "multilang": [],
        "abbr":      [],
    },
    "claude": {
        "primary":   ["claude", "anthropic", "claude.ai"],
        "secondary": [],
        "multilang": [],
        "abbr":      [],
    },
    "google": {
        "primary":   ["google", "gmail", "google.com", "accounts.google"],
        "secondary": ["googlemail", "g-mail"],
        "multilang": ["جوجل", "غوغل", "گوگل", "구글", "グーグル", "গুগল"],
        "abbr":      ["youtube", "google voice"],
    },
    "apple": {
        "primary":   ["apple", "icloud", "apple.com", "appleid"],
        "secondary": ["apple id", "itunes"],
        "multilang": ["آبل", "اپل", "애플", "アップル"],
        "abbr":      [],
    },
    "adobe": {
        "primary":   ["adobe", "adobe.com"],
        "secondary": ["adobe id"],
        "multilang": ["أدوبي", "어도비"],
        "abbr":      [],
    },
    "netflix": {
        "primary":   ["netflix", "netflix.com"],
        "secondary": [],
        "multilang": ["نتفليكس", "넷플릭스", "ネットフリックス", "نتفلیکس"],
        "abbr":      [],
    },
    "amazon": {
        "primary":   ["amazon", "amazon.com", "amzn"],
        "secondary": ["amazon prime", "amazn"],
        "multilang": ["أمازون", "아마존", "アマゾン", "آمازون"],
        "abbr":      [],
    },
    "binance": {
        "primary":   ["binance", "binance.com"],
        "secondary": [],
        "multilang": ["بينانس", "바이낸스", "بایننس"],
        "abbr":      ["bnb"],
    },
    "paypal": {
        "primary":   ["paypal", "paypal.com"],
        "secondary": ["pay pal"],
        "multilang": ["باي بال", "페이팔", "ペイパル", "پی‌پال"],
        "abbr":      [],
    },
    "line":      {"primary": ["line app", "line.me"],           "secondary": ["line verification"], "multilang": ["لاين", "라인", "ライン"],        "abbr": []},
    "wechat":    {"primary": ["wechat", "weixin", "we chat"],   "secondary": [],                    "multilang": ["وي تشات", "微信"],               "abbr": []},
    "signal":    {"primary": ["signal", "signal.org"],          "secondary": [],                    "multilang": ["سيجنال", "시그널"],               "abbr": []},
    "imo":       {"primary": ["imo"],                           "secondary": [],                    "multilang": ["ايمو", "아이모"],                  "abbr": []},
    "microsoft": {"primary": ["microsoft", "outlook.com", "hotmail", "live.com"], "secondary": ["ms account"], "multilang": ["مايكروسوفت", "마이크로소프트"], "abbr": ["msn"]},
    "yahoo":     {"primary": ["yahoo", "yahoo.com", "ymail"],  "secondary": [],                    "multilang": ["ياهو"],                          "abbr": []},
    "coinbase":  {"primary": ["coinbase"],                      "secondary": [],                    "multilang": [],                               "abbr": []},
    "okx":       {"primary": ["okx", "okex"],                   "secondary": [],                    "multilang": [],                               "abbr": []},
    "bybit":     {"primary": ["bybit"],                         "secondary": [],                    "multilang": [],                               "abbr": []},
    "huobi":     {"primary": ["huobi", "htx"],                  "secondary": [],                    "multilang": [],                               "abbr": []},
    "bkash":     {"primary": ["bkash", "b-kash"],               "secondary": [],                    "multilang": ["বিকাশ"],                         "abbr": []},
    "nagad":     {"primary": ["nagad"],                         "secondary": [],                    "multilang": ["নগদ"],                           "abbr": []},
    "rocket":    {"primary": ["rocket", "dutch bangla"],        "secondary": [],                    "multilang": [],                               "abbr": []},
    "uber":      {"primary": ["uber", "ubereats"],              "secondary": ["uber eats"],          "multilang": [],                               "abbr": []},
    "spotify":   {"primary": ["spotify"],                       "secondary": [],                    "multilang": [],                               "abbr": []},
    "steam":     {"primary": ["steam", "steamguard"],           "secondary": ["steam guard"],       "multilang": [],                               "abbr": []},
    "tinder":    {"primary": ["tinder"],                        "secondary": [],                    "multilang": [],                               "abbr": []},
    "1xbet":     {"primary": ["1xbet", "1x bet"],               "secondary": [],                    "multilang": [],                               "abbr": []},
    "ebay":      {"primary": ["ebay"],                          "secondary": [],                    "multilang": [],                               "abbr": []},
    "aliexpress": {"primary": ["aliexpress"],                   "secondary": ["ali express"],       "multilang": [],                               "abbr": []},
    "daraz":     {"primary": ["daraz"],                         "secondary": [],                    "multilang": [],                               "abbr": []},
    "foodpanda": {"primary": ["foodpanda", "food panda"],       "secondary": [],                    "multilang": [],                               "abbr": []},
}

def detect_service(text):
    """
    3-Priority service detection:
    1. Primary (real brand name) — highest confidence
    2. Multilang (brand name in other scripts)
    3. Secondary/abbreviation — lowest
    """
    t = str(text).lower().strip()
    # Priority 1: primary
    for svc, data in SERVICE_SMS_KEYWORDS.items():
        for kw in (data if isinstance(data, list) else data.get("primary", [])):
            if kw in t:
                return svc.upper()
    # Priority 2: multilang
    for svc, data in SERVICE_SMS_KEYWORDS.items():
        if isinstance(data, list): continue
        for kw in data.get("multilang", []):
            if kw in t:
                return svc.upper()
    # Priority 3: secondary + abbr
    for svc, data in SERVICE_SMS_KEYWORDS.items():
        if isinstance(data, list): continue
        for kw in data.get("secondary", []) + data.get("abbr", []):
            if kw in t:
                return svc.upper()
    return None

    clean_s = re.sub(r'[^\w\s]', '', detected_service).strip()
    
    for app_name, data in apps.items():
        if app_name == detected_service or app_name == clean_s or app_name in detected_service or detected_service in app_name:
            full_name = data.get("name", app_name.title())
            char = data.get("char", "📱")
            eid = data.get("id")
            if eid: return full_name, f'<tg-emoji emoji-id="{eid}">{char}</tg-emoji>'
            return full_name, char
            
    if len(detected_service) > 20:
        return "Message", "💬"
        
    return detected_service.title(), "📱"

def detect_language(text):
    if not text: return "#EN"
    text_str = str(text)

    # ১. Unicode Block দিয়ে নিখুঁত বর্ণমালা শনাক্তকরণ (100% Accurate for scripts)
    if any('\u0600' <= c <= '\u06ff' for c in text_str): return "#AR" # Arabic / Persian / Urdu
    if any('\u0980' <= c <= '\u09ff' for c in text_str): return "#BN" # Bengali
    if any('\u0900' <= c <= '\u097f' for c in text_str): return "#HI" # Hindi / Marathi / Nepali
    if any('\u0a00' <= c <= '\u0a7f' for c in text_str): return "#PA" # Punjabi (Gurmukhi)
    if any('\u0a80' <= c <= '\u0aff' for c in text_str): return "#GU" # Gujarati
    if any('\u0b00' <= c <= '\u0b7f' for c in text_str): return "#OR" # Odia
    if any('\u0b80' <= c <= '\u0bff' for c in text_str): return "#TA" # Tamil
    if any('\u0c00' <= c <= '\u0c7f' for c in text_str): return "#TE" # Telugu
    if any('\u0c80' <= c <= '\u0cff' for c in text_str): return "#KN" # Kannada
    if any('\u0d00' <= c <= '\u0d7f' for c in text_str): return "#ML" # Malayalam
    if any('\u0d80' <= c <= '\u0dff' for c in text_str): return "#SI" # Sinhala
    if any('\u0e00' <= c <= '\u0e7f' for c in text_str): return "#TH" # Thai
    if any('\u0e80' <= c <= '\u0eff' for c in text_str): return "#LO" # Lao
    if any('\u0f00' <= c <= '\u0fff' for c in text_str): return "#BO" # Tibetan
    if any('\u1000' <= c <= '\u109f' for c in text_str): return "#MY" # Burmese (Myanmar)
    if any('\u1200' <= c <= '\u137f' for c in text_str): return "#AM" # Amharic (Ethiopic)
    if any('\u1780' <= c <= '\u17ff' for c in text_str): return "#KM" # Khmer
    if any('\u10a0' <= c <= '\u10ff' for c in text_str): return "#KA" # Georgian
    if any('\u0530' <= c <= '\u058f' for c in text_str): return "#HY" # Armenian
    if any('\u0590' <= c <= '\u05ff' for c in text_str): return "#HE" # Hebrew
    if any('\u0370' <= c <= '\u03ff' for c in text_str): return "#EL" # Greek
    if any('\u0400' <= c <= '\u04ff' for c in text_str): return "#RU" # Russian / Ukrainian (Cyrillic)
    if any('\u4e00' <= c <= '\u9fff' for c in text_str): return "#ZH" # Chinese
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text_str): return "#JA" # Japanese
    if any('\uac00' <= c <= '\ud7af' for c in text_str): return "#KO" # Korean

    # ২. OTP Keyword দিয়ে ভাষা শনাক্তকরণ (Latin script languages)
    text_lower = text_str.lower()
    
    # Asian / Pacific
    if any(w in text_lower for w in ["kode verifikasi", "jangan bagikan", "rahasia"]): return "#ID" # Indonesian
    if any(w in text_lower for w in ["kod pengesahan", "jangan kongsi"]): return "#MS" # Malay
    if any(w in text_lower for w in ["mã của bạn", "không chia sẻ", "mã xác minh"]): return "#VN" # Vietnamese
    if any(w in text_lower for w in ["ang iyong code", "huwag ibahagi"]): return "#TL" # Tagalog / Filipino
    
    # European / Americas
    if any(w in text_lower for w in ["código", "tu código", "verificación", "no compartas"]): return "#ES" # Spanish
    if any(w in text_lower for w in ["seu código", "código de verificação", "não compartilhe"]): return "#PT" # Portuguese
    if any(w in text_lower for w in ["code secret", "ne partagez pas", "votre code"]): return "#FR" # French
    if any(w in text_lower for w in ["dein code", "bestätigungscode", "nicht teilen"]): return "#DE" # German
    if any(w in text_lower for w in ["il tuo codice", "codice di verifica", "non condividere"]): return "#IT" # Italian
    if any(w in text_lower for w in ["twój kod", "nie udostępniaj", "kod weryfikacyjny"]): return "#PL" # Polish
    if any(w in text_lower for w in ["doğrulama kodu", "paylaşmayın", "onay kodu"]): return "#TR" # Turkish
    if any(w in text_lower for w in ["jouw code", "verificatiecode", "niet delen"]): return "#NL" # Dutch
    if any(w in text_lower for w in ["din kod", "verifieringskod", "dela inte"]): return "#SV" # Swedish
    if any(w in text_lower for w in ["bekræftelseskode", "del ikke"]): return "#DA" # Danish
    if any(w in text_lower for w in ["bekreftelseskode", "ikke del"]): return "#NO" # Norwegian
    if any(w in text_lower for w in ["vahvistuskoodi", "älä jaa"]): return "#FI" # Finnish
    if any(w in text_lower for w in ["váš kód", "ověřovací kód", "nesdílejte"]): return "#CS" # Czech
    if any(w in text_lower for w in ["overovací kód", "nezdieľajte"]): return "#SK" # Slovak
    if any(w in text_lower for w in ["ellenőrző kód", "ne oszd meg"]): return "#HU" # Hungarian
    if any(w in text_lower for w in ["codul tău", "codul de verificare", "nu partaja"]): return "#RO" # Romanian
    if any(w in text_lower for w in ["kontrolni kod", "kod za potvrdu", "ne delite"]): return "#HR" # Croatian/Serbian
    if any(w in text_lower for w in ["код за потвърждение", "не споделяйте"]): return "#BG" # Bulgarian
    if any(w in text_lower for w in ["ваш код", "код підтвердження"]): return "#UK" # Ukrainian
    
    # African
    if any(w in text_lower for w in ["msimbo wako", "usishiriki"]): return "#SW" # Swahili
    if any(w in text_lower for w in ["verifikasiekode", "moenie deel nie"]): return "#AF" # Afrikaans
    
    # ৩. উপরের কোনোটি না মিললে ডিফল্ট
    return "#EN"

def parse_chat_id(text):
    text = text.strip()
    if text.startswith("-100") or (text.startswith("-") and text[1:].isdigit()):
        return text
    if "t.me/" in text:
        parts = text.split("/")
        username = parts[-1]
        if username: return "@" + username if not username.startswith("@") else username
    if text.startswith("@"):
        return text
    return "@" + text

def is_admin(user_id):
    return user_id in bot_settings["admins"] or user_id == OWNER_ID

def check_force_join(user_id):
    if not bot_settings["fj_on"] or not bot_settings["fj_channels"]: return True
    if is_admin(user_id): return True
    for ch in bot_settings["fj_channels"]:
        res = api_call("getChatMember", {"chat_id": ch, "user_id": user_id})
        if res.get("ok") and res["result"]["status"] not in ["left", "kicked"]: continue
        else: return False
    return True

def send_force_join_msg(chat_id):
    kb = []
    for ch in bot_settings["fj_channels"]:
        url = f"https://t.me/{ch.replace('@', '')}" if ch.startswith("@") else ch
        kb.append([{"text": f"Join Channel", "icon_custom_emoji_id": "5789428375261023681", "url": url, "style": "primary"}])
    kb.append([{"text": "Check Joined", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "check_fj", "style": "success"}])
    send_message(chat_id, render_body_text(f"{PEM['warn']} <b>Please join our channels to use the bot!</b>"), reply_markup={"inline_keyboard": kb})

def is_user_banned(user_id):
    if is_admin(user_id): return False
    if user_id in user_banned_cache and time.time() - user_banned_cache[user_id]['time'] < 60:
        return user_banned_cache[user_id]['banned']
    user_data = get_user(user_id)
    banned = user_data.get("banned", False)
    user_banned_cache[user_id] = {'banned': banned, 'time': time.time()}
    return banned

# ==========================================
# Captcha Auto Login & Parsing Core
# ==========================================
def extract_otp_code(text):
    clean_text = re.sub(r'[\u200B-\u200D\uFEFF]', '', str(text))

    # 1. Multi-part OTPs (e.g. 123-456 or 809-761)
    multi_part = re.search(r'(\d{3}[-\s]+\d{3})|(\d{2}[-\s]+\d{2}[-\s]+\d{2})', clean_text)
    if multi_part:
        # হাইফেন (-) থাকলে সেটা রেখে দিবে, কিন্তু স্পেস থাকলে মুছে একসাথে করে দিবে
        return multi_part.group(0).replace(" ", "")

    # 2. Keyword-based extraction
    otp_keywords = ['code', 'is', 'otp', 'pin', 'verification', 'auth', 'কোড', 'رمز', 'your code']
    keywords_pattern = '|'.join(otp_keywords)
    keyword_match = re.search(rf'(?:{keywords_pattern})\s*(?:is|:|-|=)?\s*([a-z0-9]{{4,10}})', clean_text, re.I)
    if keyword_match and keyword_match.group(1).isdigit():
        return keyword_match.group(1)
        
    keyword_match_rev = re.search(rf'([a-z0-9]{{4,10}})\s*(?:is your|is the|কোড)', clean_text, re.I)
    if keyword_match_rev and keyword_match_rev.group(1).isdigit():
        return keyword_match_rev.group(1)

    # 3. Google OTP
    g_match = re.search(r'G-(\d{6})', clean_text, re.IGNORECASE)
    if g_match: return g_match.group(1)

    # 4. Digit sequences fallback
    digit_matches = re.findall(r'(?<!\d)\d{4,8}(?!\d)', clean_text)
    if digit_matches: return digit_matches[0]

    return None

def parse_panel_response(response_text, p_config=None):
    results = []
    p_type = p_config.get("type", "API Panel") if p_config else "API Panel"
    
    n_col_name = p_config.get("num_col_name", "number").lower() if p_config else "number"
    m_col_name = p_config.get("msg_col_name", "message").lower() if p_config else "message"
    n_idx = int(p_config.get("num_col_idx", 1)) - 1 if p_config and p_config.get("num_col_idx") else 1
    m_idx = int(p_config.get("msg_col_idx", 2)) - 1 if p_config and p_config.get("msg_col_idx") else 2

    if p_type == "Auto Captcha Panel":
        try:
            soup = BeautifulSoup(response_text, 'html.parser')
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if not rows: continue
                
                # 🌟 Option 1 + Smart HTML Detection: কলামের নাম ও ব্যবহারকারীর দেওয়া সিরিয়াল দিয়ে সঠিক পজিশন বের করা
                final_n_idx = n_idx
                final_m_idx = m_idx
                
                # প্রথম রো (Header) চেক করে কলামের আসল সিরিয়াল মিলিয়ে নেওয়া
                header_cells = rows[0].find_all(['th', 'td'])
                for i, cell in enumerate(header_cells):
                    c_text = cell.get_text(strip=True).lower()
                    if n_col_name in c_text: final_n_idx = i
                    if m_col_name in c_text: final_m_idx = i

                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    
                    # হেডার রো (যেখানে সব th থাকে) সেগুলো থেকে ডাটা নিবে না
                    if all(c.name == 'th' for c in cols): continue
                    
                    if len(cols) > max(final_n_idx, final_m_idx):
                        # HTML টেবিল থেকে টেক্সট বের করা
                        num_text = cols[final_n_idx].get_text(separator=" ", strip=True)
                        msg_text = cols[final_m_idx].get_text(separator=" ", strip=True)
                        
                        clean_num = re.sub(r'\D', '', num_text)
                        
                        # নাম্বারটা আসলেই ৫-১৮ ডিজিটের কিনা তা নিশ্চিত করা (যাতে উল্টাপাল্টা টেক্সট না আসে)
                        if clean_num and 5 <= len(clean_num) <= 18:
                            otp = extract_otp_code(msg_text)
                            if otp and len(msg_text) > 4:
                                results.append({"number": clean_num, "message": msg_text, "otp": otp})
        except Exception as e:
            pass
    else:
        try:
            data = json.loads(response_text)
            temp_results = []
            
            def process_item(item):
                pot_nums_list = []
                pot_msg = None
                values = []
                
                if isinstance(item, dict):
                    # ১. প্রথমে পরিচিত JSON Key (যেমন: num, phone, sms) দিয়ে খোঁজার চেষ্টা
                    lower_keys = {str(k).lower(): v for k, v in item.items()}
                    for k in ["number", "num", "phone", "msisdn", "sender"]:
                        if k in lower_keys:
                            clean_val = re.sub(r'\D', '', str(lower_keys[k]))
                            if 5 <= len(clean_val) <= 18:
                                if clean_val not in pot_nums_list: pot_nums_list.append(clean_val)
                    for k in ["message", "msg", "sms", "content", "text"]:
                        if k in lower_keys:
                            val = str(lower_keys[k])
                            if len(val) > 4:
                                pot_msg = val
                                break
                    values = list(item.values())
                elif isinstance(item, list):
                    values = item

                # ২. যদি Key দিয়ে না পাওয়া যায়, তবে Smart Blind Scan (সব ভ্যালু চেক করবে)
                for v in values:
                    if isinstance(v, (dict, list)) or v is None: continue
                    v_str = str(v).strip()
                    
                    # Number Detection: 7 থেকে 18 ডিজিট
                    clean_v = re.sub(r'\D', '', v_str)
                    if 7 <= len(clean_v) <= 18 and not re.search(r'[a-zA-Z]', v_str):
                        # Date/Time/IP এড়ানোর লজিক
                        if not re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', v_str) and not re.search(r'\d{2}:\d{2}:\d{2}', v_str) and "." not in v_str:
                            if clean_v not in pot_nums_list:
                                pot_nums_list.append(clean_v)
                    
                    # Message Detection: 5 অক্ষরের বেশি এবং শুধু সংখ্যা নয়
                    if len(v_str) > 4 and not v_str.isdigit():
                        if extract_otp_code(v_str):
                            if pot_msg is None or len(v_str) > len(pot_msg):
                                pot_msg = v_str
                                
                # 🌟 ৩. Multiple Numbers Logic (User Priority > Second Number > First Number)
                pot_num = None
                if pot_nums_list:
                    matched_user_num = None
                    for n in pot_nums_list:
                        # চেক করবে ইউজারের অ্যাসাইন করা নাম্বারের তালিকায় এই নাম্বারটি আছে কি না
                        if any(n == act_num for sess in user_active_sessions.values() for act_num in sess.get("nums", [])):
                            matched_user_num = n
                            break
                    
                    if matched_user_num:
                        pot_num = matched_user_num
                    elif len(pot_nums_list) >= 2:
                        pot_num = pot_nums_list[1] # ইউজারের কাছে না থাকলে সরাসরি দ্বিতীয় নাম্বারটি নেবে
                    else:
                        pot_num = pot_nums_list[0]
                            
                if pot_num and pot_msg:
                    otp = extract_otp_code(pot_msg)
                    if otp:
                        temp_results.append({"number": pot_num, "message": pot_msg, "otp": otp})
                        
            def traverse_json(node):
                if isinstance(node, list):
                    if len(node) > 0 and not isinstance(node[0], (dict, list)):
                        # It's a flat list representing one record
                        process_item(node)
                    for child in node:
                        if isinstance(child, (dict, list)):
                            traverse_json(child)
                elif isinstance(node, dict):
                    process_item(node)
                    for val in node.values():
                        if isinstance(val, (dict, list)):
                            traverse_json(val)

            traverse_json(data)
            
            # Remove duplicates
            seen = set()
            for r in temp_results:
                uid = f"{r['number']}_{r['otp']}"
                if uid not in seen:
                    seen.add(uid)
                    results.append(r)
        except: pass
        
    return results

# 🌟 Advanced Automated Background Captcha Solver 🌟
def attempt_auto_login(p, idx):
    login_url = p.get("login_url", "").strip()
    if not login_url.startswith("http"):
        login_url = "http://" + login_url
        
    if not login_url.lower().endswith('/login') and not login_url.lower().endswith('.php'):
        login_url = f"{login_url.rstrip('/')}/login"
        
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    })
    
    try:
        res = session.get(login_url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        all_text = res.text
        
        # 1. SOLVE CAPTCHA (Exact bot 3.py logic)
        captcha_match = re.search(r'(\d+\s*[\+\-\*]\s*\d+)\s*[=\?:]', all_text)
        if not captcha_match:
            captcha_match = re.search(r'what is\s*(\d+\s*[\+\-\*]\s*\d+)', all_text, re.I)
        if not captcha_match:
            elements = soup.find_all(["label", "div", "span", "p", "strong"])
            for el in elements:
                txt = el.get_text(separator=" ", strip=True)
                if any(op in txt for op in ["+", "-", "*"]):
                    m = re.search(r'(\d+\s*[\+\-\*]\s*\d+)', txt)
                    if m:
                        captcha_match = m
                        break
                        
        captcha_text = captcha_match.group(1) if captcha_match else "0 + 0"
        answer = "0"
        m2 = re.search(r'(\d+)\s*([\+\-\*])\s*(\d+)', captcha_text)
        if m2:
            a, op, b = int(m2.group(1)), m2.group(2), int(m2.group(3))
            if op == '+': answer = str(a + b)
            elif op == '-': answer = str(a - b)
            elif op == '*': answer = str(a * b)

        # 2. FIND FORM
        form = soup.find("form")
        if not form:
            p["login_status"] = "❌ No login form found"
            return False
            
        action = form.get("action")
        from urllib.parse import urljoin
        post_url = urljoin(login_url, action) if action else login_url

        form_data = {}
        for hidden in form.find_all("input", type="hidden"):
            name = hidden.get("name")
            if name: form_data[name] = hidden.get("value") or ""
        
        user_input = form.find("input", {"name": re.compile(r"user|email|id", re.I)}) or \
                     form.find("input", {"type": "text", "placeholder": re.compile(r"user|email", re.I)}) or \
                     form.find("input", {"type": "text"})
                     
        pass_input = form.find("input", {"name": re.compile(r"pass", re.I)}) or \
                     form.find("input", {"type": "password"})
                     
        captcha_input = form.find("input", {"placeholder": re.compile(r"answer|ans|code|verification|value|captcha", re.I)}) or \
                        form.find("input", {"name": re.compile(r"ans|captcha|ver|code", re.I)})
        
        user_field = user_input.get("name") if user_input else "username"
        pass_field = pass_input.get("name") if pass_input else "password"
        captcha_field = captcha_input.get("name") if captcha_input else "answer"

        form_data[user_field] = p.get("username", "")
        form_data[pass_field] = p.get("password", "")
        if captcha_field:
            form_data[captcha_field] = answer

        # 3. SUBMIT
        login_req = session.post(post_url, data=form_data, allow_redirects=True, timeout=15)
        
        # 4. VERIFY (Exact bot 3.py check logic)
        msg_link = p.get("msg_link", "").strip()
        if not msg_link.startswith("http") and msg_link != "":
            msg_link = "http://" + msg_link
            
        check_url = msg_link if msg_link else f"{login_url.split('/login')[0]}/client/SMSCDRStats"
        
        check_res = session.get(check_url, timeout=10)
        
        if 'logout' in login_req.text.lower() or 'logout' in check_res.text.lower() or 'sms reports' in check_res.text.lower() or 'dashboard' in check_res.text.lower() or 'cdrs' in check_res.text.lower():
            panel_sessions[idx] = session
            p["login_status"] = "✅ Active & Fetching"
            return True
        else:
            # এখানে ফেইল হলে অংক কী পেয়েছিল তা দেখা যাবে
            p["login_status"] = f"❌ Login Failed (Math: {captcha_text} = {answer})"
            return False
            
    except Exception as e:
        p["login_status"] = f"❌ Error: {str(e)[:20]}"
        
    return False

import io

# ══════════════════════════════════════════════════════════════
#                    XISORA PANEL ENGINE
# ══════════════════════════════════════════════════════════════
XISORA_LOGIN_PAGE = "http://94.23.31.29/sms/SignIn"
XISORA_LOGIN_POST = "http://94.23.31.29/sms/signmein"
XISORA_CAPTCHA_URL = "http://94.23.31.29/sms/captcha.php?rand="
XISORA_DATA_URL = "http://94.23.31.29/sms/subclient/ajax/dt_reports.php"

_pending_captcha = {}        # panel_idx → {"chat_id": int, "msg_id": int}
_xisora_sessions = {}        # panel_idx → requests.Session
_xisora_captcha_sent_time = {}  # panel_idx → timestamp (prevent rapid re-send)

def _xisora_get_captcha_image(panel_idx):
    import requests as req_lib
    sess = req_lib.Session()
    _xisora_sessions[panel_idx] = sess
    try:
        sess.get(XISORA_LOGIN_PAGE, timeout=10)
        r = sess.get(XISORA_CAPTCHA_URL + str(int(time.time() * 1000)), timeout=10)
        if r.status_code == 200 and r.content:
            return r.content, sess
    except Exception:
        pass
    return None, sess

def xisora_request_captcha(panel_idx):
    """Send captcha image to admins. Prevents duplicate sends."""
    # Already pending — don't send again
    if panel_idx in _pending_captcha:
        return False
    # Rate limit: don't re-send within 60 seconds
    last_sent = _xisora_captcha_sent_time.get(panel_idx, 0)
    if time.time() - last_sent < 60:
        return False

    if panel_idx >= len(bot_settings.get("panels", [])):
        return False
    p = bot_settings["panels"][panel_idx]
    img, sess = _xisora_get_captcha_image(panel_idx)
    if not img:
        p["login_status"] = "❌ Captcha fetch failed"
        return False

    p["login_status"] = "⏳ Awaiting captcha answer"
    _xisora_sessions[panel_idx] = sess
    _xisora_captcha_sent_time[panel_idx] = time.time()

    sent = False
    for admin_id in bot_settings.get("admins", [OWNER_ID]):
        try:
            resp = requests.post(f"{BASE_URL}/sendPhoto", data={
                "chat_id": admin_id,
                "caption": (f"🔐 <b>XISORA Captcha</b>\n"
                            f"Panel: <b>{p['name']}</b> (idx={panel_idx})\n\n"
                            f"✏️ <b>Reply to this message</b> with the captcha text:"),
                "parse_mode": "HTML"
            }, files={"photo": ("captcha.jpg", io.BytesIO(img), "image/jpeg")}, timeout=15)
            result = resp.json()
            if result.get("ok"):
                _pending_captcha[panel_idx] = {
                    "chat_id": admin_id,
                    "msg_id": result["result"]["message_id"]
                }
                sent = True
                break  # send to first admin only
        except Exception:
            pass
    return sent

def xisora_login_with_captcha(panel_idx, captcha_answer):
    """Login with captcha. Returns True on success."""
    if panel_idx >= len(bot_settings.get("panels", [])):
        _pending_captcha.pop(panel_idx, None)
        return False
    p = bot_settings["panels"][panel_idx]
    sess = _xisora_sessions.get(panel_idx)
    if not sess:
        sess = requests.Session()
        _xisora_sessions[panel_idx] = sess
    try:
        r = sess.post(XISORA_LOGIN_POST, data={
            "username": p.get("username", ""),
            "password": p.get("password", ""),
            "capt": captcha_answer.strip()
        }, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": XISORA_LOGIN_PAGE,
            "User-Agent": "Mozilla/5.0"
        }, timeout=15, allow_redirects=True)

        # Success: redirected away from login page
        ok = (
            "subclient" in r.url.lower() or
            "report" in r.url.lower() or
            "dashboard" in r.url.lower() or
            "sms" in r.url.lower() and "signin" not in r.url.lower()
        )
        # Failure: still on login/signin page
        if "signin" in r.url.lower() or "login" in r.url.lower():
            ok = False

        if ok:
            p["login_status"] = "✅ Online"
            p["xisora_logged_in"] = True
        else:
            p["login_status"] = "❌ Wrong captcha — try again"
            p["xisora_logged_in"] = False
            _xisora_sessions.pop(panel_idx, None)

        save_db()
    except Exception as e:
        p["login_status"] = f"❌ Error: {str(e)[:40]}"
        p["xisora_logged_in"] = False
        ok = False

    # Always clear pending after attempt — CRITICAL to stop loop
    _pending_captcha.pop(panel_idx, None)
    _xisora_captcha_sent_time.pop(panel_idx, None)

    # Notify admin result
    for admin_id in bot_settings.get("admins", [OWNER_ID]):
        try:
            send_message(admin_id, render_body_text(
                f"{'✅ Xisora login successful!' if ok else '❌ Xisora login failed!'}\n"
                f"Panel: <b>{p.get('name','?')}</b>\n"
                f"Status: {p['login_status']}"
            ))
            break
        except: pass

    return ok

def fetch_xisora_otps(panel_idx):
    """Fetch OTPs from Xisora panel. Returns list of {number, otp, message} or None."""
    p = bot_settings["panels"][panel_idx]
    sess = _xisora_sessions.get(panel_idx)
    if not sess:
        return None
    try:
        from datetime import datetime as _dt
        today = _dt.now().strftime("%Y-%m-%d")
        params = {
            "fdate1": f"{today} 00:00:00", "fdate2": f"{today} 23:59:59",
            "ftermination": "", "fnum": "", "fcli": "", "fgdate": "0",
            "fgtermination": "0", "fgnumber": "0", "fgcli": "0", "fg": "0",
            "sEcho": "1", "iColumns": "8", "sColumns": ",,,,,,,",
            "iDisplayStart": "0", "iDisplayLength": "25",
            "mDataProp_0": "0", "mDataProp_1": "1", "mDataProp_2": "2",
            "mDataProp_3": "3", "mDataProp_4": "4", "mDataProp_5": "5",
            "mDataProp_6": "6", "mDataProp_7": "7",
            "sSearch": "", "bRegex": "false",
            "iSortCol_0": "0", "sSortDir_0": "desc", "iSortingCols": "1",
            "_": str(int(time.time() * 1000)),
        }
        r = sess.get(XISORA_DATA_URL, params=params, headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "http://94.23.31.29/sms/subclient/Reports",
        }, timeout=15, allow_redirects=True)

        if "signin" in r.url.lower() or "login" in r.url.lower():
            p["login_status"] = "⏳ Session expired"
            _pending_captcha.pop(panel_idx, None)
            return None
        if r.status_code != 200:
            return None
        data = r.json()
        rows = data.get("aaData", data.get("data", []))
        results = []
        for row in rows:
            try:
                # Columns: 0=date, 1=number, 2=cli, 3=msg, 4=..., 5=..., 6=..., 7=...
                number = str(row[1]).strip() if len(row) > 1 else ""
                msg_text = str(row[3]).strip() if len(row) > 3 else ""
                if not number or not msg_text:
                    continue
                # Extract OTP from message
                otp_match = re.search(r'\b(\d{4,8})\b', msg_text)
                if not otp_match:
                    continue
                results.append({"number": number, "otp": otp_match.group(1), "message": msg_text})
            except Exception:
                continue
        return results
    except Exception:
        return None

PANEL_TEMPLATES_FILE = "panel_templates.txt"
API_TEMPLATES_FILE = "api_templates.txt"

def load_panel_templates():
    """Load CPT panel templates from txt file. Returns list of dicts.
    Format per block:
      PanelName
      http://login_url
      http://data_url
      Number3
      SMS5
      delay=16   (optional)
    """
    templates = []
    if not os.path.exists(PANEL_TEMPLATES_FILE):
        return templates
    try:
        with open(PANEL_TEMPLATES_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        blocks = [b.strip() for b in raw.strip().split("\n\n") if b.strip()]
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if len(lines) < 5:
                continue
            import re as _re
            name      = lines[0]
            login_url = lines[1]
            data_url  = lines[2]
            num_col   = lines[3]
            msg_col   = lines[4]
            delay_s   = 5  # default
            for extra in lines[5:]:
                if extra.lower().startswith("delay="):
                    try: delay_s = int(extra.split("=")[1].strip())
                    except: pass
            m_num = _re.search(r'(\d+)$', num_col)
            m_msg = _re.search(r'(\d+)$', msg_col)
            templates.append({
                "name":         name,
                "login_url":    login_url,
                "data_url":     data_url,
                "num_col_name": _re.sub(r'\d+$', '', num_col),
                "num_col_idx":  int(m_num.group(1)) if m_num else 3,
                "msg_col_name": _re.sub(r'\d+$', '', msg_col),
                "msg_col_idx":  int(m_msg.group(1)) if m_msg else 5,
                "delay_seconds": delay_s,
            })
    except Exception:
        pass
    return templates

def load_api_templates():
    """Load API panel templates from txt file. Returns list of dicts."""
    templates = []
    if not os.path.exists(API_TEMPLATES_FILE):
        return templates
    try:
        with open(API_TEMPLATES_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        blocks = [b.strip() for b in raw.strip().split("\n\n") if b.strip()]
        for block in blocks:
            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if len(lines) < 2:
                continue
            # Format: ProviderName\nAPI_URL_TEMPLATE (with {key} placeholder)
            name     = lines[0]
            url_tmpl = lines[1]
            notes    = lines[2] if len(lines) > 2 else ""
            templates.append({"name": name, "url_template": url_tmpl, "notes": notes})
    except Exception:
        pass
    return templates

def save_panel_template(name, login_url, data_url, num_col, msg_col):
    """Append a new CPT panel template to the file."""
    block = f"{name}\n{login_url}\n{data_url}\n{num_col}\n{msg_col}\n"
    with open(PANEL_TEMPLATES_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + block)

def save_api_template(name, url_template, notes=""):
    """Append a new API panel template to the file."""
    block = f"{name}\n{url_template}\n{notes}\n"
    with open(API_TEMPLATES_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + block)

def panel_templates_keyboard():
    templates = load_panel_templates()
    kb = []
    for i, t in enumerate(templates):
        kb.append([{"text": f"📡 {t['name']}", "callback_data": f"use_cpt_tmpl_{i}", "style": "primary"}])
    kb.append([{"text": "📤 Upload Template File", "callback_data": "upload_cpt_tmpl_file", "style": "success"}])
    kb.append([{"text": "➕ Add New Template Manually", "callback_data": "add_cpt_tmpl_manual", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_cpt_panels", "style": "danger"}])
    return {"inline_keyboard": kb}

def api_templates_keyboard():
    templates = load_api_templates()
    kb = []
    for i, t in enumerate(templates):
        kb.append([{"text": f"🌐 {t['name']}", "callback_data": f"use_api_tmpl_{i}", "style": "primary"}])
    kb.append([{"text": "📤 Upload Template File", "callback_data": "upload_api_tmpl_file", "style": "success"}])
    kb.append([{"text": "➕ Add New Template Manually", "callback_data": "add_api_tmpl_manual", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_api_panels", "style": "danger"}])
    return {"inline_keyboard": kb}

def _save_cpt_from_template(chat_id, t, username, password, delay_s, msg_id_t):
    """Save CPT panel from template data."""
    new_panel = {
        "name": t["name"], "type": "Auto Captcha Panel", "status": "ON",
        "login_url": t["login_url"], "msg_link": t["data_url"],
        "num_col_idx": t["num_col_idx"], "msg_col_idx": t["msg_col_idx"],
        "username": username, "password": password,
        "login_status": "⏳ Pending Auto-Login...",
        "delay_seconds": delay_s, "records": 0
    }
    bot_settings["panels"].append(new_panel)
    save_db()
    _cleanup_state(chat_id)
    if msg_id_t:
        edit_message(chat_id, msg_id_t, render_body_text(
            f"✅ <b>{t['name']}</b> added!\n"
            f"👤 <code>{username}</code> | ⏱ Delay: {delay_s}s"
        ), reply_markup=admin_panel_keyboard())


def panel_monitor_thread():
    global processed_otps, recent_traffic, panel_sessions
    while True:
        try:
            # ── processed_otps TTL cleanup (1 hour) ──
            _now_otp = time.time()
            processed_otps = {k: v for k, v in processed_otps.items() if _now_otp - v < 3600}

            for idx, p in enumerate(bot_settings.get("panels", [])):
                if p.get("status") == "ON":

                    if p.get("type") == "Xisora Panel":
                        # ── Xisora captcha-based panel ──
                        # If already pending captcha — skip
                        if idx in _pending_captcha:
                            continue
                        # If not logged in — request captcha (once)
                        if not p.get("xisora_logged_in"):
                            xisora_request_captcha(idx)
                            continue
                        # Logged in — fetch OTPs
                        rows = fetch_xisora_otps(idx)
                        if rows is None:
                            # Session expired — mark as logged out, will re-captcha next cycle
                            p["xisora_logged_in"] = False
                            p["login_status"] = "⏳ Session expired — awaiting captcha"
                            continue
                        parsed_data = rows

                    elif p.get("type") == "Auto Captcha Panel":
                        sess = panel_sessions.get(idx)
                        if not sess:
                            now = time.time()
                            if now - p.get("last_login_attempt", 0) < 30:
                                continue
                            p["last_login_attempt"] = now
                            success = attempt_auto_login(p, idx)
                            save_db()
                            if not success:
                                continue
                            sess = panel_sessions.get(idx)
                        try:
                            parsed_data, res_text = fetch_cpt_panel_cdrs(p, sess, p["msg_link"])
                            p["login_status"] = "✅ Active & Fetching"
                        except Exception:
                            p["login_status"] = "❌ Session Expired (Retrying...)"
                            del panel_sessions[idx]
                            save_db()
                            continue

                    elif p.get("api_url") or p.get("full_api_url"):
                        full_url = p.get("full_api_url", "").strip()
                        url = p.get("api_url", "").strip()
                        token = p.get("token", "").strip()
                        if not full_url and not url:
                            continue
                        urls_to_try = []
                        if full_url:
                            urls_to_try.append(full_url)
                        else:
                            if "{token}" in url or "{key}" in url:
                                urls_to_try.append(url.replace("{token}", token).replace("{key}", token))
                            elif "token=" in url or "key=" in url:
                                urls_to_try.append(url)
                            else:
                                sep = '&' if '?' in url else '?'
                                urls_to_try.append(f"{url}{sep}token={token}")
                                urls_to_try.append(f"{url}{sep}key={token}&start=0")
                                urls_to_try.append(f"{url}{sep}key={token}")
                        parsed_data = []
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                        for try_url in urls_to_try:
                            try:
                                res = requests.get(try_url, headers=headers, timeout=10)
                                parsed_data = parse_panel_response(res.text, p)
                                if parsed_data:
                                    if not full_url and try_url != url and token:
                                        p["api_url"] = try_url.replace(token, "{token}")
                                        save_db()
                                    break
                            except Exception:
                                continue
                        if not parsed_data:
                            continue
                    else:
                        continue

                    if p.get("type") != "Auto Captcha Panel":
                        limit = p.get("records", 0)
                        if limit > 0:
                            parsed_data = parsed_data[:limit]

                    for item in parsed_data:
                        num = item["number"]
                        otp = item["otp"]
                        msg_text = item["message"]
                        _clean_num_for_id = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                        unique_id = f"{_clean_num_for_id}_{otp}"

                        if unique_id not in processed_otps:
                            processed_otps[unique_id] = time.time()

                            char, iso = get_flag_and_code(num)
                            app_full_name, prem_app_html = get_service_info_html(p.get("name", "Panel"), msg_text)
                            current_time = time.time()

                            recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                            recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num, "time": current_time})
                            save_local_db()

                            display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                            masked = mask_number(display_num)
                            lang = detect_language(msg_text)
                            display_msg = render_body_text(f"╔═══════════════╗\n║ {prem_app_html} {get_flag_info_html(display_num)} {masked} {lang}\n╚═══════════════╝")

                            for fw in bot_settings.get("fw_groups", []):
                                try:
                                    fw_layout = fw.get("layout", "classic")
                                    if fw_layout == "modern":
                                        send_modern_otp_to_group(fw, num, otp, msg_text, app_full_name)
                                    else:
                                        kb = [[{"text": f"{otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                                        for btn in fw.get("buttons", []):
                                            b_obj = {"text": btn["text"], "url": btn["url"], "style": "primary"}
                                            if "icon_custom_emoji_id" in btn:
                                                b_obj["icon_custom_emoji_id"] = btn["icon_custom_emoji_id"]
                                            kb.append([b_obj])
                                        send_message(fw["chat_id"], display_msg, reply_markup={"inline_keyboard": kb})
                                except Exception:
                                    pass

                            owners = []
                            clean_api_num = str(num).replace("+", "").replace(" ", "").replace("-", "").strip()
                            # safe snapshot to avoid RuntimeError: dictionary changed size during iteration
                            sessions_snapshot = dict(user_active_sessions)
                            for uid, session_data in sessions_snapshot.items():
                                for act_num in session_data.get("nums", []):
                                    act_clean = str(act_num).replace("+", "").replace(" ", "").replace("-", "").strip()
                                    if (act_clean == clean_api_num or
                                            (len(act_clean) >= 8 and act_clean.endswith(clean_api_num[-8:])) or
                                            (len(clean_api_num) >= 8 and clean_api_num.endswith(act_clean[-8:]))):
                                        owners.append(uid)
                                        break

                            owners = list(set(owners))
                            for owner_id in owners:
                                not_earn_services = bot_settings.get("not_earn_services", [])
                                svc_name_key = str(app_full_name)
                                if svc_name_key.upper() not in [s.upper() for s in not_earn_services]:
                                    session_info = sessions_snapshot.get(owner_id, {})
                                    session_rate = float(session_info.get("rate", bot_settings.get("otp_reward", 0.1)))
                                    total_earn = session_rate
                                else:
                                    total_earn = 0.0
                                try:
                                    new_bal, actual_earn = update_balance_and_otp(owner_id, total_earn, apply_bonus=True)
                                    flag_html_inbox = get_flag_info_html(display_num)
                                    inbox_msg = render_body_text(
                                        f"New OTP Received ⚡\n\n"
                                        f"Service: {prem_app_html} {svc_name_key}\n"
                                        f"Number: {display_num} {flag_html_inbox}\n"
                                        f"OTP: {otp} 🚀\n"
                                        f"Earn: +{actual_earn} BDT 💰\n"
                                        f"Balance: {new_bal} BDT"
                                    )
                                    inbox_kb = [[{"text": f"📋 Copy OTP: {otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                                    send_message(owner_id, inbox_msg, reply_markup={"inline_keyboard": inbox_kb})

                                    # Modern mode: mark number as truly used after OTP received
                                    if bot_settings.get("num_used_mode", "classic") == "modern":
                                        with _batch_lock:
                                            for b_id, b_data in number_batches.items():
                                                for n_obj in b_data["numbers"]:
                                                    if n_obj["num"].replace("+","") == clean_api_num or clean_api_num.endswith(n_obj["num"].replace("+","")[-8:]):
                                                        if owner_id in n_obj.get("allocated_to", []):
                                                            n_obj["shares"] = n_obj.get("shares", 0) + 1
                                                            n_obj.setdefault("used_by", []).append(owner_id)
                                                            if n_obj["shares"] >= bot_settings.get("num_share", 1):
                                                                n_obj["to_remove"] = True
                                                                used_numbers_list.append(n_obj["num"])
                                            for b_id in number_batches:
                                                number_batches[b_id]["numbers"] = [n for n in number_batches[b_id]["numbers"] if not n.get("to_remove")]
                                            save_db()
                                except Exception:
                                    pass

                # Per-panel delay (default 5s, configurable)
                p_delay = int(p.get("delay_seconds", 5))
                if p_delay > 5:
                    time.sleep(p_delay - 5)  # extra wait beyond the base 5s loop sleep

        except Exception:
            pass
        time.sleep(5)

# ==========================================
# Firebase User Management
# ==========================================
# 🌟 Local User Cache: বারবার Firestore থেকে Read করা বন্ধ করবে!
user_cache = {}

def _default_user(user_id):
    return {"user_id": user_id, "balance": 0.0, "total_refers": 0, "total_otps": 0,
            "banned": False, "verified": False, "otp_dates": [], "bonus_rate": 0.0}

def _get_user_nolock(users_db, user_id):
    """Lock ছাড়া user পড়া — শুধু তখন call করবে যখন caller ইতিমধ্যে _balance_lock ধরে আছে।"""
    uid_str = str(user_id)
    if uid_str in users_db:
        data = users_db[uid_str]
        for k, v in _default_user(user_id).items():
            if k not in data:
                data[k] = v
        return data
    else:
        new_user = _default_user(user_id)
        users_db[uid_str] = new_user
        return new_user

def get_user(user_id):
    """Read fresh from disk. Uses lock only if user doesn't exist yet."""
    uid_str = str(user_id)
    # disk থেকে সরাসরি পড়ি (lock ছাড়া read — JSON read এ race condition নেই)
    users_db = _load_users_db()
    if uid_str in users_db:
        data = users_db[uid_str]
        for k, v in _default_user(user_id).items():
            if k not in data:
                data[k] = v
        user_cache[user_id] = data
        return data
    else:
        # নতুন user — write এ lock দরকার
        with _balance_lock:
            users_db2 = _load_users_db()
            if uid_str not in users_db2:
                new_user = _default_user(user_id)
                users_db2[uid_str] = new_user
                _save_users_db(users_db2)
                user_cache[user_id] = new_user
                return new_user
            else:
                user_cache[user_id] = users_db2[uid_str]
                return users_db2[uid_str]

def update_balance(user_id, amount):
    """Atomic balance update — reads fresh from disk, adds amount, saves immediately."""
    with _balance_lock:
        users_db = _load_users_db()
        uid_str = str(user_id)
        if uid_str not in users_db:
            users_db[uid_str] = _default_user(user_id)
        old_bal = float(users_db[uid_str].get("balance", 0.0))
        new_bal = round(old_bal + float(amount), 4)
        users_db[uid_str]["balance"] = new_bal
        _save_users_db(users_db)
        # cache sync
        if user_id in user_cache:
            user_cache[user_id]["balance"] = new_bal
        return new_bal

def update_balance_and_otp(user_id, amount, apply_bonus=False):
    """Atomically add balance AND increment OTP count in one single file write.
    apply_bonus=True হলে lock এর ভেতরে user এর bonus_rate পড়ে যোগ করে।
    এটা OTP receive হলে call করতে হবে — race condition সম্পূর্ণ দূর করে।"""
    referral_to_pay = None
    actual_earn = 0.0  # inbox message এ দেখানোর জন্য

    with _balance_lock:
        users_db = _load_users_db()
        uid_str = str(user_id)
        if uid_str not in users_db:
            users_db[uid_str] = _default_user(user_id)
        u = users_db[uid_str]

        # bonus_rate lock এর ভেতরে পড়া — সবচেয়ে latest value
        bonus_rate = float(u.get("bonus_rate", 0.0)) if apply_bonus else 0.0
        total_amount = round(float(amount) + bonus_rate, 4)
        actual_earn = total_amount

        # balance add
        old_bal = float(u.get("balance", 0.0))
        new_bal = round(old_bal + total_amount, 4)
        u["balance"] = new_bal
        # otp count
        old_otps = u.get("total_otps", 0)
        new_otps = old_otps + 1
        u["total_otps"] = new_otps
        # date tracking
        today = datetime.now().strftime("%Y-%m-%d")
        dates = u.get("otp_dates", [])
        dates.append(today)
        if len(dates) > 10000:
            dates = dates[-5000:]
        u["otp_dates"] = dates

        # ✅ Referral reward: per-OTP system with max cap
        refer_per_otp = float(bot_settings.get("refer_per_otp", 0.0))
        refer_max_otps = int(bot_settings.get("refer_max_otps", 50))
        if refer_per_otp > 0 and u.get("referred_by") and not u.get("ref_paid"):
            ref_counted = u.get("ref_otps_counted", 0)
            if ref_counted < refer_max_otps:
                inviter_id = u["referred_by"]
                inv_str = str(inviter_id)
                u["ref_otps_counted"] = ref_counted + 1
                if inv_str not in users_db:
                    users_db[inv_str] = _default_user(inviter_id)
                users_db[inv_str]["balance"] = round(
                    float(users_db[inv_str].get("balance", 0.0)) + refer_per_otp, 4)
                if inviter_id in user_cache:
                    user_cache[inviter_id]["balance"] = users_db[inv_str]["balance"]
                # Cap পূর্ণ হলে ref_paid = True
                if u["ref_otps_counted"] >= refer_max_otps:
                    u["ref_paid"] = True
                referral_to_pay = (inviter_id, refer_per_otp, user_id,
                                   u["ref_otps_counted"], refer_max_otps)

        users_db[uid_str] = u
        _save_users_db(users_db)
        if user_id in user_cache:
            user_cache[user_id]["balance"] = new_bal
            user_cache[user_id]["total_otps"] = new_otps
            user_cache[user_id]["otp_dates"] = dates

    # lock এর বাইরে Telegram message পাঠাও
    if referral_to_pay:
        inv_id, inv_reward, from_uid, counted, max_otps = referral_to_pay
        done_mark = "🏁" if counted >= max_otps else "📊"
        ref_msg = (
            f"{PEM['gift']} <b>Referral Bonus!</b>\n"
            f"------------------\n"
            f"💰 <b>+{inv_reward} BDT</b> per OTP\n"
            f"{done_mark} <b>Progress: {counted}/{max_otps} OTPs</b>\n"
            f"------------------\n"
            f"{PEM['user']} <b>From:</b> <code>{from_uid}</code>"
        )
        if counted >= max_otps:
            ref_msg += f"\n\n✅ <b>Max referral OTPs reached! No more bonuses.</b>"
        try:
            send_message(inv_id, render_body_text(ref_msg))
        except: pass

    return new_bal, actual_earn  # (new_balance, actual_earned_including_bonus)


# ==========================================
# UI Keyboards & Menu Builders
# ==========================================
def get_cancel_kb():
    return {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_state", "style": "danger"}]]}

def main_menu(user_id):
    kb = [
        [
            {"text": "Get Number", "icon_custom_emoji_id": "5352995071614549948", "style": "danger"},
            {"text": "Live Traffic", "icon_custom_emoji_id": "5352877703043258544", "style": "success"}
        ],
        [
            {"text": "2F Auth", "icon_custom_emoji_id": "5267421176841398765", "style": "success"},
            {"text": "Profile", "icon_custom_emoji_id": "5193063022226086560", "style": "danger"}
        ],
        [
            {"text": "Support", "icon_custom_emoji_id": "5352892752608663501", "style": "primary"}
        ]
    ]
    if is_admin(user_id): 
        kb.append([{"text": "Admin Panel", "icon_custom_emoji_id": "5420155432272438703", "style": "danger"}])
    return {"keyboard": kb, "resize_keyboard": True}

def get_admin_text():
    users_count = len(all_known_users) # 🌟 Zero Cost User Count!
    total_files = len(number_batches)
    available_nums = sum(len(b["numbers"]) for b in number_batches.values())

    txt = f"""
{PEM['admin']} <b>ADMIN CONTROL PANEL</b> {PEM['admin']}
━━━━━━━━━━━━━━━━━━

{PEM['graph']} <b>DATABASE OVERVIEW</b>
— — — — — — — — — —
{PEM['user']} Users      » {users_count}
{PEM['file']} Files      » {total_files}
{PEM['num']} Numbers    » {total_uploaded_stats}
{PEM['ok']} Assigned   » {total_assigned_stats}
{PEM['rocket']} Available  » {available_nums}

{PEM['graph']} <b>STOCK LEVEL</b>
— — — — — — — — — —
[██████░░░░░░░░░] {available_nums} free
"""
    return render_body_text(txt)

def admin_panel_keyboard():
    return {"inline_keyboard": [
        [{"text": "LEADER BOARD SYSTEM", "icon_custom_emoji_id": "5353032893096567467", "callback_data": "lb_main", "style": "success"}],
        [{"text": "Upload Number", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "upload_num", "style": "primary"},
         {"text": "Delete files", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "delete_files", "style": "danger"}],
        [{"text": "Broadcast", "icon_custom_emoji_id": "5789428375261023681", "callback_data": "broadcast_msg", "style": "success"},
         {"text": "System", "icon_custom_emoji_id": "5420155432272438703", "callback_data": "system_settings", "style": "primary"}],
        [{"text": "Used number", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "show_used", "style": "success"},
         {"text": "Unused number", "icon_custom_emoji_id": "5352597830089347330", "callback_data": "show_unused", "style": "success"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}]
    ]}

def system_settings_keyboard():
    return {"inline_keyboard": [
        [{"text": "Force Join System", "icon_custom_emoji_id": "5420517437885943844", "callback_data": "manage_fj", "style": "primary"},
         {"text": "Admin Management", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "manage_admins", "style": "danger"}],
        [{"text": "OTP Group", "icon_custom_emoji_id": "5190447043545438788", "callback_data": "manage_otp_groups", "style": "danger"},
         {"text": "User Management", "icon_custom_emoji_id": "5193063022226086560", "callback_data": "user_management", "style": "primary"}],
        [{"text": "Panel Management", "icon_custom_emoji_id": "5336879280578138635", "callback_data": "manage_panels", "style": "danger"},
         {"text": "XTY Control", "icon_custom_emoji_id": "5193100774988617665", "callback_data": "xty_control", "style": "primary"}],
        [{"text": "Premium Emoji", "icon_custom_emoji_id": "5352552689983067014", "callback_data": "manage_emojis", "style": "success"},
         {"text": "Menu Design", "icon_custom_emoji_id": "5190751148704833975", "callback_data": "menu_design_list", "style": "primary"}],
        [{"text": "Not Earn Service", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "not_earn_service", "style": "danger"},
         {"text": "Manage Services", "icon_custom_emoji_id": "5337302974806922068", "callback_data": "manage_services", "style": "success"}],
        [{"text": "Admin Stats", "icon_custom_emoji_id": "5352877703043258544", "callback_data": "admin_stats", "style": "success"},
         {"text": "Test OTP Message", "icon_custom_emoji_id": "5190781475468915802", "callback_data": "test_message_flow", "style": "primary"}],
        [{"text": "Import Users", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "import_users", "style": "primary"},
         {"text": "Export Users", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "export_users", "style": "primary"}],
        [{"text": "Reset All Balance", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "reset_all_balance_confirm", "style": "danger"},
         {"text": "Used System", "icon_custom_emoji_id": "5318840353510408444", "callback_data": "toggle_used_mode", "style": "primary"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
    ]}

def get_user_management_text():
    # 🌟 Fast & Free User Management Stats!
    total = len(all_known_users)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txt = f"""➖➖➖➖➖➖➖➖
《 👋 USER VIEW 》
➖➖➖➖➖➖➖➖
📊 LIVE STATISTICS:
➖➖➖➖➖➖➖➖
🫂 TOTAL USERS: {total}
✅ VERIFIED USERS: (Hidden to save DB Cost)
🚫 BANNED USERS: (Hidden to save DB Cost)
➖➖➖➖➖➖➖➖
⌛ UPDATED: {now_str}"""
    return render_body_text(txt)

def user_management_keyboard():
    return {"inline_keyboard": [
        [{"text": "Manage Balance", "icon_custom_emoji_id": "5190576863226933563", "callback_data": "um_manage_balance", "style": "primary"},
         {"text": "Ban/Unban User", "icon_custom_emoji_id": "5334807341109908955", "callback_data": "um_ban_unban", "style": "danger"}],
        [{"text": "User Profile", "icon_custom_emoji_id": "5352861489541714456", "callback_data": "um_user_profile", "style": "success"}],
        [{"text": "Set Bonus Rate", "icon_custom_emoji_id": "5420396762189831222", "callback_data": "set_bonus_rate", "style": "success"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
    ]}

def menu_design_list_keyboard():
    return {"inline_keyboard": [
        [{"text": "Edit /start Menu", "icon_custom_emoji_id": "5395444784611480792", "callback_data": "md_edit_start", "style": "primary"}],
        [{"text": "Edit GET NUMBER", "icon_custom_emoji_id": "5337132498965010628", "callback_data": "md_edit_get_number", "style": "success"},
         {"text": "Edit Search Number", "icon_custom_emoji_id": "5190645917711114179", "callback_data": "md_edit_search_number", "style": "success"}],
        [{"text": "Edit Select Country", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "md_edit_select_country", "style": "primary"}],
        [{"text": "Edit TRAFFIC", "icon_custom_emoji_id": "5353032893096567467", "callback_data": "md_edit_traffic", "style": "primary"},
         {"text": "Edit Refer", "icon_custom_emoji_id": "5420396762189831222", "callback_data": "md_edit_refer", "style": "primary"}],
        [{"text": "Edit WITHDRAWAL", "icon_custom_emoji_id": "5352585194295564660", "callback_data": "md_edit_withdrawal", "style": "danger"},
         {"text": "Edit SUPPORT", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "md_edit_support", "style": "danger"}],
        [{"text": "Reset Defaults", "icon_custom_emoji_id": "5192812028632274956", "callback_data": "md_reset_defaults", "style": "success"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
    ]}

def menu_edit_options_keyboard(menu_key):
    return {"inline_keyboard": [
        [{"text": "Edit Body (Text)", "icon_custom_emoji_id": "5395444784611480792", "callback_data": f"md_text_{menu_key}", "style": "primary"}],
        [{"text": "Edit Inline Buttons", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"md_btns_{menu_key}", "style": "success"}],
        [{"text": "Back to Menus", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "menu_design_list", "style": "danger"}]
    ]}

def menu_buttons_list_keyboard(menu_key):
    kb = []
    btns = bot_settings["custom_messages"].get(menu_key, {}).get("buttons", [])
    for idx, btn in enumerate(btns):
        kb.append([{"text": f"Del: {btn['text']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"md_delbtn_{menu_key}_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Inline Button", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"md_addbtn_{menu_key}", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_edit_{menu_key}", "style": "primary"}])
    return {"inline_keyboard": kb}

def emoji_settings_keyboard():
    return {"inline_keyboard": [
        [{"text": "Upload Flags (TXT)", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "up_flags_txt", "style": "primary"},
         {"text": "Download Flags", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_flags_txt", "style": "success"}],
        [{"text": "Upload Services (TXT)", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "up_apps_txt", "style": "primary"},
         {"text": "Download Services", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_apps_txt", "style": "success"}],
        [{"text": "Delete All Flags", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "del_all_flags", "style": "danger"},
         {"text": "Add Single Emoji", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_single_emoji", "style": "success"}],
        [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]
    ]}

def fj_settings_keyboard():
    status_text = 'ON' if bot_settings['fj_on'] else 'OFF'
    status_icon = "5352694861990501856" if bot_settings['fj_on'] else "5318840353510408444"
    kb = [[{"text": f"STATUS: {status_text}", "icon_custom_emoji_id": status_icon, "callback_data": "toggle_fj", "style": "primary"}]]
    for idx, ch in enumerate(bot_settings["fj_channels"]):
        kb.append([{"text": f"Delete: {ch}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_fj_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Channel", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_fj", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}])
    return {"inline_keyboard": kb}

def admin_settings_keyboard():
    kb = []
    for idx, adm in enumerate(bot_settings["admins"]):
        text_btn = f"Owner: {adm}" if adm == OWNER_ID else f"Delete: {adm}"
        icon_id = "5353032893096567467" if adm == OWNER_ID else "5420130255174145507"
        cb_data = "ignore" if adm == OWNER_ID else f"del_adm_{idx}"
        kb.append([{"text": text_btn, "icon_custom_emoji_id": icon_id, "callback_data": cb_data, "style": "danger" if adm != OWNER_ID else "primary"}])
    kb.append([{"text": "Add Admin", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_adm", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}])
    return {"inline_keyboard": kb}

def otp_groups_list_keyboard():
    kb = [[{"text": "Edit OTP Button Link", "icon_custom_emoji_id": "5420517437885943844", "callback_data": "edit_otp_link", "style": "primary"}]]
    for idx, fg in enumerate(bot_settings["fw_groups"]):
        kb.append([{"text": f"Group: {fg['chat_id']}", "icon_custom_emoji_id": "5193063022226086560", "callback_data": f"manage_fw_{idx}", "style": "primary"}])
    kb.append([{"text": "Add Forward Group", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_fw", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}])
    return {"inline_keyboard": kb}

def specific_fw_group_keyboard(idx):
    if idx >= len(bot_settings["fw_groups"]):
        return {"inline_keyboard": [[{"text": "Back", "callback_data": "manage_otp_groups", "style": "primary"}]]}
    group = bot_settings["fw_groups"][idx]
    kb = []
    # Layout switch
    cur_layout = group.get("layout", "classic")
    other_layout = "modern" if cur_layout == "classic" else "classic"
    layout_icon = "5352694861990501856" if cur_layout == "modern" else "5318840353510408444"
    kb.append([{"text": f"Layout: {cur_layout.upper()} → Switch to {other_layout}", "icon_custom_emoji_id": layout_icon, "callback_data": f"fw_toggle_layout_{idx}", "style": "primary"}])
    # Modern layout buttons (only shown if modern)
    if cur_layout == "modern":
        b1t = group.get("btn1_text", "📢 Channel")
        b2t = group.get("btn2_text", "💬 Group")
        kb.append([{"text": f"Btn1: {b1t}", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"fw_edit_btn1_{idx}", "style": "success"},
                   {"text": f"Btn2: {b2t}", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"fw_edit_btn2_{idx}", "style": "success"}])
    # Classic layout custom buttons
    if cur_layout == "classic":
        for b_idx, btn in enumerate(group.get("buttons", [])):
            kb.append([{"text": f"Del: {btn['text']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_fwbtn_{idx}_{b_idx}", "style": "danger"}])
        kb.append([{"text": "Add Inline Button", "icon_custom_emoji_id": "5420323438508155202", "callback_data": f"add_fwbtn_{idx}", "style": "success"}])
    kb.append([{"text": "Delete This Group", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"del_fw_{idx}", "style": "danger"}])
    kb.append([{"text": "Back to Groups", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "primary"}])
    return {"inline_keyboard": kb}

def services_keyboard():
    kb = []
    for idx, svc in enumerate(bot_settings.get("services", [])):
        kb.append([{"text": f"🗑 {svc}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_service_{idx}", "style": "danger"}])
    kb.append([{"text": "➕ Add Service", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_service", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}])
    return {"inline_keyboard": kb}

def service_select_keyboard_for_upload():
    kb = []
    services = bot_settings.get("services", [])
    row = []
    for i, svc in enumerate(services):
        row.append({"text": svc, "callback_data": f"upload_svc_{svc}", "style": "primary"})
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_upload", "style": "danger"}])
    return {"inline_keyboard": kb}

def xty_control_keyboard():
    w_status = "ON" if bot_settings["withdraw_on"] else "OFF"
    sup_status = "ON" if bot_settings.get("support_link") else "OFF"
    grp_status = "ON" if bot_settings.get("w_group") else "OFF"
    r_per = bot_settings.get("refer_per_otp", 0.0)
    r_max = bot_settings.get("refer_max_otps", 50)
    return {"inline_keyboard": [
        [{"text": f"WITHDRAW: {w_status}", "icon_custom_emoji_id": "5348469219761626211", "callback_data": "xty_toggle_w", "style": "primary"}],
        [{"text": f"MIN WITHDRAW: {bot_settings['min_withdraw']}", "icon_custom_emoji_id": "5352877703043258544", "callback_data": "xty_min_w", "style": "success"},
         {"text": f"OTP REWARD: {bot_settings['otp_reward']}", "icon_custom_emoji_id": "5190576863226933563", "callback_data": "xty_otp_r", "style": "primary"}],
        [{"text": f"REFER/OTP: {r_per} BDT", "icon_custom_emoji_id": "5420396762189831222", "callback_data": "xty_ref_per_otp", "style": "success"},
         {"text": f"REFER MAX: {r_max} OTPs", "icon_custom_emoji_id": "5337172996211648018", "callback_data": "xty_ref_max_otps", "style": "primary"}],
        [{"text": f"COOLDOWN: {bot_settings['cooldown']}s", "icon_custom_emoji_id": "5337172996211648018", "callback_data": "xty_cool", "style": "success"},
         {"text": f"NUM/REQ: {bot_settings['num_req']}", "icon_custom_emoji_id": "5337132498965010628", "callback_data": "xty_num_req", "style": "primary"}],
        [{"text": f"NUM/SHARE: {bot_settings['num_share']}", "icon_custom_emoji_id": "5352862640592949843", "callback_data": "xty_num_share", "style": "success"},
         {"text": f"SUPPORT: {sup_status}", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "xty_sup_link", "style": "primary"}],
        [{"text": "W. METHODS", "icon_custom_emoji_id": "5190899075968441286", "callback_data": "manage_w_methods", "style": "success"},
         {"text": f"W. GROUP: {grp_status}", "icon_custom_emoji_id": "5420517437885943844", "callback_data": "xty_w_group", "style": "primary"}],
        [{"text": "BACK", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]
    ]}

def w_methods_keyboard():
    kb = []
    for idx, m in enumerate(bot_settings["w_methods"]):
        kb.append([{"text": f"Delete: {m}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"del_wm_{idx}", "style": "danger"}])
    kb.append([{"text": "Add Method", "icon_custom_emoji_id": "5420323438508155202", "callback_data": "add_wm", "style": "success"}])
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "xty_control", "style": "primary"}])
    return {"inline_keyboard": kb}

def typed_panels_list_keyboard(p_type):
    panels_of_type = [(idx, p) for idx, p in enumerate(bot_settings["panels"]) if p.get("type") == p_type]
    kb = []
    if not panels_of_type:
        kb.append([{"text": "No panels added yet", "callback_data": "ignore", "style": "primary"}])
    for idx, p in panels_of_type:
        status = p.get("status", "OFF")
        name = p.get("name", "?")
        indicator = "🟢" if status == "ON" else "🔴"
        toggle_style = "success" if status == "ON" else "danger"
        kb.append([
            {"text": f"{indicator} {name}", "callback_data": f"tog_pnl_{idx}", "style": toggle_style},
            {"text": "⚙️ Config", "callback_data": f"conf_pnl_{idx}", "style": "primary"}
        ])
        login_st = p.get("login_status", "")
        if login_st and p_type in ("Auto Captcha Panel", "Xisora Panel"):
            kb.append([{"text": f"   {login_st[:40]}", "callback_data": "ignore", "style": "primary"}])

    if p_type == "API Panel":
        add_cb, del_cb = "add_api_panel", "list_del_api"
        tmpl_cb = "api_templates"
    elif p_type == "Auto Captcha Panel":
        add_cb, del_cb = "add_cpt_panel", "list_del_cpt"
        tmpl_cb = "cpt_templates"
    else:
        add_cb, del_cb = "add_xisora_panel", "list_del_xisora"
        tmpl_cb = None

    row_add = [{"text": "➕ Add Panel", "callback_data": add_cb, "style": "success"}]
    if tmpl_cb:
        row_add.append({"text": "📋 Templates", "callback_data": tmpl_cb, "style": "primary"})
    kb.append(row_add)
    kb.append([
        {"text": "🗑 Delete", "callback_data": del_cb, "style": "danger"},
        {"text": "◀️ Back", "callback_data": "manage_panels", "style": "primary"}
    ])
    return {"inline_keyboard": kb}


def panel_config_keyboard(idx):
    p = bot_settings["panels"][idx]
    
    kb = []
    action_text = "Turn OFF" if p['status'] == 'ON' else "Turn ON"
    action_icon = "5318840353510408444" if p['status'] == 'ON' else "5192812028632274956"
    kb.append([{"text": action_text, "icon_custom_emoji_id": action_icon, "callback_data": f"tog_pnl_{idx}", "style": "danger" if p['status'] == 'ON' else "success"}])
    
    if p["type"] != "Auto Captcha Panel":
        rec_count_text = "All (Unlimited)" if p.get('records', 0) == 0 else str(p.get('records'))
        kb.append([{"text": "Set API URL", "icon_custom_emoji_id": "5420517437885943844", "callback_data": f"set_p_api_{idx}", "style": "primary"}])
        kb.append([{"text": "Set Token", "icon_custom_emoji_id": "5353022963132174959", "callback_data": f"set_p_tok_{idx}", "style": "primary"}])
        kb.append([{"text": "🌐 Full API (URL+Token)", "icon_custom_emoji_id": "5420517437885943844", "callback_data": f"set_p_fapi_{idx}", "style": "primary"}])
        kb.append([{"text": f"Set Records Count: {rec_count_text}", "icon_custom_emoji_id": "5192739271886282680", "callback_data": f"set_p_rec_{idx}", "style": "primary"}])
        
    kb.append([{"text": "Test Connection", "icon_custom_emoji_id": "5352694861990501856", "callback_data": f"test_p_conn_{idx}", "style": "success"}])
        
    back_data = "manage_api_panels"
    if p.get("type") == "Auto Captcha Panel":
        back_data = "manage_cpt_panels"
    elif p.get("type") == "Xisora Panel":
        back_data = "manage_xisora_panels"
    kb.append([{"text": "Back to Providers", "icon_custom_emoji_id": "5267490665117275176", "callback_data": back_data, "style": "danger"}])
    return {"inline_keyboard": kb}

def build_traffic_ui():
    global recent_traffic
    current_time = time.time()
    five_min_ago = current_time - 300  # Last 5 minutes
    
    recent_5min = [t for t in recent_traffic if t.get("time", 0) >= five_min_ago]
    total_count = len(recent_5min)
    
    country_counts = {}
    for t in recent_5min:
        iso = t.get("iso", "XX")
        flag = t.get("flag", "🌍")
        c_name = iso
        for code, fdata in bot_settings.get("premium_flags", {}).items():
            if fdata.get("iso") == iso:
                c_name = fdata.get("name", iso)
                break
        if iso not in country_counts:
            country_counts[iso] = {"count": 0, "flag": flag, "name": c_name}
        country_counts[iso]["count"] += 1
    
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    top_country = "N/A"
    if sorted_countries:
        top_iso, top_data = sorted_countries[0]
        top_flag_html = get_flag_info_html(top_iso)
        top_country = f"{top_flag_html} {top_data['name']}"
    
    txt = f"📈 <b>Live Traffic</b>\n\n"
    txt += f"🕒 <b>Window:</b> Last 5 minutes\n"
    txt += f"📊 <b>Results Sent:</b> {total_count}\n"
    txt += f"🏆 <b>Top Country:</b> {top_country}\n"
    
    if sorted_countries:
        txt += f"\n🌍 <b>Top Countries:</b>\n"
        for i, (iso, data) in enumerate(sorted_countries[:10]):
            prem_flag_html = get_flag_info_html(iso)
            txt += f"{i+1}. {prem_flag_html} {data['name']} — {data['count']}\n"
    else:
        txt += "\n<i>No traffic in the last 5 minutes...</i>\n"
    
    txt = render_body_text(txt)
    kb = [[{"text": "🔄 Refresh", "icon_custom_emoji_id": "5465368548702446780", "callback_data": "refresh_traffic", "style": "primary"}]]
    kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}])
    
    return txt, {"inline_keyboard": kb}

# ==========================================
# Message Handler
# ==========================================
def _do_upload_batch(chat_id, service, country_name, country_iso, rate, new_batch=False):
    """Number batch upload করা — duplicate country হলে new_batch=True তে নতুন নাম দেয়।"""
    global total_uploaded_stats
    if not _require_temp(chat_id, "numbers"):
        send_message(chat_id, render_body_text("❌ Session expired."), reply_markup=main_menu(chat_id))
        _cleanup_state(chat_id)
        return
    raw_numbers = temp_data[chat_id]["numbers"]
    filename = temp_data[chat_id].get("filename", "upload.txt")

    clean_nums = []
    for num in raw_numbers:
        num = num.strip()
        if num:
            if not num.startswith('+'): num = '+' + num
            clean_nums.append(num)

    # Determine final country_name for new batch
    final_country_name = country_name
    final_country_iso = country_iso
    if new_batch:
        # Find existing batches for same service+ISO
        existing_for_iso = [
            b for b in number_batches.values()
            if b.get("service") == service and b.get("country", "").upper() == country_iso.upper()
        ]
        if len(existing_for_iso) == 0:
            # First batch — keep original name
            pass
        elif len(existing_for_iso) == 1:
            # Second batch → rename this new one as "ISO-1"
            final_country_name = f"{country_name}-1"
        else:
            # nth batch → ISO-n
            counter = len(existing_for_iso)
            final_country_name = f"{country_name}-{counter}"

    with _batch_lock:
        batch_id = str(uuid.uuid4())[:8]
        number_batches[batch_id] = {
            "filename": filename,
            "service": service,
            "country": country_iso,
            "country_name": final_country_name,
            "rate": rate,
            "numbers": [{"num": n, "shares": 0, "used_by": []} for n in clean_nums]
        }
        total_uploaded_stats += len(clean_nums)
        save_db()

    app_full_name, prem_app_html = get_service_info_html(service)
    prem_flag_html = get_flag_info_html(clean_nums[0]) if clean_nums else ""
    success_msg = render_body_text(
        f"✅ <b>Upload Complete!</b>\n\n"
        f"📱 Service: {prem_app_html} {app_full_name}\n"
        f"🌍 Country: {prem_flag_html} {final_country_name}\n"
        f"💰 Rate: {rate} BDT/OTP\n"
        f"📊 Numbers: {len(clean_nums)}"
    )
    send_message(chat_id, success_msg, reply_markup=admin_panel_keyboard())
    _cleanup_state(chat_id)

    # Broadcast to all users
    def _broadcast_upload():
        bot_link = f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=start"
        bcast_txt = render_body_text(
            f"🔥 <b>New Numbers Available!</b>\n\n"
            f"📱 Service: <b>{app_full_name}</b> {prem_app_html}\n"
            f"🌍 Country: <b>{final_country_name}</b> {prem_flag_html}\n"
            f"📊 Numbers: <b>{len(clean_nums)}</b>\n\n"
            f"✅ Get your number now!\n"
            f"👇 <a href='{bot_link}'><b>Get Number</b></a>"
        )
        import time as _t
        for u_id in list(all_known_users):
            try:
                requests.post(f"{BASE_URL}/sendMessage", json={
                    "chat_id": u_id,
                    "text": bcast_txt,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }, timeout=5)
            except: pass
            _t.sleep(0.05)
    threading.Thread(target=_broadcast_upload, daemon=True).start()


def handle_message(msg):
    global total_uploaded_stats, total_assigned_stats
    chat_id = msg["chat"]["id"]
    chat_type = msg["chat"].get("type", "private")
    
    if chat_type != "private":
        return
        
    text = msg.get("text", "")
    register_user_local(chat_id)

    # ── Xisora captcha answer detection ────────────────────────────────────
    # If admin replied to the captcha photo message
    if is_admin(chat_id) and text and msg.get("reply_to_message"):
        reply_msg_id = msg["reply_to_message"].get("message_id")
        for panel_idx, pend in list(_pending_captcha.items()):
            if pend.get("chat_id") == chat_id and pend.get("msg_id") == reply_msg_id:
                # Admin answered captcha
                threading.Thread(
                    target=xisora_login_with_captcha,
                    args=(panel_idx, text.strip()),
                    daemon=True
                ).start()
                p_name = bot_settings["panels"][panel_idx].get("name", "?") if panel_idx < len(bot_settings["panels"]) else "?"
                send_message(chat_id, render_body_text(f"🔐 Captcha submitted for <b>{p_name}</b>. Logging in..."))
                return
    # ───────────────────────────────────────────────────────────────────────

    if is_user_banned(chat_id):
        send_message(chat_id, render_body_text("🚫 <b>You are banned from using this bot!</b>\nIf you think this is a mistake, please contact support."))
        return
    
    # --- REFERRAL FIX: Save inviter BEFORE Force Join ---
    if text.startswith("/start"):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            inviter = int(parts[1])
            if inviter != chat_id:
                users_db = _load_users_db()
                if str(chat_id) not in users_db:
                    get_user(chat_id)
                    users_db2 = _load_users_db()
                    if str(chat_id) in users_db2:
                        if not users_db2[str(chat_id)].get("referred_by"):
                            users_db2[str(chat_id)]["referred_by"] = inviter
                            users_db2[str(chat_id)]["ref_paid"] = False
                            _save_users_db(users_db2)
                        
    if not check_force_join(chat_id):
        send_force_join_msg(chat_id)
        return
        
    MAIN_MENU_CMDS = ["Get Number", "GET NUMBER", "Live Traffic", "TRAFFIC", "My Profile", "Profile", "2FA Online", "2FA ONLINE", "🔐 2FA ONLINE", "2F Auth", "Support", "SUPPORT", "Admin Panel"]
    
    is_main_cmd = False
    if text in MAIN_MENU_CMDS or text.startswith("/start"):
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        is_main_cmd = True
    
    if chat_id in user_states and not is_main_cmd:
        state = user_states[chat_id]
        
        # 🌟 Auto Captcha Panel Setup Flow 
        if state == "wait_for_cpanel_url" and text:
            temp_data[chat_id]["p_data"]["login_url"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_user"
            send_message(chat_id, render_body_text("2️⃣ <b>Username</b>\n➡️ Panel এর Username দিন:"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_user" and text:
            temp_data[chat_id]["p_data"]["username"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_pass"
            send_message(chat_id, render_body_text("3️⃣ <b>Password</b>\n➡️ Panel এর Password দিন:"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_pass" and text:
            temp_data[chat_id]["p_data"]["password"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_msg_link"
            send_message(chat_id, render_body_text("4️⃣ <b>Message Link</b>\n➡️ যেখান থেকে SMS/OTP ডাটা (JSON) আসবে সেই Link দিন:"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_link" and text:
            temp_data[chat_id]["p_data"]["msg_link"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_num_col_name"
            send_message(chat_id, render_body_text("5️⃣ <b>Number Column Name</b>\n➡️ Data তে Number column এর নাম কী? (যেমন: number, phone):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_num_col_name" and text:
            temp_data[chat_id]["p_data"]["num_col_name"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_num_col_idx"
            send_message(chat_id, render_body_text("6️⃣ <b>Number Column Serial</b>\n➡️ Number Column এর Serial Number কত? (যেমন: 3, 5):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_num_col_idx" and text:
            if text.isdigit():
                temp_data[chat_id]["p_data"]["num_col_idx"] = int(text)
                user_states[chat_id] = "wait_for_cpanel_msg_col_name"
                send_message(chat_id, render_body_text("7️⃣ <b>Message Column Name</b>\n➡️ Message/OTP column এর নাম কী? (যেমন: message, sms):"), reply_markup=get_cancel_kb())
            else:
                 send_message(chat_id, render_body_text("❌ Please enter a valid number serial!"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_col_name" and text:
            temp_data[chat_id]["p_data"]["msg_col_name"] = text.strip()
            user_states[chat_id] = "wait_for_cpanel_msg_col_idx"
            send_message(chat_id, render_body_text("8️⃣ <b>Message Column Serial</b>\n➡️ Message Column এর Serial Number কত? (যেমন: 5, 7):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_cpanel_msg_col_idx" and text:
            if text.isdigit():
                temp_data[chat_id]["p_data"]["msg_col_idx"] = int(text)
                temp_data[chat_id]["p_data"]["login_status"] = "⏳ Pending Auto-Login..."
                
                # Delay question before saving
                user_states[chat_id] = "wait_for_cpt_delay_choice"
                try:
                    sent = send_message(chat_id, render_body_text(
                        f"⏱ <b>Add custom delay?</b>\n\n"
                        f"Some panels return errors if refreshed too quickly.\n"
                        f"Set a custom delay between requests?"
                    ), reply_markup={"inline_keyboard": [
                        [{"text": "✅ Yes — Set Delay", "callback_data": "cpt_delay_yes", "style": "success"},
                         {"text": "❌ No — Default (5s)", "callback_data": "cpt_delay_no", "style": "danger"}]
                    ]})
                    new_msg_id = sent.get("result", {}).get("message_id") if sent else None
                    if new_msg_id:
                        temp_data[chat_id]["msg_id"] = new_msg_id
                except Exception as e:
                    send_message(chat_id, render_body_text(f"❌ Error showing delay options: {e}"), reply_markup=get_cancel_kb())
            else:
                send_message(chat_id, render_body_text("❌ Please enter a valid number serial!"), reply_markup=get_cancel_kb())
            return

        # --- User Management Flows ---
        elif state == "wait_for_um_bal_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID! Please send a numeric User ID."), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            users_db = _load_users_db()
            if str(target_uid) not in users_db:
                send_message(chat_id, render_body_text("❌ User not found!"), reply_markup=get_cancel_kb())
                return
            current_bal = users_db[str(target_uid)].get('balance', 0.0)
            temp_data[chat_id]["target_uid"] = target_uid
            user_states[chat_id] = "wait_for_um_bal_amt"
            send_message(chat_id, render_body_text(f"✅ User found!\n💰 Current Balance: {current_bal} ৳\n\n📝 Send the amount to ADD (e.g. 50) or REMOVE (e.g. -50):"), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_um_bal_amt" and text:
            try:
                amt = float(text.strip())
                target_uid = temp_data[chat_id]["target_uid"]
                update_balance(target_uid, amt)
                send_message(chat_id, render_body_text(f"{PEM['ok']} Balance updated successfully for {target_uid}!"), reply_markup=main_menu(chat_id))
                send_message(target_uid, render_body_text(f"🔔 Your balance has been adjusted by <b>{amt} ৳</b> by an Admin."))
                del user_states[chat_id]
                del temp_data[chat_id]
            except ValueError:
                send_message(chat_id, render_body_text("❌ Invalid amount! Please send a number."), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_um_ban_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID!"), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            users_db = _load_users_db()
            uid_str = str(target_uid)
            if uid_str not in users_db:
                send_message(chat_id, render_body_text("❌ User not found!"), reply_markup=get_cancel_kb())
                return
            current_status = users_db[uid_str].get("banned", False)
            new_status = not current_status
            users_db[uid_str]["banned"] = new_status
            _save_users_db(users_db)
            if target_uid in user_cache: user_cache[target_uid]["banned"] = new_status
            user_banned_cache[target_uid] = {'banned': new_status, 'time': time.time()}
            status_text = "BANNED 🚫" if new_status else "UNBANNED ✅"
            send_message(chat_id, render_body_text(f"✅ User {target_uid} has been {status_text}!"), reply_markup=main_menu(chat_id))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_um_prof_uid" and text:
            target_uid_str = text.strip()
            if not target_uid_str.isdigit():
                send_message(chat_id, render_body_text("❌ Invalid ID!"), reply_markup=get_cancel_kb())
                return
            target_uid = int(target_uid_str)
            users_db = _load_users_db()
            uid_str = str(target_uid)
            if uid_str not in users_db:
                send_message(chat_id, render_body_text("❌ User not found!"), reply_markup=get_cancel_kb())
                return
            data = users_db[uid_str]
            is_verified = True if data.get('total_otps', 0) > 0 else data.get('verified', False)
            prof_text = f"""➖➖➖➖➖➖➖➖
👤 <b>USER PROFILE</b>
➖➖➖➖➖➖➖➖
🆔 ID: <code>{target_uid}</code>
💰 Balance: {data.get('balance', 0.0):.4f} BDT
🤝 Total Refers: {data.get('total_refers', 0)}
🔐 Total OTPs: {data.get('total_otps', 0)}
✅ Verified: {is_verified}
🚫 Banned: {data.get('banned', False)}
➕ Bonus Rate: {data.get('bonus_rate', 0.0)} BDT
➖➖➖➖➖➖➖➖"""
            kb = {"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "user_management", "style": "primary"}]]}
            send_message(chat_id, render_body_text(prof_text), reply_markup=kb)
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        # --- Menu Design Flow ---
        elif state == "wait_for_menu_text" and text:
            try:
                menu_key = temp_data[chat_id]["menu_key"]
                formatted_html_text = extract_premium_html(msg)
                
                bot_settings["custom_messages"][menu_key]["text"] = formatted_html_text
                save_db()
                
                delete_message(chat_id, msg["message_id"])
                
                preview_text = render_body_text(formatted_html_text)
                success_text = f"{PEM['ok']} <b>Message Body Updated successfully!</b>\n\n🎨 <b>Editing: {menu_key.upper()}</b>\n\nPreview of current Text:\n{preview_text}"
                edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(success_text), reply_markup=menu_edit_options_keyboard(menu_key))
            except Exception as e:
                send_message(chat_id, f"❌ Error saving text: {e}")
            finally:
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
            return
            
        elif state == "wait_for_menu_btn" and text:
            try:
                menu_key = temp_data[chat_id]["menu_key"]
                if "-" in text:
                    parts = text.split("-", 1)
                    btn_text = parts[0].strip()
                    btn_url = parts[1].strip()
                    
                    emoji_id = None
                    emoji_char = ""
                    for ent in msg.get("entities", []):
                        if ent.get("type") == "custom_emoji":
                            emoji_id = ent.get("custom_emoji_id")
                            offset = ent.get("offset", 0)
                            length = ent.get("length", 0)
                            b_text = text.encode('utf-16-le')
                            emoji_char = b_text[offset*2:(offset+length)*2].decode('utf-16-le')
                            break
                            
                    if emoji_char:
                        btn_text = btn_text.replace(emoji_char, "").strip()
                        
                    btn_data = {"text": btn_text, "url": btn_url, "style": "primary"}
                    if emoji_id:
                        btn_data["icon_custom_emoji_id"] = emoji_id
                        
                    bot_settings["custom_messages"][menu_key]["buttons"].append(btn_data)
                    save_db()
                    delete_message(chat_id, msg["message_id"])
                    edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"{PEM['gear']} <b>Edit Inline Buttons: {menu_key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(menu_key))
                else:
                    send_message(chat_id, render_body_text(f"{PEM['no']} Invalid format. Use <code>Button Text - https://link.com</code>"))
            except Exception as e:
                 pass
            finally:
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
            return

        elif state == "wait_for_test_service" and text:
            temp_data[chat_id]["service"] = text.strip()
            user_states[chat_id] = "wait_for_test_number"
            send_message(chat_id, render_body_text("📝 Send the Number (e.g. +8801712345678):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_number" and text:
            temp_data[chat_id]["number"] = text.strip()
            user_states[chat_id] = "wait_for_test_otp"
            send_message(chat_id, render_body_text("📝 Send the OTP (e.g. 556677):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_otp" and text:
            temp_data[chat_id]["otp"] = text.strip()
            user_states[chat_id] = "wait_for_test_lang"
            send_message(chat_id, render_body_text("📝 Send the Language (e.g. EN, AR):"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_test_lang" and text:
            lang = text.strip().upper()
            if not lang.startswith("#"):
                lang = "#" + lang
                
            srv = temp_data[chat_id].get("service", "TEST")
            num = temp_data[chat_id].get("number", "+8801700000000")
            otp = temp_data[chat_id].get("otp", "123456")
            
            masked = mask_number(num)
            prem_flag_html = get_flag_info_html(num)
            app_full_name, prem_app_html = get_service_info_html(srv)
            
            msg_text_display = render_body_text(f"╔═══════════════╗\n║ {prem_app_html} {prem_flag_html} {masked} {lang}\n╚═══════════════╝")
            
            sent_count = 0
            errors = []
            if not bot_settings.get("fw_groups"):
                send_message(chat_id, render_body_text("⚠️ No OTP Groups configured! Add a group first from Settings → OTP Group."), reply_markup=main_menu(chat_id))
                _cleanup_state(chat_id)
                return

            for fw in bot_settings["fw_groups"]:
                try:
                    if fw.get("layout", "classic") == "modern":
                        result = send_modern_otp_to_group(fw, num, otp, f"Your OTP is {otp}", srv)
                        if result and result.get("ok"):
                            sent_count += 1
                        else:
                            errors.append(f"Group {fw.get('chat_id')}: {result.get('description', 'unknown error') if result else 'no response'}")
                    else:
                        kb = [[{"text": f"{otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                        for btn in fw.get("buttons", []):
                            b_obj = {"text": btn["text"], "url": btn["url"], "style": "primary"}
                            if "icon_custom_emoji_id" in btn: b_obj["icon_custom_emoji_id"] = btn["icon_custom_emoji_id"]
                            kb.append([b_obj])
                        result = send_message(fw["chat_id"], msg_text_display, reply_markup={"inline_keyboard": kb})
                        if result and result.get("ok"):
                            sent_count += 1
                        else:
                            errors.append(f"Group {fw.get('chat_id')}: {result.get('description', 'failed') if result else 'no response'}")
                except Exception as e:
                    errors.append(f"Group {fw.get('chat_id')}: {str(e)}")
            
            result_msg = f"✅ Test sent to {sent_count}/{len(bot_settings['fw_groups'])} groups!"
            if errors:
                result_msg += "\n\n❌ Errors:\n" + "\n".join(errors[:5])
            send_message(chat_id, render_body_text(result_msg), reply_markup=main_menu(chat_id))
            _cleanup_state(chat_id)
            return

        elif state == "wait_for_emoji_extract":
            entities = msg.get("entities", [])
            custom_emoji_id = None
            emoji_text = ""
            for ent in entities:
                if ent.get("type") == "custom_emoji":
                    custom_emoji_id = ent.get("custom_emoji_id")
                    offset = ent.get("offset", 0)
                    length = ent.get("length", 0)
                    b_text = msg.get("text", "").encode('utf-16-le')
                    emoji_text = b_text[offset*2:(offset+length)*2].decode('utf-16-le')
                    break
            
            if custom_emoji_id:
                temp_data[chat_id] = {"id": custom_emoji_id, "char": emoji_text}
                user_states[chat_id] = "wait_for_emoji_details"
                send_message(chat_id, render_body_text(f"{PEM['ok']} Emoji ID পাওয়া গেছে: <code>{custom_emoji_id}</code>\n\n📌 এখন এটি সেভ করার জন্য টাইপ এবং নাম লিখুন।\n\n<b>ফরমেট:</b>\n`FLAG | 880 | BD | Bangladesh`\nঅথবা\n`APP | WhatsApp`"), reply_markup=get_cancel_kb())
            else:
                send_message(chat_id, render_body_text(f"{PEM['no']} কোনো Premium Emoji পাওয়া যায়নি! দয়া করে Custom Emoji সেন্ড করুন।"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_emoji_details" and text:
            parts = [p.strip() for p in text.split("|")]
            mode = parts[0].upper()
            eid = temp_data[chat_id]["id"]
            char = temp_data[chat_id]["char"]
            
            if mode == "FLAG" and len(parts) == 4:
                code, iso, name = parts[1], parts[2], parts[3]
                bot_settings["premium_flags"][iso.upper()] = {"char": char, "iso": iso.upper(), "name": name, "id": eid, "dial_code": code}
                save_db()
                send_message(chat_id, render_body_text(f"{PEM['ok']} Flag Emoji সেভ হয়েছে!\nISO: {iso.upper()} | Name: {name}"), reply_markup=emoji_settings_keyboard())
            elif mode == "APP" and len(parts) == 2:
                name = parts[1]
                bot_settings["premium_apps"][name.upper()] = {"char": char, "id": eid, "name": name.title()}
                save_db()
                send_message(chat_id, render_body_text(f"{PEM['ok']} App Emoji সেভ হয়েছে!\nName: {name}"), reply_markup=emoji_settings_keyboard())
            else:
                send_message(chat_id, render_body_text(f"{PEM['no']} ফরম্যাট ভুল!\n\nসঠিক ফরম্যাট:\n`FLAG | 880 | BD | Bangladesh`\n`APP | WhatsApp`"))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state in ["wait_for_flag_txt", "wait_for_app_txt"] and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text(f"{PEM['no']} Please upload a .txt file only."))
                return
            file_id = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            content = requests.get(f"{FILE_URL}{file_path}").text
            
            mode = "flags" if state == "wait_for_flag_txt" else "apps"
            count = 0
            
            if mode == "flags":
                for line in content.splitlines():
                    json_match = re.search(r'(\{.*\})', line)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(1))
                            char = data.get("emoji")
                            eid = data.get("id")
                            prefix_str = line[:json_match.start()].strip()
                            # Extract dial code — first (digits) group
                            code_match = re.search(r'\((\d+)\)', prefix_str)
                            # Extract ISO — first (letters) group
                            iso_match = re.search(r'\(([A-Za-z]{2,3})\)', prefix_str)
                            if code_match and iso_match and char and eid:
                                dial_code = code_match.group(1)
                                iso = iso_match.group(1).upper()
                                name = prefix_str\
                                    .replace(f"({dial_code})", "")\
                                    .replace(f"({iso_match.group(1)})", "")\
                                    .replace(char, "").strip()
                                # ISO কোড দিয়ে key করা হয় (প্রতিটা দেশের ISO ইউনিক, তাই কোনো collision হয় না —
                                # যেমন আগে dial_code দিয়ে key করায় +1/+44 এর মতো শেয়ার্ড কোডে ভুল দেশ বসে যেত)
                                bot_settings["premium_flags"][iso] = {
                                    "char": char, "iso": iso,
                                    "name": name, "id": eid,
                                    "dial_code": dial_code
                                }
                                count += 1
                        except: pass
            else:
                for line in content.splitlines():
                    json_match = re.search(r'(\{.*\})', line)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(1))
                            char = data.get("emoji")
                            eid = data.get("id")
                            
                            name_part = line[:json_match.start()].strip()
                            name = name_part.replace(char, '').strip() if char else name_part
                            
                            if char and eid and name:
                                bot_settings["premium_apps"][name.upper()] = {"char": char, "id": eid, "name": name}
                                count += 1
                        except: pass
            
            save_db()
            send_message(chat_id, render_body_text(f"{PEM['ok']} Successfully loaded {count} Emojis!"), reply_markup=emoji_settings_keyboard())
            del user_states[chat_id]
            return

        elif state == "wait_for_broadcast":
            msg_id = msg["message_id"]
            send_message(chat_id, render_body_text(f"{PEM['ok']} Broadcast started..."))
            threading.Thread(target=broadcast_copymessage, args=(chat_id, msg_id)).start()
            del user_states[chat_id]
            return

        elif state == "wait_for_cpt_tmpl_file" and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text("❌ Please upload a .txt file!"))
                return
            file_id = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            content = requests.get(f"{FILE_URL}{file_path}").text
            # Overwrite the templates file
            with open(PANEL_TEMPLATES_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            templates = load_panel_templates()
            msg_id_t = temp_data[chat_id].get("msg_id")
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t,
                             render_body_text(f"✅ <b>{len(templates)}</b> CPT panel templates loaded!"),
                             reply_markup=panel_templates_keyboard())
            return

        elif state == "wait_for_api_tmpl_file" and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text("❌ Please upload a .txt file!"))
                return
            file_id = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            content = requests.get(f"{FILE_URL}{file_path}").text
            with open(API_TEMPLATES_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            templates = load_api_templates()
            msg_id_t = temp_data[chat_id].get("msg_id")
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t,
                             render_body_text(f"✅ <b>{len(templates)}</b> API panel templates loaded!"),
                             reply_markup=api_templates_keyboard())
            return

        elif state == "wait_for_txt" and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text(f"{PEM['no']} Please upload a .txt file only."))
                return
            file_id = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_content = requests.get(f"{FILE_URL}{file_path}").text

            raw_numbers = [n.strip() for n in file_content.splitlines() if n.strip()]
            if not raw_numbers:
                send_message(chat_id, render_body_text("❌ No numbers found in file!"))
                return

            # Auto-detect country from first number using proper longest-prefix matching
            first_num = raw_numbers[0].replace("+", "").replace(" ", "").replace("-", "")
            detected_country = None
            detected_iso = None

            # Use get_flag_info_from_num — longest-prefix matching
            flag_char, iso_code, flag_eid = get_flag_info_from_num(first_num)
            flags_db_up = bot_settings.get("premium_flags", {})

            if iso_code and iso_code != "XX":
                detected_iso = iso_code
                # Find country name: match by ISO — but also get the dial code for exact lookup
                # sorted longest-first so same code as get_flag_info_from_num
                sorted_keys = sorted(flags_db_up.keys(), key=len, reverse=True)
                for fc in sorted_keys:
                    if first_num.startswith(fc):
                        fd = flags_db_up[fc]
                        detected_country = fd.get("name", iso_code)
                        detected_iso = fd.get("iso", iso_code)
                        break
                if not detected_country:
                    detected_country = iso_code

            temp_data[chat_id] = {
                "numbers": raw_numbers,
                "filename": doc["file_name"],
                "detected_country": detected_country,
                "detected_iso": detected_iso
            }

            services = bot_settings.get("services", [])
            if services:
                user_states[chat_id] = "wait_for_service_select"
                country_info = f"🌍 Country: <b>{detected_country}</b> (auto-detected)\n\n" if detected_country else "⚠️ Country not auto-detected\n\n"
                send_message(chat_id, render_body_text(
                    f"✅ File received: <b>{len(raw_numbers)} numbers</b>\n{country_info}"
                    f"📌 Select a service:"
                ), reply_markup=service_select_keyboard_for_upload())
            else:
                # No services configured — fallback to text input
                user_states[chat_id] = "wait_for_service"
                send_message(chat_id, render_body_text(
                    f"✅ File received ({len(raw_numbers)} numbers)\n"
                    f"⚠️ No services configured. Enter service name manually:"
                ), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_import_txt" and "document" in msg:
            doc = msg["document"]
            if not doc["file_name"].endswith(".txt"):
                send_message(chat_id, render_body_text("❌ Please upload a .txt file!"))
                return
            file_id = doc["file_id"]
            file_info = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            content = requests.get(f"{FILE_URL}{file_path}").text
            imported = 0
            skipped = 0
            with _balance_lock:
                users_db_imp = _load_users_db()
                for line in content.splitlines():
                    uid_str = line.strip()
                    if not uid_str.isdigit():
                        continue
                    if uid_str not in users_db_imp:
                        users_db_imp[uid_str] = _default_user(int(uid_str))
                        all_known_users.add(uid_str)
                        imported += 1
                    else:
                        skipped += 1
                _save_users_db(users_db_imp)
            # Save all_known_users
            try:
                with open("all_users.txt", "a", encoding="utf-8") as f:
                    pass  # file already appended via register_user_local on next message
                # Rebuild all_users.txt from users_db
                with open("all_users.txt", "w", encoding="utf-8") as f:
                    for uid in all_known_users:
                        f.write(str(uid) + "\n")
            except: pass
            send_message(chat_id, render_body_text(
                f"✅ Import complete!\n\n"
                f"➕ Imported: <b>{imported}</b> new users\n"
                f"⏭ Skipped: <b>{skipped}</b> (already exist)"
            ), reply_markup=system_settings_keyboard())
            _cleanup_state(chat_id)
            return

        elif state == "wait_for_cpt_delay" and text:
            try:
                delay_secs = int(text.strip())
                if delay_secs < 1: raise ValueError
            except:
                send_message(chat_id, render_body_text("❌ Enter a valid number (e.g. 16)"), reply_markup=get_cancel_kb())
                return
            msg_id_t = temp_data.get(chat_id, {}).get("msg_id")
            try:
                # Template flow
                if _require_temp(chat_id, "tmpl", "tmpl_user", "tmpl_pass"):
                    t = temp_data[chat_id]["tmpl"]
                    _save_cpt_from_template(chat_id, t, temp_data[chat_id]["tmpl_user"],
                                            temp_data[chat_id]["tmpl_pass"], delay_secs, msg_id_t)
                # Manual p_data flow
                elif _require_temp(chat_id, "p_data"):
                    temp_data[chat_id]["p_data"]["delay_seconds"] = delay_secs
                    bot_settings["panels"].append(temp_data[chat_id]["p_data"])
                    save_db()
                    _cleanup_state(chat_id)
                    send_message(chat_id, render_body_text(
                        f"✅ Panel added! ⏱ Delay: <b>{delay_secs}s</b>"
                    ), reply_markup=admin_panel_keyboard())
                else:
                    _cleanup_state(chat_id)
                    send_message(chat_id, render_body_text("❌ Session expired."), reply_markup=main_menu(chat_id))
            except Exception as e:
                send_message(chat_id, render_body_text(f"❌ Panel add করতে সমস্যা হয়েছে:\n<code>{e}</code>"), reply_markup=admin_panel_keyboard())
            return

        elif state == "wait_for_new_service" and text:
            svc_name = text.strip().upper()
            if not svc_name:
                send_message(chat_id, render_body_text("❌ Service name cannot be empty!"), reply_markup=get_cancel_kb())
                return
            if "services" not in bot_settings:
                bot_settings["services"] = []
            msg_id_s = temp_data[chat_id].get("msg_id")
            if svc_name not in bot_settings["services"]:
                bot_settings["services"].append(svc_name)
                save_db()
                result_txt = f"✅ Service <b>{svc_name}</b> added!\nTotal: {len(bot_settings['services'])}"
            else:
                result_txt = f"⚠️ <b>{svc_name}</b> already exists!"
            _cleanup_state(chat_id)
            if msg_id_s:
                edit_message(chat_id, msg_id_s, render_body_text(result_txt), reply_markup=services_keyboard())
            else:
                send_message(chat_id, render_body_text(result_txt), reply_markup=services_keyboard())
            return

        elif state == "wait_for_service" and text:
            svc_name = text.upper().strip()
            # Auto-add to services list so it shows next time
            if "services" not in bot_settings:
                bot_settings["services"] = []
            if svc_name not in bot_settings["services"]:
                bot_settings["services"].append(svc_name)
                save_db()
            temp_data[chat_id]["service"] = svc_name

            if temp_data[chat_id].get("detected_country"):
                user_states[chat_id] = "wait_for_rate"
                send_message(chat_id, render_body_text(
                    f"✅ Service: <b>{svc_name}</b>\n"
                    f"🌍 Country: <b>{temp_data[chat_id]['detected_country']}</b> (auto-detected)\n\n"
                    f"💰 Enter the rate per OTP in BDT (e.g., 0.10):"
                ), reply_markup=get_cancel_kb())
            else:
                user_states[chat_id] = "wait_for_country"
                send_message(chat_id, render_body_text(
                    f"✅ Service: <b>{svc_name}</b>\n\n"
                    f"⚠️ Country not auto-detected. Enter country info:\n\n"
                    f"<code>880 | BD | Bangladesh | 🇧🇩 | emoji_id</code>\n\n"
                    f"(dial_code | ISO | Country Name | Flag | Premium Flag ID)"
                ), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_country" and text:
            # Parse manual country input: 880 | BD | Bangladesh | 🇧🇩 | 5291937511591925566
            parts = [p.strip() for p in text.split("|")]
            if len(parts) >= 4:
                dial_code = parts[0].replace("+", "").strip()
                iso = parts[1].strip().upper()
                country_name = parts[2].strip()
                flag_emoji = parts[3].strip()
                flag_id = parts[4].strip() if len(parts) > 4 else ""
                
                # Save to premium_flags
                if "premium_flags" not in bot_settings: bot_settings["premium_flags"] = {}
                bot_settings["premium_flags"][dial_code] = {
                    "iso": iso, "name": country_name, "dial_code": dial_code,
                    "char": flag_emoji, "flag": flag_emoji, "id": flag_id
                }
                save_db()
                
                temp_data[chat_id]["detected_country"] = country_name
                temp_data[chat_id]["detected_iso"] = iso
                user_states[chat_id] = "wait_for_rate"
                send_message(chat_id, render_body_text(
                    f"✅ Country saved: <b>{country_name}</b>\n\n"
                    f"💰 Enter the rate per OTP in BDT (e.g., 0.01):"
                ), reply_markup=get_cancel_kb())
            else:
                send_message(chat_id, render_body_text(
                    "❌ Invalid format! Please use:\n"
                    "<code>880 | BD | Bangladesh | 🇧🇩 | 5291937511591925566</code>"
                ), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_rate" and text:
            try:
                rate = round(float(text.strip()), 4)
            except:
                send_message(chat_id, render_body_text("❌ Invalid rate! Enter a number like 0.01"), reply_markup=get_cancel_kb())
                return
            
            if not _require_temp(chat_id, "service", "detected_country"):
                send_message(chat_id, render_body_text("❌ Session expired. Please start over."), reply_markup=main_menu(chat_id))
                _cleanup_state(chat_id)
                return
            if not temp_data[chat_id].get("numbers"):
                send_message(chat_id, render_body_text("❌ No numbers found in session. Please upload again."), reply_markup=main_menu(chat_id))
                _cleanup_state(chat_id)
                return

            service = temp_data[chat_id]["service"]
            country_name = temp_data[chat_id]["detected_country"]
            country_iso = temp_data[chat_id].get("detected_iso", country_name[:2].upper())
            temp_data[chat_id]["rate"] = rate

            # ── Duplicate country check ──────────────────────────────────────
            existing_match = None
            for b_id, b_data in number_batches.items():
                if b_data.get("service") == service and b_data.get("country_name", "").lower() == country_name.lower():
                    existing_match = b_id
                    break

            if existing_match:
                user_states[chat_id] = "wait_for_add_another"
                temp_data[chat_id]["existing_batch"] = existing_match
                kb = {"inline_keyboard": [
                    [{"text": "✅ Yes — Create New Batch", "callback_data": "upload_add_another_yes", "style": "success"},
                     {"text": "❌ No — Add to Existing", "callback_data": "upload_add_another_no", "style": "danger"}]
                ]}
                send_message(chat_id, render_body_text(
                    f"⚠️ <b>{country_name}</b> already exists for <b>{service}</b>!\n\n"
                    f"Add Another (new separate batch)?"
                ), reply_markup=kb)
                return
            else:
                # No duplicate — proceed directly
                _do_upload_batch(chat_id, service, country_name, country_iso, rate, new_batch=False)
                return

        elif state == "wait_for_not_earn_svc" and text:
            svc = text.strip().upper()
            if "not_earn_services" not in bot_settings: bot_settings["not_earn_services"] = []
            if svc not in bot_settings["not_earn_services"]:
                bot_settings["not_earn_services"].append(svc)
                save_db()
                send_message(chat_id, render_body_text(f"✅ <b>{svc}</b> added to Not Earn Services!"))
            else:
                send_message(chat_id, render_body_text(f"⚠️ <b>{svc}</b> already in list!"))
            del user_states[chat_id]
            if chat_id in temp_data: del temp_data[chat_id]
            return

        elif state == "wait_for_bonus_uid" and text:
            try:
                target_uid = int(text.strip())
            except:
                send_message(chat_id, render_body_text("❌ Invalid User ID!"), reply_markup=get_cancel_kb())
                return
            users_db_b = _load_users_db()
            if str(target_uid) not in users_db_b:
                send_message(chat_id, render_body_text("❌ User not found!"), reply_markup=get_cancel_kb())
                return
            temp_data[chat_id]["target_uid"] = target_uid
            user_states[chat_id] = "wait_for_bonus_rate"
            cur_bonus = users_db_b[str(target_uid)].get("bonus_rate", 0.0)
            send_message(chat_id, render_body_text(
                f"👤 User: <code>{target_uid}</code>\n"
                f"Current Bonus Rate: <b>{cur_bonus} BDT</b>\n\n"
                f"📝 Enter new bonus rate (e.g., 0.01). Enter 0 to remove bonus:"
            ), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_bonus_rate" and text:
            try:
                bonus = round(float(text.strip()), 4)
            except:
                send_message(chat_id, render_body_text("❌ Invalid rate!"), reply_markup=get_cancel_kb())
                return
            target_uid = temp_data[chat_id].get("target_uid")
            with _balance_lock:
                users_db_b = _load_users_db()
                if str(target_uid) not in users_db_b:
                    users_db_b[str(target_uid)] = _default_user(target_uid)
                users_db_b[str(target_uid)]["bonus_rate"] = bonus
                _save_users_db(users_db_b)
            if target_uid in user_cache:
                user_cache[target_uid]["bonus_rate"] = bonus
            send_message(chat_id, render_body_text(
                f"✅ Bonus rate for <code>{target_uid}</code> set to <b>{bonus} BDT</b>!\n"
                f"ℹ️ Per OTP earn: base_rate + {bonus} BDT"
            ))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_xisora_user" and text:
            if not _require_temp(chat_id, "p_name"):
                _cleanup_state(chat_id); return
            temp_data[chat_id]["xisora_user"] = text.strip()
            user_states[chat_id] = "wait_for_xisora_pass"
            send_message(chat_id, render_body_text("🔑 Enter your <b>password</b>:"), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_xisora_pass" and text:
            if not _require_temp(chat_id, "p_name", "xisora_user"):
                _cleanup_state(chat_id); return
            p_name    = temp_data[chat_id]["p_name"]
            username  = temp_data[chat_id]["xisora_user"]
            password  = text.strip()
            msg_id_x  = temp_data[chat_id].get("msg_id")
            new_panel = {
                "name": p_name, "type": "Xisora Panel", "status": "ON",
                "username": username, "password": password,
                "login_status": "⏳ Requesting captcha...", "delay_seconds": 5
            }
            bot_settings["panels"].append(new_panel)
            save_db()
            new_idx = len(bot_settings["panels"]) - 1
            _cleanup_state(chat_id)
            send_message(chat_id, render_body_text(
                f"✅ Xisora panel <b>{p_name}</b> added!\n\n"
                f"🔐 Requesting captcha from server now..."
            ))
            # Immediately request captcha
            threading.Thread(target=xisora_request_captcha, args=(new_idx,), daemon=True).start()
            return

        elif state == "wait_for_xisora_captcha" and text:
            # Admin replied with captcha answer
            panel_idx = temp_data[chat_id].get("panel_idx")
            if panel_idx is None:
                _cleanup_state(chat_id); return
            _cleanup_state(chat_id)
            ok = xisora_login_with_captcha(panel_idx, text.strip())
            p_name = bot_settings["panels"][panel_idx].get("name", "?") if panel_idx < len(bot_settings["panels"]) else "?"
            send_message(chat_id, render_body_text(
                f"{'✅ Xisora login successful!' if ok else '❌ Xisora login failed. Try again.'}\n"
                f"Panel: <b>{p_name}</b>"
            ))
            return


            svc_name = text.strip().upper()
            if not svc_name:
                send_message(chat_id, render_body_text("❌ Service name cannot be empty!"), reply_markup=get_cancel_kb())
                return
            if "services" not in bot_settings:
                bot_settings["services"] = []
            if svc_name not in bot_settings["services"]:
                bot_settings["services"].append(svc_name)
                save_db()
            msg_id_t = temp_data[chat_id].get("msg_id")
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t,
                             render_body_text(f"✅ Service <b>{svc_name}</b> added!"),
                             reply_markup=services_keyboard())
            return

        elif state == "wait_for_stats_date" and text:
            from datetime import datetime
            date_str = text.strip()
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                send_message(chat_id, render_body_text("❌ Invalid format! Use YYYY-MM-DD"), reply_markup=get_cancel_kb())
                return
            users_db_sd = _load_users_db()
            day_total = 0
            svc_counts_sd = {}
            for u in users_db_sd.values():
                day_total += sum(1 for d in u.get("otp_dates", []) if d == date_str)
            for t in recent_traffic:
                from datetime import datetime as dt2
                t_date = dt2.fromtimestamp(t.get("time", 0)).strftime("%Y-%m-%d")
                if t_date == date_str:
                    svc = t.get("service", "?")
                    svc_counts_sd[svc] = svc_counts_sd.get(svc, 0) + 1
            svc_txt_sd = ""
            for svc, cnt in sorted(svc_counts_sd.items(), key=lambda x: -x[1]):
                svc_txt_sd += f"├ {svc}: <b>{cnt}</b>\n"
            if not svc_txt_sd:
                svc_txt_sd = "└ No recent_traffic data for this date\n"
            msg_id_t = temp_data[chat_id].get("msg_id")
            _cleanup_state(chat_id)
            result_txt = (
                f"━━━━━━━━━━━━━━━\n"
                f"📅 <b>Stats for {date_str}</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📊 Total OTPs: <b>{day_total}</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🔥 By Service:\n{svc_txt_sd}"
                f"━━━━━━━━━━━━━━━"
            )
            kb = [[{"text": "🔙 Back to Stats", "callback_data": "admin_stats", "style": "primary"}]]
            if msg_id_t:
                edit_message(chat_id, msg_id_t, render_body_text(result_txt), reply_markup={"inline_keyboard": kb})
            return

        elif state == "wait_xty_ref_per_otp" and text:
            try:
                val = round(float(text.strip()), 4)
            except:
                send_message(chat_id, render_body_text("❌ Invalid amount!"), reply_markup=get_cancel_kb())
                return
            bot_settings["refer_per_otp"] = val
            save_db()
            msg_id_t = temp_data[chat_id].get("msg_id")
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t,
                             render_body_text(f"✅ Referral per-OTP bonus set to <b>{val} BDT</b>!"),
                             reply_markup=xty_control_keyboard())
            return

        elif state == "wait_xty_ref_max_otps" and text:
            try:
                val = int(text.strip())
                if val < 1: raise ValueError
            except:
                send_message(chat_id, render_body_text("❌ Invalid number! Enter a positive integer."), reply_markup=get_cancel_kb())
                return
            bot_settings["refer_max_otps"] = val
            save_db()
            msg_id_t = temp_data[chat_id].get("msg_id")
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t,
                             render_body_text(f"✅ Max referral OTPs set to <b>{val}</b>!"),
                             reply_markup=xty_control_keyboard())
            return

        elif state and state.startswith("wait_fw_btn") and text:
            # Format: wait_fw_btn1_0 or wait_fw_btn2_1
            parts = state.split("_")
            which = parts[2]   # btn1 or btn2
            idx = int(parts[3])
            if "|" not in text:
                send_message(chat_id, render_body_text("❌ Use format: <code>Label | https://link</code>"), reply_markup=get_cancel_kb())
                return
            label, url = [p.strip() for p in text.split("|", 1)]
            if idx < len(bot_settings["fw_groups"]):
                bot_settings["fw_groups"][idx][f"{which}_text"] = label
                bot_settings["fw_groups"][idx][f"{which}_url"] = url
                save_db()
            msg_id_t = temp_data[chat_id].get("msg_id")
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t,
                             render_body_text(f"✅ <b>{which.upper()}</b> updated!\n{label} → {url}"),
                             reply_markup=specific_fw_group_keyboard(idx))
            return


            code = text.strip().replace("+", "")
            if "search_countries" not in bot_settings: bot_settings["search_countries"] = []
            bot_settings["search_countries"].append(code)
            save_db()
            delete_message(chat_id, msg["message_id"])
            kb = []
            for idx, c in enumerate(bot_settings.get("search_countries", [])):
                kb.append([{"text": f"❌ Delete {c}", "callback_data": f"del_sc_{idx}", "style": "danger"}])
            kb.append([{"text": "➕ Add Country Code", "callback_data": "add_search_country", "style": "success"}])
            kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🌍 <b>Allowed Search Countries:</b>\nOnly these country codes will be allowed in Search Number."), reply_markup={"inline_keyboard": kb})
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_wm" and text:
            bot_settings["w_methods"].append(text.strip())
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("💳 <b>WITHDRAWAL METHODS</b>\n\nManage your withdrawal methods below:"), reply_markup=w_methods_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_fj" and text:
            bot_settings["fj_channels"].append(parse_chat_id(text))
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🔗 <b>FORCE JOIN SYSTEM</b>\nManage channels below:\n<i>(Note: For private links, use numeric IDs like -100...)</i>"), reply_markup=fj_settings_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_add_adm" and text:
            if text.isdigit():
                bot_settings["admins"].append(int(text))
                save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("👥 <b>ADMIN MANAGEMENT</b>\nManage your bot admins below:"), reply_markup=admin_settings_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_add_fw_id" and text:
            bot_settings["fw_groups"].append({"chat_id": text.strip(), "buttons": []})
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_add_fw_btn" and text:
            fw_idx = temp_data[chat_id]["fw_idx"]
            if "-" in text:
                parts = text.split("-", 1)
                btn_text = parts[0].strip()
                btn_url = parts[1].strip()
                
                emoji_id = None
                emoji_char = ""
                for ent in msg.get("entities", []):
                    if ent.get("type") == "custom_emoji":
                        emoji_id = ent.get("custom_emoji_id")
                        offset = ent.get("offset", 0)
                        length = ent.get("length", 0)
                        b_text = text.encode('utf-16-le')
                        emoji_char = b_text[offset*2:(offset+length)*2].decode('utf-16-le')
                        break
                
                if emoji_char:
                    btn_text = btn_text.replace(emoji_char, "").strip()
                    
                btn_data = {"text": btn_text, "url": btn_url}
                if emoji_id:
                    btn_data["icon_custom_emoji_id"] = emoji_id
                    
                bot_settings["fw_groups"][fw_idx]["buttons"].append(btn_data)
                save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(f"🛡 <b>Manage Group:</b> {bot_settings['fw_groups'][fw_idx]['chat_id']}"), reply_markup=specific_fw_group_keyboard(fw_idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return
            
        elif state == "wait_for_otp_link" and text:
            bot_settings["otp_link"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_panel_name" and text:
            p_name = text.strip()
            t_key = temp_data[chat_id].get("add_type", "api")
            msg_id = temp_data[chat_id]["msg_id"]
            delete_message(chat_id, msg["message_id"])
            
            if t_key == "logc":
                user_states[chat_id] = "wait_for_cpanel_url"
                temp_data[chat_id] = {"msg_id": msg_id, "p_data": {
                    "name": p_name, "type": "Auto Captcha Panel", "status": "ON", "records": 0, "login_status": "⏳ Pending First Login"
                }}
                edit_message(chat_id, msg_id, render_body_text("1️⃣ <b>Login URL</b>\n➡️ Panel এর Login Link দিন:"), reply_markup=get_cancel_kb())
                return
            elif t_key == "xisora":
                # Xisora: only need username + password
                user_states[chat_id] = "wait_for_xisora_user"
                temp_data[chat_id] = {"msg_id": msg_id, "p_name": p_name}
                edit_message(chat_id, msg_id, render_body_text(
                    f"🔐 <b>Xisora Panel: {p_name}</b>\n\n"
                    f"URL: <code>{XISORA_LOGIN_PAGE}</code> (fixed)\n\n"
                    f"📝 Enter your <b>username</b>:"
                ), reply_markup=get_cancel_kb())
                return
            else:
                temp_data[chat_id]["p_name"] = p_name
                user_states[chat_id] = "wait_for_p_delay_choice"
                edit_message(chat_id, msg_id, render_body_text(
                    f"⚙️ Panel: <b>{p_name}</b>\n\n"
                    f"⏱ <b>Add custom delay?</b>\n"
                    f"(Some panels require 15-16s between requests to avoid errors)"
                ), reply_markup={"inline_keyboard": [
                    [{"text": "✅ Yes — Set Delay", "callback_data": "panel_delay_yes", "style": "success"},
                     {"text": "❌ No — Default", "callback_data": "panel_delay_no", "style": "danger"}]
                ]})
                return

        elif state == "wait_for_cpt_tmpl_username" and text:
            if not _require_temp(chat_id, "tmpl"):
                _cleanup_state(chat_id); return
            temp_data[chat_id]["tmpl_user"] = text.strip()
            user_states[chat_id] = "wait_for_cpt_tmpl_password"
            send_message(chat_id, render_body_text("🔑 Enter <b>password</b>:"), reply_markup=get_cancel_kb())
            return

        elif state == "wait_for_cpt_tmpl_password" and text:
            if not _require_temp(chat_id, "tmpl", "tmpl_user"):
                _cleanup_state(chat_id); return
            t = temp_data[chat_id]["tmpl"]
            temp_data[chat_id]["tmpl_pass"] = text.strip()
            msg_id_t = temp_data[chat_id].get("msg_id")
            # If template has delay already set, skip question
            if t.get("delay_seconds", 5) != 5:
                # Save directly with template delay
                _save_cpt_from_template(chat_id, t, temp_data[chat_id]["tmpl_user"],
                                        text.strip(), t["delay_seconds"], msg_id_t)
                return
            # Ask delay
            user_states[chat_id] = "wait_for_cpt_delay_choice"
            kb = {"inline_keyboard": [
                [{"text": "✅ Yes — Set Delay", "callback_data": "cpt_delay_yes", "style": "success"},
                 {"text": "❌ No — Default 5s", "callback_data": "cpt_delay_no", "style": "danger"}]
            ]}
            if msg_id_t:
                edit_message(chat_id, msg_id_t, render_body_text(
                    f"✅ Password saved!\n\n⏱ <b>Add custom delay?</b>\n"
                    f"(Some panels need 15-16s between requests)"
                ), reply_markup=kb)
            return

        elif state == "wait_for_api_tmpl_key" and text:
            if not _require_temp(chat_id, "tmpl"):
                _cleanup_state(chat_id); return
            t = temp_data[chat_id]["tmpl"]
            api_key = text.strip()
            msg_id_t = temp_data[chat_id].get("msg_id")
            full_url = t["url_template"].replace("{key}", api_key).replace("{token}", api_key)
            new_panel = {
                "name": t["name"],
                "type": "API Panel",
                "status": "ON",
                "api_url": t["url_template"],
                "full_api_url": full_url,
                "token": api_key,
                "delay_seconds": 5,
                "records": 0
            }
            bot_settings["panels"].append(new_panel)
            save_db()
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t, render_body_text(
                    f"✅ <b>{t['name']}</b> added from template!\n"
                    f"🔑 Key: <code>{api_key[:8]}...</code>"
                ), reply_markup=admin_panel_keyboard())
            return

        elif state == "wait_for_cpt_tmpl_block" and text:
            lines_t = [l.strip() for l in text.strip().splitlines() if l.strip()]
            msg_id_t = temp_data[chat_id].get("msg_id")
            if len(lines_t) < 5:
                send_message(chat_id, render_body_text(
                    "❌ Need 5 lines:\n<code>Name\nlogin_url\ndata_url\nNumber3\nSMS5</code>"
                ), reply_markup=get_cancel_kb())
                return
            save_panel_template(*lines_t[:5])
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t,
                             render_body_text(f"✅ Template <b>{lines_t[0]}</b> saved!"),
                             reply_markup=panel_templates_keyboard())
            return

        elif state == "wait_for_api_tmpl_block" and text:
            lines_t = [l.strip() for l in text.strip().splitlines() if l.strip()]
            msg_id_t = temp_data[chat_id].get("msg_id")
            if len(lines_t) < 2:
                send_message(chat_id, render_body_text(
                    "❌ Need at least 2 lines:\n<code>Name\nhttps://api.url?key={key}</code>"
                ), reply_markup=get_cancel_kb())
                return
            save_api_template(lines_t[0], lines_t[1], lines_t[2] if len(lines_t) > 2 else "")
            _cleanup_state(chat_id)
            if msg_id_t:
                edit_message(chat_id, msg_id_t,
                             render_body_text(f"✅ Template <b>{lines_t[0]}</b> saved!"),
                             reply_markup=api_templates_keyboard())
            return


            svc_name = text.strip().upper()
            if not svc_name:
                send_message(chat_id, render_body_text("❌ Service name cannot be empty!"), reply_markup=get_cancel_kb())
                return
            if "services" not in bot_settings:
                bot_settings["services"] = []
            if svc_name not in bot_settings["services"]:
                bot_settings["services"].append(svc_name)
                save_db()
                msg_id_s = temp_data[chat_id].get("msg_id")
                _cleanup_state(chat_id)
                if msg_id_s:
                    edit_message(chat_id, msg_id_s,
                                 render_body_text(f"✅ Service <b>{svc_name}</b> added!\n\nTotal services: {len(bot_settings['services'])}"),
                                 reply_markup=services_keyboard())
            else:
                msg_id_s = temp_data[chat_id].get("msg_id")
                _cleanup_state(chat_id)
                if msg_id_s:
                    edit_message(chat_id, msg_id_s,
                                 render_body_text(f"⚠️ <b>{svc_name}</b> already exists!"),
                                 reply_markup=services_keyboard())
            return

        elif state == "wait_for_p_api" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["api_url"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>"
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_tok" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["token"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>"
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_fapi" and text:
            idx = temp_data[chat_id]["p_idx"]
            bot_settings["panels"][idx]["full_api_url"] = text.strip()
            save_db()
            delete_message(chat_id, msg["message_id"])
            p = bot_settings["panels"][idx]
            ui_text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Full API URL:</b> <code>{p.get('full_api_url', 'None')}</code>"
            edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_p_rec" and text:
            if text.isdigit():
                idx = temp_data[chat_id]["p_idx"]
                bot_settings["panels"][idx]["records"] = int(text)
                save_db()
                delete_message(chat_id, msg["message_id"])
                p = bot_settings["panels"][idx]
                
                ui_text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>"
                edit_message(chat_id, temp_data[chat_id]["msg_id"], render_body_text(ui_text), reply_markup=panel_config_keyboard(idx))
            else:
                send_message(chat_id, render_body_text("❌ Please enter a valid number! Try again."), reply_markup=get_cancel_kb())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "set_xty":
            msg_id = temp_data[chat_id]["msg_id"]
            key = temp_data[chat_id]["key"]
            try:
                if key in ["min_withdraw", "otp_reward", "refer_reward"]: bot_settings[key] = float(text)
                elif key in ["cooldown", "num_req", "num_share"]: bot_settings[key] = int(text)
                else: bot_settings[key] = text
                save_db()
                delete_message(chat_id, msg["message_id"])
                edit_message(chat_id, msg_id, render_body_text("🕹 <b>XTY CONTROL PANEL</b>"), reply_markup=xty_control_keyboard())
            except:
                delete_message(chat_id, msg["message_id"])
                edit_message(chat_id, msg_id, render_body_text("🕹 <b>XTY CONTROL PANEL</b>\n\n❌ Invalid value!"), reply_markup=xty_control_keyboard())
            del user_states[chat_id]
            del temp_data[chat_id]
            return

        elif state == "wait_for_search" and text:
            query = text.strip().replace("+", "")
            if not query.isdigit() or len(query) < 3 or len(query) > 9:
                send_message(chat_id, render_body_text("❌ Please enter a valid 3 to 9 digit number!"))
                return

            # ── Cooldown check ─────────────────────────────────────────────
            now_cd = time.time()
            last_req = user_cooldowns.get(chat_id, 0)
            cd_secs = int(bot_settings.get("cooldown", 0))
            if cd_secs > 0 and (now_cd - last_req) < cd_secs:
                remaining = int(cd_secs - (now_cd - last_req))
                send_message(chat_id, render_body_text(f"⏳ Please wait {remaining}s before requesting again!"))
                return
            # ── Set cooldown BEFORE assignment to block parallel requests ──
            user_cooldowns[chat_id] = now_cd
                
            wait_msg = send_message(chat_id, render_body_text("⌛ <i>Processing... Finding Number...</i>"))
            wait_msg_id = wait_msg.get("result", {}).get("message_id")
            
            fetched_nums = []
            search_rate = float(bot_settings.get("otp_reward", 0.1))

            with _batch_lock:
                found_indices = []
                for b_id, b_data in number_batches.items():
                    for idx, n_obj in enumerate(b_data["numbers"]):
                        if n_obj["num"].replace("+", "").startswith(query) and (chat_id not in n_obj.get("used_by", []) and chat_id not in n_obj.get("allocated_to", [])):
                            found_indices.append((b_id, idx))
                
                if not found_indices:
                    pass  # handled below
                else:
                    used_mode = bot_settings.get("num_used_mode", "classic")
                    random.shuffle(found_indices)
                    for b_id, idx in found_indices:
                        if len(fetched_nums) >= bot_settings.get("num_req", 1): break
                        n_obj = number_batches[b_id]["numbers"][idx]
                        num_str = n_obj["num"]
                        fetched_nums.append(num_str)
                        if len(fetched_nums) == 1:
                            search_rate = float(number_batches[b_id].get("rate", bot_settings.get("otp_reward", 0.1)))
                        global total_assigned_stats
                        total_assigned_stats += 1
                        if used_mode == "classic":
                            n_obj["shares"] += 1
                            n_obj["used_by"].append(chat_id)
                            if n_obj["shares"] >= bot_settings.get("num_share", 1):
                                n_obj["to_remove"] = True
                                used_numbers_list.append(num_str)
                        else:
                            n_obj.setdefault("allocated_to", [])
                            if chat_id not in n_obj["allocated_to"]:
                                n_obj["allocated_to"].append(chat_id)
                    if used_mode == "classic":
                        for b_id in number_batches:
                            number_batches[b_id]["numbers"] = [n for n in number_batches[b_id]["numbers"] if not n.get("to_remove")]
                    save_db()

            if not fetched_nums:
                if wait_msg_id: delete_message(chat_id, wait_msg_id)
                send_message(chat_id, render_body_text("❌ Number out of stock!"), reply_markup=main_menu(chat_id))
                del user_states[chat_id]
                return
                
            if wait_msg_id: edit_message(chat_id, wait_msg_id, render_body_text("✅ Number Found!"))
            kb = []
            flags_db = bot_settings.get("premium_flags", {})
            for num in fetched_nums:
                _, iso = get_flag_and_code(num)
                display_num = f"+{num}" if not num.startswith("+") else num
                
                emoji_id = "5780471598922337683" # Default Flag
                for flag_code, flag_data in flags_db.items():
                    if iso == flag_data.get("iso"):
                        if "id" in flag_data: emoji_id = flag_data["id"]
                        break
                kb.append([{"text": f"{display_num}", "icon_custom_emoji_id": emoji_id, "copy_text": {"text": display_num}, "style": "primary"}])
                
            kb.append([{"text": "Change Number", "icon_custom_emoji_id": "5465368548702446780", "callback_data": f"c_n_s_{query}", "style": "success"},
                       {"text": "OTP Group", "icon_custom_emoji_id": "5190447043545438788", "url": bot_settings["otp_link"], "style": "success"}])
            
            c_btns = bot_settings["custom_messages"].get("search_number", {}).get("buttons", [])
            for c_b in c_btns: 
                b_copy = c_b.copy()
                if "style" not in b_copy: b_copy["style"] = "primary"
                kb.append([b_copy])
            
            kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}])
            
            if wait_msg_id:
                edit_message(chat_id, wait_msg_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
                user_active_sessions[chat_id] = {"msg_id": wait_msg_id, "nums": fetched_nums, "rate": search_rate, "_ts": time.time()}
            else:
                msg_res = send_message(chat_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
                if msg_res and "result" in msg_res:
                    user_active_sessions[chat_id] = {"msg_id": msg_res["result"]["message_id"], "nums": fetched_nums, "rate": search_rate, "_ts": time.time()}
            return
            
        elif state == "wait_for_withdraw_amount" and text:
            if not _require_temp(chat_id, "method"):
                send_message(chat_id, render_body_text("❌ Session expired. Please start over."), reply_markup=main_menu(chat_id))
                _cleanup_state(chat_id)
                return
            msg_id_to_edit = temp_data[chat_id].get("msg_id")
            try:
                amount = float(text.strip())
                # Always read fresh balance from disk
                fresh_bal = float(get_user(chat_id).get("balance", 0.0))
                min_w = float(bot_settings.get('min_withdraw', 10))

                if amount < min_w:
                    if msg_id_to_edit: edit_message(chat_id, msg_id_to_edit, render_body_text(f"❌ Minimum withdrawal is {min_w} BDT!\n💰 Balance: {fresh_bal:.4f} BDT\n\n📝 Enter again:"), reply_markup=get_cancel_kb())
                    return
                if amount > fresh_bal:
                    if msg_id_to_edit: edit_message(chat_id, msg_id_to_edit, render_body_text(f"❌ Insufficient balance!\n💰 Balance: {fresh_bal:.4f} BDT\n\n📝 Enter again:"), reply_markup=get_cancel_kb())
                    return

                temp_data[chat_id]["amount"] = amount
                user_states[chat_id] = "wait_for_withdraw_number"
                if msg_id_to_edit:
                    edit_message(chat_id, msg_id_to_edit, render_body_text(
                        f"✅ Amount: <b>{amount} BDT</b>\n\n"
                        f"📱 Now send your <b>{temp_data[chat_id]['method']}</b> account number:"
                    ), reply_markup=get_cancel_kb())
            except ValueError:
                if msg_id_to_edit: edit_message(chat_id, msg_id_to_edit, render_body_text("❌ Invalid amount! Enter a number like 50"), reply_markup=get_cancel_kb())
            return
            
        elif state == "wait_for_2fa_key" and text:
            msg_id_to_edit = temp_data.get(chat_id, {}).get("msg_id")
            delete_message(chat_id, msg.get("message_id")) # ইউজারের মেসেজ ডিলিট

            if not msg_id_to_edit:
                send_message(chat_id, render_body_text("❌ Error: Message not found. Try again."))
                del user_states[chat_id]
                return

            try:
                secret = text.strip().replace(" ", "")
                totp = pyotp.TOTP(secret)
                code = totp.now()
                remaining_time = 30 - (int(time.time()) % 30)
                
                success_txt = (
                    f"━━━━━━━━━━━━━━━\n"
                    f"《 🔐 <b>2FA CODE</b> 》\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🔐 <b>CODE:</b> <code>{code}</code>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🕓 <b>EXPIRES IN:</b> {remaining_time}s\n"
                    f"━━━━━━━━━━━━━━━"
                )
                kb = [[{"text": f"Click to copy {code}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": code}, "style": "success"}],
                      [{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"ref_2fa_{secret}", "style": "primary"},
                       {"text": "New Code", "icon_custom_emoji_id": "5352552689983067014", "callback_data": "gen_2fa", "style": "danger"}],
                      [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}]]
                
                edit_message(chat_id, msg_id_to_edit, render_body_text(success_txt), reply_markup={"inline_keyboard": kb})
                del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
            except Exception:
                error_txt = "━━━━━━━━━━━━━━━\n《 🔑 <b>ENTER 2FA KEY</b> 》\n━━━━━━━━━━━━━━━\n📝 <b>SEND YOUR 2FA SECRET KEY</b>\n━━━━━━━━━━━━━━━\n❌ <b>Invalid Secret Key! Try again.</b>\n━━━━━━━━━━━━━━━"
                cancel_kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_2fa", "style": "danger"}]]}
                edit_message(chat_id, msg_id_to_edit, render_body_text(error_txt), reply_markup=cancel_kb)
            return

        elif state == "wait_for_withdraw_number":
            if not _require_temp(chat_id, "method", "amount"):
                send_message(chat_id, render_body_text("❌ Session expired. Please start over."), reply_markup=main_menu(chat_id))
                _cleanup_state(chat_id)
                return
            msg_id_to_edit = temp_data[chat_id].get("msg_id")
            method = temp_data[chat_id]["method"]
            amount = temp_data[chat_id]["amount"]
            number = text.strip()

            first_name = msg.get("from", {}).get("first_name", "User")
            last_name = msg.get("from", {}).get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()

            temp_data[chat_id]["number"] = number
            temp_data[chat_id]["full_name"] = full_name
            user_states[chat_id] = "wait_for_withdraw_confirm"

            confirm_txt = (
                f"━━━━━━━━━━━━━━━\n"
                f"💸 <b>Confirm Withdrawal</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"💰 Amount: <b>{amount} BDT</b>\n"
                f"🏦 Method: <b>{method}</b>\n"
                f"📱 Number: <code>{number}</code>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"<i>Please confirm your withdrawal request.</i>"
            )
            req_preview_kb = {"inline_keyboard": [
                [{"text": "✅ Confirm", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "confirm_withdraw", "style": "success"},
                 {"text": "❌ Cancel", "icon_custom_emoji_id": "5420130255174145507", "callback_data": "cancel_withdraw", "style": "danger"}]
            ]}
            if msg_id_to_edit:
                edit_message(chat_id, msg_id_to_edit, render_body_text(confirm_txt), reply_markup=req_preview_kb)
            else:
                send_message(chat_id, render_body_text(confirm_txt), reply_markup=req_preview_kb)
            return

    # --- Regular Commands ---
    if text.startswith("/start"):
        get_user(chat_id)
        
        # referred_by শুধু সেট করা হয় (reward পরে দেওয়া হবে 10 OTP রিসিভের পর)
        parts = text.split()
        if len(parts) > 1:
            try:
                inviter = int(parts[1])
                if inviter != chat_id:
                    with _balance_lock:
                        users_db_ref = _load_users_db()
                        uid_str = str(chat_id)
                        if uid_str not in users_db_ref:
                            users_db_ref[uid_str] = _default_user(chat_id)
                        if not users_db_ref[uid_str].get("referred_by"):
                            users_db_ref[uid_str]["referred_by"] = inviter
                            users_db_ref[uid_str]["ref_paid"] = False
                            _save_users_db(users_db_ref)
            except: pass
        
        c_msg = bot_settings["custom_messages"].get("start", {})
        txt = render_body_text(c_msg.get("text", f"{PEM['hi']} Welcome!"))
        kb = []
        for b in c_msg.get("buttons", []):
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        
        if kb:
            send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})
            send_message(chat_id, render_body_text(f"{PEM['gear']} Navigation Menu:"), reply_markup=main_menu(chat_id))
        else:
            send_message(chat_id, txt, reply_markup=main_menu(chat_id))
            
    elif text == "TRAFFIC" or text == "Live Traffic":
        txt, markup = build_traffic_ui()
        send_message(chat_id, txt, reply_markup=markup)

    elif text == "My Profile" or text == "Profile":
        u_data = get_user(chat_id)
        bal = u_data.get('balance', 0.0)
        total_otps = u_data.get('total_otps', 0)
        total_refs = u_data.get('total_refers', 0)
        ref_link = f"https://t.me/{BOT_USERNAME}?start={chat_id}"

        # Stats calculation
        from datetime import datetime, timedelta
        otp_dates = u_data.get('otp_dates', [])
        today_str = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        today_count = sum(1 for d in otp_dates if d == today_str)
        week_count = sum(1 for d in otp_dates if d >= week_ago)
        month_count = sum(1 for d in otp_dates if d >= month_ago)

        # Referral progress status
        ref_per_otp = float(bot_settings.get("refer_per_otp", 0.0))
        ref_max = int(bot_settings.get("refer_max_otps", 50))
        ref_status_line = ""
        if u_data.get("referred_by"):
            ref_counted = u_data.get("ref_otps_counted", 0)
            if not u_data.get("ref_paid"):
                ref_status_line = f"\n📊 <b>Ref Progress:</b> {ref_counted}/{ref_max} OTPs (+{ref_per_otp} BDT each)"
            else:
                ref_status_line = f"\n✅ <b>Ref Bonus:</b> Completed ({ref_max}/{ref_max} OTPs)"

        prof_txt = (
            f"━━━━━━━━━━━━━━━\n"
            f"{PEM.get('user','👤')} <b>MY PROFILE</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{chat_id}</code>\n"
            f"💰 <b>Balance:</b> {bal:.4f} BDT\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 <b>My Statistics</b>\n"
            f"├ Today: {today_count}\n"
            f"├ Last 7 Days: {week_count}\n"
            f"├ Last 30 Days: {month_count}\n"
            f"└ Lifetime: {total_otps}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🤝 <b>Referrals:</b> {total_refs}{ref_status_line}\n"
            f"━━━━━━━━━━━━━━━"
        )
        kb = [
            [{"text": "💸 Withdrawal", "icon_custom_emoji_id": "5352585194295564660", "callback_data": "my_withdrawal", "style": "danger"}],
            [{"text": "🔗 Refer Link", "icon_custom_emoji_id": "5420396762189831222", "copy_text": {"text": ref_link}, "style": "success"}],
            [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "primary"}]
        ]
        send_message(chat_id, render_body_text(prof_txt), reply_markup={"inline_keyboard": kb})

    elif text == "Admin Panel" and is_admin(chat_id):
        send_message(chat_id, get_admin_text(), reply_markup=admin_panel_keyboard())

    elif text == "Get Number" or text == "GET NUMBER":
        local_srvs = set([b["service"] for b in number_batches.values() if b["numbers"]])
        all_services = local_srvs

        if not all_services:
            send_message(chat_id, render_body_text(f"{PEM['no']} No numbers available!"))
        else:
            c_msg = bot_settings["custom_messages"].get("get_number", {})
            txt = render_body_text(c_msg.get("text", f"{PEM['pin']} Select Service"))

            apps_db = bot_settings.get("premium_apps", {})
            kb = []
            for s in all_services:
                emoji_id = "5352694861990501856"
                for app_key, app_data in apps_db.items():
                    if s.upper() == app_key or s.upper() in app_key or app_key in s.upper():
                        if "id" in app_data:
                            emoji_id = app_data["id"]
                            break
                kb.append([{"text": f"{s}", "icon_custom_emoji_id": emoji_id, "callback_data": f"g_s_{s}", "style": "primary"}])

            for b in c_msg.get("buttons", []):
                b_copy = b.copy()
                if "style" not in b_copy: b_copy["style"] = "primary"
                kb.append([b_copy])
            kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}])

            send_message(chat_id, txt, reply_markup={"inline_keyboard": kb})

    elif text == "2FA Online" or text == "2FA ONLINE" or text == "🔐 2FA ONLINE" or text == "2F Auth":
        txt = "━━━━━━━━━━━━━━━\n《 🔐 <b>2FA ONLINE</b> 》\n━━━━━━━━━━━━━━━\n<i>Generate your 2FA security code instantly using your secret key.</i>\n━━━━━━━━━━━━━━━"
        kb = [[{"text": "Generate 2fa code", "icon_custom_emoji_id": "5353022963132174959", "callback_data": "gen_2fa", "style": "success"}],
              [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}]]
        send_message(chat_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif text == "Support" or text == "SUPPORT":
        c_msg = bot_settings["custom_messages"].get("support", {})
        txt = render_body_text(c_msg.get("text", f"{PEM['msg']} Support"))
        if not txt.strip(): txt = render_body_text(f"{PEM['msg']} Support")
        kb = []
        for b in c_msg.get("buttons", []):
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])

        sup_link = bot_settings.get("support_link", "")
        if sup_link:
            kb.insert(0, [{"text": "Contact Support", "icon_custom_emoji_id": "5337302974806922068", "url": sup_link, "style": "success"}])

        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}])
        send_message(chat_id, txt, reply_markup={"inline_keyboard": kb} if kb else None)

def expire_previous_number(chat_id):
    if chat_id in user_active_sessions:
        prev_data = user_active_sessions[chat_id]
        prev_msg_id = prev_data["msg_id"]
        nums = prev_data["nums"]
        
        save_db()
        
        # আগের মেসেজ ইডিট করে Expired বাটন বসানো
        kb = [[{"text": "Number Expired", "icon_custom_emoji_id": "5336997731481193790", "callback_data": "ignore", "style": "danger"}]]
        try:
            edit_message(chat_id, prev_msg_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
        except:
            pass
        del user_active_sessions[chat_id]

# ==========================================
# Callback Query Handler
# ==========================================
def handle_callback(call):
    global total_assigned_stats
    chat_id = call["message"]["chat"]["id"]
    chat_type = call["message"]["chat"].get("type", "private")
    data = call.get("data", "")

    # 🌟 Button Loading Fix: বাটন চাপার সাথে সাথেই টেলিগ্রামকে Response দিয়ে দেওয়া, যাতে বাটন আটকে না থাকে!
    if not data.startswith("test_p_conn_") and not data.startswith("c_n_") and not data.startswith("g_c_"):
        try: threading.Thread(target=answer_callback, args=(call["id"],)).start()
        except: pass

    if chat_type != "private" and not (data.startswith("wapp_") or data.startswith("wrej_")):
        return

    msg_id = call["message"]["message_id"]

    if chat_type == "private":
        if is_user_banned(chat_id):
            answer_callback(call["id"], "🚫 You are banned from using this bot!", show_alert=True)
            return

        if not check_force_join(chat_id) and data != "check_fj":
            send_force_join_msg(chat_id)
            return

    if data == "check_fj":
        if check_force_join(chat_id):
            delete_message(chat_id, msg_id)
            send_message(chat_id, render_body_text(f"{PEM['ok']} Thanks for joining! You can now use the bot."), reply_markup=main_menu(chat_id))
            # referred_by ইতিমধ্যে /start এ সেট হয়েছে — reward 10 OTP পর দেওয়া হবে
        else:
            answer_callback(call["id"], "❌ You haven't joined all channels yet!", show_alert=True)
        return

    if data == "close_msg":
        delete_message(chat_id, msg_id)
        
    elif data == "cancel_state":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        delete_message(chat_id, msg_id)

    elif data == "cancel_2fa":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        txt = "━━━━━━━━━━━━━━━\n《 🔐 <b>2FA ONLINE</b> 》\n━━━━━━━━━━━━━━━\n<i>Generate your 2FA security code instantly using your secret key.</i>\n━━━━━━━━━━━━━━━"
        kb = [[{"text": "Generate 2fa code", "icon_custom_emoji_id": "5353022963132174959", "callback_data": "gen_2fa", "style": "success"}],
              [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}]]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    elif data == "gen_2fa":
        user_states[chat_id] = "wait_for_2fa_key"
        temp_data[chat_id] = {"msg_id": msg_id}
        txt = "━━━━━━━━━━━━━━━\n《 🔑 <b>ENTER 2FA KEY</b> 》\n━━━━━━━━━━━━━━━\n📝 <b>SEND YOUR 2FA SECRET KEY</b>\n━━━━━━━━━━━━━━━"
        kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_2fa", "style": "danger"}]]}
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup=kb)
        answer_callback(call["id"])

    elif data.startswith("ref_2fa_"):
        secret = data.replace("ref_2fa_", "")
        try:
            totp = pyotp.TOTP(secret)
            code = totp.now()
            remaining_time = 30 - (int(time.time()) % 30)
            
            success_txt = (
                f"━━━━━━━━━━━━━━━\n"
                f"《 🔐 <b>2FA CODE</b> 》\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🔐 <b>CODE:</b> <code>{code}</code>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🕓 <b>EXPIRES IN:</b> {remaining_time}s\n"
                f"━━━━━━━━━━━━━━━"
            )
            kb = [[{"text": f"Click to copy {code}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": code}, "style": "success"}],
                  [{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": f"ref_2fa_{secret}", "style": "primary"},
                   {"text": "New Code", "icon_custom_emoji_id": "5352552689983067014", "callback_data": "gen_2fa", "style": "danger"}],
                  [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}]]
            
            edit_message(chat_id, msg_id, render_body_text(success_txt), reply_markup={"inline_keyboard": kb})
        except:
            answer_callback(call["id"], "❌ Error refreshing code!", show_alert=True)

    elif data == "cancel_xty_edit":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        edit_message(chat_id, msg_id, render_body_text("🕹 <b>XTY CONTROL PANEL</b>"), reply_markup=xty_control_keyboard())
        
    elif data == "dummy_alert":
        answer_callback(call["id"], "This feature will be added later!", show_alert=True)
        
    elif data == "refresh_traffic":
        txt, markup = build_traffic_ui()
        edit_message(chat_id, msg_id, txt, reply_markup=markup)
        answer_callback(call["id"], "✅ Traffic Refreshed!", show_alert=False)

    elif data.startswith("exp_rng_"):
        srv_query = data.replace("exp_rng_", "")
        
        country_stats = {}
        current_time = time.time()
        for t in recent_traffic:
            if current_time - t.get("time", 0) <= 3600:
                if t.get("service", "").startswith(srv_query):
                    iso = t.get("iso", "XX")
                    flag = t.get("flag", "🌍")
                    if iso not in country_stats:
                        country_stats[iso] = {"count": 0, "flag": flag}
                    country_stats[iso]["count"] += 1
        
        if not country_stats:
            answer_callback(call["id"], "❌ No recent traffic found for this service!", show_alert=True)
            return
            
        kb = []
        for iso, c_data in sorted(country_stats.items(), key=lambda x: x[1]["count"], reverse=True):
            count = c_data["count"]
            c_name = iso
            emoji_id = "5780471598922337683"
            for code, fdata in bot_settings.get("premium_flags", {}).items():
                if fdata.get("iso") == iso:
                    c_name = fdata.get("name", iso)
                    if "id" in fdata: emoji_id = fdata["id"]
                    break
            
            btn_text = f"{c_name} ({iso}) - {count} OTP"
            kb.append([{"text": btn_text, "icon_custom_emoji_id": emoji_id, "callback_data": f"exp_c_{srv_query}_{iso}", "style": "primary"}])
            
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "refresh_traffic", "style": "danger"}])
        
        app_full_name, prem_app_html = get_service_info_html(srv_query)
        edit_message(chat_id, msg_id, render_body_text(f"📊 <b>Explore Service: {prem_app_html} {app_full_name}</b>\n\nSelect a country to view available ranges:"), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    elif data.startswith("exp_c_"):
        parts = data.split("_")
        srv_query = parts[2]
        iso_query = parts[3]
        
        nums = []
        current_time = time.time()
        for t in recent_traffic:
            if current_time - t.get("time", 0) <= 3600:
                if t.get("service", "").startswith(srv_query) and t.get("iso") == iso_query:
                    num = t.get("number", "").replace("+", "").strip()
                    if num: nums.append(num)
        
        if not nums:
            answer_callback(call["id"], "❌ No recent numbers found for this country!", show_alert=True)
            return
            
        known_ranges = set()
        sorted_known = sorted(list(known_ranges), key=len, reverse=True)
        
        
        r_counts = Counter()
        for num in nums:
            matched = False
            for r in sorted_known:
                if num.startswith(r):
                    r_counts[r] += 1
                    matched = True
                    break
            if not matched:
                if len(num) >= 7:
                    r_counts[num[:7]] += 1
                else:
                    r_counts[num] += 1
                    
        r_list = r_counts.most_common(12)
        
        kb = []
        for r, count in r_list:
            # এক লাইনে একটা করে বাটন
            kb.append([{"text": f"{r} ({count})", "icon_custom_emoji_id": "5352862640592949843", "copy_text": {"text": r}, "style": "primary"}])
            
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"exp_rng_{srv_query}", "style": "danger"}])
        
        app_full_name, prem_app_html = get_service_info_html(srv_query)
        prem_flag_html = get_flag_info_html(iso_query)
        
        edit_message(chat_id, msg_id, render_body_text(f"📊 <b>Ranges for {prem_app_html} {app_full_name} - {prem_flag_html} {iso_query}</b>\n\nClick on any range to copy it."), reply_markup={"inline_keyboard": kb})
        answer_callback(call["id"])

    # --- User Management Flows Integration ---
    elif data == "user_management":
        edit_message(chat_id, msg_id, get_user_management_text(), reply_markup=user_management_keyboard())

    elif data == "um_manage_balance":
        user_states[chat_id] = "wait_for_um_bal_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID to Manage Balance:"), reply_markup=get_cancel_kb())
        
    elif data == "um_ban_unban":
        user_states[chat_id] = "wait_for_um_ban_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID to Ban or Unban:"), reply_markup=get_cancel_kb())

    elif data == "um_user_profile":
        user_states[chat_id] = "wait_for_um_prof_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID to View Profile:"), reply_markup=get_cancel_kb())

    # --- Menu Design Integration ---
    elif data == "menu_design_list":
        edit_message(chat_id, msg_id, render_body_text(f"🎨 <b>Menu Design Editor</b>\n\nSelect a menu block to edit its Body Text and Inline Buttons. You can use Premium Emojis too!"), reply_markup=menu_design_list_keyboard())

    elif data == "md_reset_defaults":
        bot_settings["custom_messages"] = DEFAULT_CUSTOM_MESSAGES.copy()
        save_db()
        answer_callback(call["id"], "✅ Resetted to Premium Defaults!", show_alert=True)

    elif data.startswith("md_edit_"):
        answer_callback(call["id"])
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        key = data.replace("md_edit_", "")
        cm_text = render_body_text(bot_settings["custom_messages"].get(key, {}).get("text", "..."))
        try:
            edit_message(chat_id, msg_id, render_body_text(f"🎨 <b>Editing: {key.upper()}</b>\n\nPreview of current Text:\n{cm_text}"), reply_markup=menu_edit_options_keyboard(key))
        except: pass

    elif data.startswith("md_text_"):
        key = data.replace("md_text_", "")
        user_states[chat_id] = "wait_for_menu_text"
        temp_data[chat_id] = {"msg_id": msg_id, "menu_key": key}
        edit_message(chat_id, msg_id, render_body_text(f"📝 <b>Edit Body: {key.upper()}</b>\n\nSend the new text. You can use Premium Emojis directly here.\n(Use standard HTML like <b>bold</b>, <i>italic</i> for formatting)"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_edit_{key}", "style": "danger"}]]})

    elif data.startswith("md_btns_"):
        answer_callback(call["id"]) 
        if chat_id in user_states: del user_states[chat_id] 
        if chat_id in temp_data: del temp_data[chat_id]
        key = data.replace("md_btns_", "")
        try:
            edit_message(chat_id, msg_id, render_body_text(f"⚙️ <b>Edit Inline Buttons: {key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(key))
        except: pass

    elif data.startswith("md_addbtn_"):
        key = data.replace("md_addbtn_", "")
        user_states[chat_id] = "wait_for_menu_btn"
        temp_data[chat_id] = {"msg_id": msg_id, "menu_key": key}
        edit_message(chat_id, msg_id, render_body_text(f"➕ <b>Add Button: {key.upper()}</b>\n\nSend custom button in this format:\n<code>Button Text - https://link.com</code>\n\n<i>(Only normal Emojis supported here!)</i>"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"md_btns_{key}", "style": "danger"}]]})

    elif data.startswith("md_delbtn_"):
        parts = data.split("_")
        key = parts[2]
        b_idx = int(parts[3])
        if b_idx < len(bot_settings["custom_messages"][key]["buttons"]):
            del bot_settings["custom_messages"][key]["buttons"][b_idx]
            save_db()
            answer_callback(call["id"], "✅ Button Deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text(f"⚙️ <b>Edit Inline Buttons: {key.upper()}</b>"), reply_markup=menu_buttons_list_keyboard(key))

    elif data == "my_withdrawal":
        if not bot_settings.get("withdraw_on", True):
            answer_callback(call["id"], "❌ Withdrawal is currently disabled!", show_alert=True)
            return
        u_data = get_user(chat_id)
        bal = u_data.get('balance', 0.0)
        min_w = bot_settings.get('min_withdraw', 10)
        txt = (
            f"💸 <b>Withdrawal</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Balance: <b>{bal:.4f} BDT</b>\n"
            f"📉 Minimum: <b>{min_w} BDT</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<i>Select your payment method:</i>"
        )
        kb = []
        for m in bot_settings.get("w_methods", []):
            kb.append([{"text": m.strip(), "icon_custom_emoji_id": "5190899075968441286", "callback_data": f"sel_wm_{m.strip()}", "style": "primary"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}])
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("sel_wm_"):
        method = data.replace("sel_wm_", "")
        bal = get_user(chat_id).get('balance', 0.0)
        min_w = bot_settings.get('min_withdraw', 10)

        if bal < min_w:
            answer_callback(call["id"], f"❌ Insufficient balance! Minimum {min_w} BDT required.", show_alert=True)
            return

        temp_data[chat_id] = {"method": method, "balance": bal, "msg_id": msg_id}
        user_states[chat_id] = "wait_for_withdraw_amount"
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['ok']} Method: <b>{method}</b>\n💰 Balance: <b>{bal:.4f} BDT</b>\n\n📝 Enter the amount (Min: {min_w} BDT):"), reply_markup=get_cancel_kb())
        answer_callback(call["id"])


    elif data == "test_message_flow":
        user_states[chat_id] = "wait_for_test_service"
        temp_data[chat_id] = {}
        edit_message(chat_id, msg_id, render_body_text("🧪 <b>Test Mode</b>\n\n📝 Send the Service Name (e.g., IG):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]]})

    elif data == "manage_emojis":
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['star']} <b>Premium Emoji Management</b>\n\nUpload your TXT files or manually add them below:"), reply_markup=emoji_settings_keyboard())

    elif data == "up_flags_txt":
        user_states[chat_id] = "wait_for_flag_txt"
        edit_message(chat_id, msg_id, render_body_text("📂 Please upload the <b>Flag Emojis</b> <code>.txt</code> file."), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_emojis", "style": "danger"}]]})

    elif data == "up_apps_txt":
        user_states[chat_id] = "wait_for_app_txt"
        edit_message(chat_id, msg_id, render_body_text("📂 Please upload the <b>Service Apps</b> <code>.txt</code> file."), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_emojis", "style": "danger"}]]})

    elif data == "add_single_emoji":
        user_states[chat_id] = "wait_for_emoji_extract"
        edit_message(chat_id, msg_id, render_body_text("📝 যেকোনো একটি Premium Emoji সেন্ড করুন (যেমন: 🇧🇩 বা 🚫):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_emojis", "style": "danger"}]]})

    elif data == "dl_flags_txt":
        content = generate_emoji_txt("flags")
        if content:
            send_document(chat_id, "Flag_Emojis.txt", content)
            answer_callback(call["id"], "✅ Downloaded!")
        else:
            answer_callback(call["id"], "❌ No Flag Emojis found!", show_alert=True)

    elif data == "dl_apps_txt":
        content = generate_emoji_txt("apps")
        if content:
            send_document(chat_id, "Service_Apps.txt", content)
            answer_callback(call["id"], "✅ Downloaded!")
        else:
            answer_callback(call["id"], "❌ No App Emojis found!", show_alert=True)

    elif data == "del_all_flags":
        bot_settings["premium_flags"] = {}
        save_db()
        answer_callback(call["id"], "✅ All Premium Flags Deleted Successfully!", show_alert=True)

    elif data == "broadcast_msg":
        user_states[chat_id] = "wait_for_broadcast"
        edit_message(chat_id, msg_id, render_body_text("📢 <b>Broadcast Mode</b>\n\nSend the message you want to broadcast (Text, Photo, Video, File etc)."), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]})

    elif data == "upload_num":
        user_states[chat_id] = "wait_for_txt"
        edit_message(chat_id, msg_id, render_body_text("📂 Please upload the numbers in a <b>.txt</b> file."), reply_markup={"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]})

    elif data == "delete_files":
        kb = []
        for b_id, b_data in number_batches.items():
            kb.append([{"text": f"{b_data['filename']} ({len(b_data['numbers'])})", "icon_custom_emoji_id": "5422557736330106570", "callback_data": f"del_b_{b_id}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "primary"}])
        txt = "🗑 Select a file to delete:" if len(kb) > 1 else f"{PEM['no']} No files found."
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_b_"):
        b_id = data.split("del_b_")[1]
        if b_id in number_batches:
            del number_batches[b_id]
            save_db()
            answer_callback(call["id"], "✅ File deleted!", show_alert=True)
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": "delete_files", "id": call["id"]})

    elif data == "show_used":
        kb = {"inline_keyboard": [[{"text": "Download TXT", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_used", "style": "primary"}], [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]}
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['ok']} <b>Total Used Numbers:</b> {len(used_numbers_list)}"), reply_markup=kb)

    elif data == "show_unused":
        unused_count = sum(len(b["numbers"]) for b in number_batches.values())
        kb = {"inline_keyboard": [[{"text": "Download TXT", "icon_custom_emoji_id": "5257969839313526622", "callback_data": "dl_unused", "style": "primary"}], [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]]}
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['rocket']} <b>Total Unused Numbers:</b> {unused_count}"), reply_markup=kb)

    elif data == "dl_used":
        if not used_numbers_list:
            answer_callback(call["id"], "❌ No used numbers found!", show_alert=True)
            return
        content = "\n".join(used_numbers_list).encode('utf-8')
        send_document(chat_id, "used_numbers.txt", content)
        answer_callback(call["id"])

    elif data == "dl_unused":
        unused_list = [n["num"] for b in number_batches.values() for n in b["numbers"]]
        if not unused_list:
            answer_callback(call["id"], "❌ No unused numbers found!", show_alert=True)
            return
        content = "\n".join(unused_list).encode('utf-8')
        send_document(chat_id, "unused_numbers.txt", content)
        answer_callback(call["id"])

    elif data == "lb_main":
        txt = f"━━━━━━━━━━━━━━━\n《 {PEM['admin']} <b>LEADER BOARD MENU</b> 》\n━━━━━━━━━━━━━━━\n<i>Select a category to view the top performers or history.</i>\n━━━━━━━━━━━━━━━"
        kb = [
            [{"text": "Top Earners (Balance)", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "lb_top_earn", "style": "primary"}],
            [{"text": "Top OTP Receivers", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "lb_top_otps", "style": "primary"}],
            [{"text": "Withdrawal History", "icon_custom_emoji_id": "5348469219761626211", "callback_data": "lb_w_history", "style": "success"}],
            [{"text": "Back to Admin", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "back_to_admin", "style": "danger"}]
        ]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data.startswith("lb_"):
        sub = data.replace("lb_", "")
        edit_message(chat_id, msg_id, render_body_text("⌛ <i>Fetching Data...</i>"))
        
        num_map = {"1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣", "0": "0️⃣"}
        def get_p_num(n): return "".join([num_map.get(c, c) for c in str(n)])
        
        try:
            users_db = _load_users_db()
            users_list = list(users_db.values())
            
            if sub == "top_earn":
                title, icon = "TOP 10 EARNERS (BALANCE)", PEM.get('money', '💸')
                sorted_users = sorted(users_list, key=lambda x: x.get("balance", 0), reverse=True)[:10]
                res_txt = ""
                for i, d in enumerate(sorted_users):
                    if d.get("balance", 0) > 0:
                        p = "└" if i == len(sorted_users)-1 else "├"
                        uid = d['user_id']
                        bal = d.get('balance', 0)
                        res_txt += f"{p} {get_p_num(i+1)} <a href='tg://user?id={uid}'>{uid}</a> ➔ <b>{bal:.2f} BDT</b>\n"
                if not res_txt: res_txt = "└ <i>No data found.</i>\n"

            elif sub == "top_otps":
                title, icon = "TOP 10 OTP RECEIVERS", PEM.get('msg', '📩')
                sorted_users = sorted(users_list, key=lambda x: x.get("total_otps", 0), reverse=True)[:10]
                res_txt = ""
                for i, d in enumerate(sorted_users):
                    if d.get("total_otps", 0) > 0:
                        p = "└" if i == len(sorted_users)-1 else "├"
                        uid = d['user_id']
                        otps = d.get('total_otps', 0)
                        res_txt += f"{p} {get_p_num(i+1)} <a href='tg://user?id={uid}'>{uid}</a> ➔ <b>{otps}</b>\n"
                if not res_txt: res_txt = "└ <i>No data found.</i>\n"

            elif sub == "w_history":
                title, icon = "LAST 10 WITHDRAWALS", PEM.get('money', '💸')
                w_list = []
                if os.path.exists("withdrawals_log.json"):
                    try:
                        with open("withdrawals_log.json", "r") as wf:
                            w_list = json.load(wf)
                    except: pass
                res_txt = ""
                for i, d in enumerate(w_list[-10:]):
                    s = str(d.get('status','Pending')).lower()
                    stat_icon = PEM.get('ok','✅') if s in ["approved","success"] else PEM.get('no','❌') if s=="rejected" else "⏳"
                    uid = d.get('user_id','User')
                    res_txt += f"├ {get_p_num(i+1)} <a href='tg://user?id={uid}'>{uid}</a> ➔ <b>{d.get('amount',0)} BDT</b> {stat_icon}\n"
                if not res_txt: res_txt = "└ <i>No history found.</i>\n"
            else:
                res_txt = "└ <i>Unknown section.</i>\n"
                title, icon = "LEADER BOARD", "📊"

            final_msg = f"━━━━━━━━━━━━━━━\n{icon} <b>{title}</b>\n━━━━━━━━━━━━━━━\n{res_txt}━━━━━━━━━━━━━━━"
            kb = [[{"text": "Refresh", "icon_custom_emoji_id": "5420155432272438703", "callback_data": data, "style": "success"}, {"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "lb_main", "style": "danger"}]]
            edit_message(chat_id, msg_id, render_body_text(final_msg), reply_markup={"inline_keyboard": kb})

        except Exception as e:
            edit_message(chat_id, msg_id, render_body_text(f"❌ Error: {e}"), reply_markup={"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "lb_main", "style": "danger"}]]})




    elif data == "not_earn_service":
        nes_list = bot_settings.get("not_earn_services", [])
        txt = "━━━━━━━━━━━━━━━\n🚫 <b>Not Earn Services</b>\n━━━━━━━━━━━━━━━\n<i>OTPs from these services will earn 0 BDT.</i>\n\n"
        if nes_list:
            for i, s in enumerate(nes_list):
                txt += f"{i+1}. <code>{s}</code>\n"
        else:
            txt += "<i>No services blocked yet.</i>\n"
        txt += "━━━━━━━━━━━━━━━"
        kb = [
            [{"text": "➕ Add Service", "icon_custom_emoji_id": "5420145051336485498", "callback_data": "add_not_earn_svc", "style": "success"}],
            [{"text": "🗑 Remove Service", "icon_custom_emoji_id": "5422557736330106570", "callback_data": "rem_not_earn_svc", "style": "danger"}],
            [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
        ]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data == "add_not_earn_svc":
        user_states[chat_id] = "wait_for_not_earn_svc"
        edit_message(chat_id, msg_id, render_body_text("📝 Enter the service name to block (e.g., TELEGRAM):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "not_earn_service", "style": "danger"}]]})

    elif data == "rem_not_earn_svc":
        nes_list = bot_settings.get("not_earn_services", [])
        if not nes_list:
            answer_callback(call["id"], "No services to remove!", show_alert=True)
            return
        kb = []
        for i, s in enumerate(nes_list):
            kb.append([{"text": f"❌ {s}", "callback_data": f"del_nes_{i}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "not_earn_service", "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text("Select a service to remove:"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("del_nes_"):
        idx = int(data.replace("del_nes_", ""))
        nes_list = bot_settings.get("not_earn_services", [])
        if 0 <= idx < len(nes_list):
            removed = nes_list.pop(idx)
            bot_settings["not_earn_services"] = nes_list
            save_db()
            answer_callback(call["id"], f"✅ {removed} removed!", show_alert=True)
        handle_callback({**call, "data": "not_earn_service"})

    elif data == "admin_stats":
        from datetime import datetime, timedelta
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        users_db_s = _load_users_db()
        total_users = len(users_db_s)
        today_otps = week_otps = month_otps = lifetime_otps = 0
        total_balance = 0.0
        svc_counts = {}
        for u in users_db_s.values():
            dates = u.get("otp_dates", [])
            today_otps += sum(1 for d in dates if d == today_str)
            week_otps += sum(1 for d in dates if d >= week_ago)
            month_otps += sum(1 for d in dates if d >= month_ago)
            lifetime_otps += u.get("total_otps", 0)
            total_balance += float(u.get("balance", 0.0))

        # Per-panel/service from recent_traffic
        for t in recent_traffic:
            t_date = datetime.fromtimestamp(t.get("time", 0)).strftime("%Y-%m-%d")
            if t_date == today_str:
                svc = t.get("service", "?")
                svc_counts[svc] = svc_counts.get(svc, 0) + 1

        svc_txt = ""
        for svc, cnt in sorted(svc_counts.items(), key=lambda x: -x[1])[:10]:
            svc_txt += f"├ {svc}: <b>{cnt}</b>\n"
        if not svc_txt: svc_txt = "└ No data today\n"

        # Panel stock
        panel_stock = ""
        for b_data in number_batches.values():
            svc = b_data.get("service", "?")
            country = b_data.get("country_name", b_data.get("country", "?"))
            remaining = len(b_data.get("numbers", []))
            panel_stock += f"├ {svc}/{country}: <b>{remaining}</b> left\n"
        if not panel_stock: panel_stock = "└ No stock\n"

        txt = (
            f"━━━━━━━━━━━━━━━\n"
            f"📊 <b>ADMIN STATISTICS</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: <b>{total_users}</b>\n"
            f"💰 Total Balance: <b>{total_balance:.4f} BDT</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 <b>OTP Stats:</b>\n"
            f"├ Today: <b>{today_otps}</b>\n"
            f"├ This Week: <b>{week_otps}</b>\n"
            f"├ This Month: <b>{month_otps}</b>\n"
            f"└ Lifetime: <b>{lifetime_otps}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🔥 <b>Today by Service:</b>\n{svc_txt}"
            f"━━━━━━━━━━━━━━━\n"
            f"📦 <b>Number Stock:</b>\n{panel_stock}"
            f"━━━━━━━━━━━━━━━\n"
            f"📤 Uploaded: <b>{total_uploaded_stats}</b> | 📥 Assigned: <b>{total_assigned_stats}</b>\n"
            f"━━━━━━━━━━━━━━━"
        )
        kb = [
            [{"text": "🔄 Refresh", "callback_data": "admin_stats", "style": "primary"},
             {"text": "📅 Date Filter", "callback_data": "stats_date_filter", "style": "success"}],
            [{"text": "📥 Download Balance TXT", "callback_data": "dl_balance_txt", "style": "success"}],
            [{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]
        ]
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup={"inline_keyboard": kb})

    elif data == "stats_date_filter":
        user_states[chat_id] = "wait_for_stats_date"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            "📅 Enter a date to view stats:\n\nFormat: <code>YYYY-MM-DD</code>\nExample: <code>2025-06-01</code>"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "admin_stats", "style": "danger"}]]})

    elif data == "dl_balance_txt":
        users_db_dl = _load_users_db()
        lines_out = ["Username/ID | User ID | Balance (BDT)", "─" * 40]
        for uid_str, u in sorted(users_db_dl.items(), key=lambda x: -float(x[1].get("balance", 0))):
            bal = float(u.get("balance", 0.0))
            if bal > 0:
                lines_out.append(f"@user_{uid_str} | {uid_str} | {bal:.4f}")
        content = "\n".join(lines_out)
        try:
            tmp_f = "/tmp/balance_report.txt"
            with open(tmp_f, "w", encoding="utf-8") as f:
                f.write(content)
            with open(tmp_f, "rb") as f:
                requests.post(f"{BASE_URL}/sendDocument", data={"chat_id": chat_id, "caption": "💰 Balance Report"}, files={"document": ("balance_report.txt", f)})
        except Exception as e:
            answer_callback(call["id"], f"Error: {e}", show_alert=True)

    elif data == "export_users":
        all_ids = list(all_known_users)
        content = "\n".join(str(uid) for uid in all_ids)
        try:
            tmp_f = "/tmp/users_export.txt"
            with open(tmp_f, "w", encoding="utf-8") as f:
                f.write(content)
            with open(tmp_f, "rb") as f:
                requests.post(f"{BASE_URL}/sendDocument", data={
                    "chat_id": chat_id,
                    "caption": f"📤 Users Export — {len(all_ids)} users"
                }, files={"document": ("users_export.txt", f)})
        except Exception as e:
            answer_callback(call["id"], f"Export error: {e}", show_alert=True)

    elif data == "import_users":
        user_states[chat_id] = "wait_for_import_txt"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            "📥 <b>Import Users</b>\n\n"
            "Upload a .txt file with one Chat ID per line.\n"
            "Existing users will be skipped (no data overwrite)."
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "system_settings", "style": "danger"}]]})

    elif data == "manage_services":
        svcs = bot_settings.get("services", [])
        txt = f"━━━━━━━━━━━━━━━\n🔧 <b>Manage Services</b>\n━━━━━━━━━━━━━━━\n"
        txt += f"Total: <b>{len(svcs)}</b> services\n━━━━━━━━━━━━━━━"
        edit_message(chat_id, msg_id, render_body_text(txt), reply_markup=services_keyboard())

    elif data == "add_service":
        user_states[chat_id] = "wait_for_new_service"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Enter service name (e.g., WHATSAPP):"),
                     reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "manage_services", "style": "danger"}]]})

    elif data.startswith("del_service_"):
        idx = int(data.replace("del_service_", ""))
        svcs = bot_settings.get("services", [])
        if 0 <= idx < len(svcs):
            removed = svcs.pop(idx)
            bot_settings["services"] = svcs
            save_db()
            answer_callback(call["id"], f"✅ {removed} removed!", show_alert=True)
        handle_callback({**call, "data": "manage_services"})

    elif data.startswith("upload_svc_"):
        svc_name = data.replace("upload_svc_", "")
        if not _require_temp(chat_id, "numbers"):
            answer_callback(call["id"], "❌ Session expired!", show_alert=True)
            return
        temp_data[chat_id]["service"] = svc_name.upper()
        if temp_data[chat_id].get("detected_country"):
            user_states[chat_id] = "wait_for_rate"
            edit_message(chat_id, msg_id, render_body_text(
                f"✅ Service: <b>{svc_name}</b>\n"
                f"🌍 Country: <b>{temp_data[chat_id]['detected_country']}</b>\n\n"
                f"💰 Enter rate per OTP (e.g., 0.10):"
            ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "cancel_upload", "style": "danger"}]]})
        else:
            user_states[chat_id] = "wait_for_country"
            edit_message(chat_id, msg_id, render_body_text(
                f"✅ Service: <b>{svc_name}</b>\n\n"
                f"⚠️ Country not detected. Enter country info:\n"
                f"<code>880 | BD | Bangladesh | 🇧🇩 | emoji_id</code>"
            ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "cancel_upload", "style": "danger"}]]})

    elif data == "cancel_upload":
        _cleanup_state(chat_id)
        edit_message(chat_id, msg_id, render_body_text("❌ Upload cancelled."), reply_markup=admin_panel_keyboard())

    elif data == "upload_add_another_yes":
        if not _require_temp(chat_id, "service", "detected_country", "rate"):
            answer_callback(call["id"], "❌ Session expired!", show_alert=True)
            return
        _do_upload_batch(chat_id,
                         temp_data[chat_id]["service"],
                         temp_data[chat_id]["detected_country"],
                         temp_data[chat_id].get("detected_iso", "XX"),
                         temp_data[chat_id]["rate"],
                         new_batch=True)

    elif data == "upload_add_another_no":
        if not _require_temp(chat_id, "service", "detected_country", "rate"):
            answer_callback(call["id"], "❌ Session expired!", show_alert=True)
            return
        _do_upload_batch(chat_id,
                         temp_data[chat_id]["service"],
                         temp_data[chat_id]["detected_country"],
                         temp_data[chat_id].get("detected_iso", "XX"),
                         temp_data[chat_id]["rate"],
                         new_batch=False)

    elif data == "fw_toggle_layout_{idx}" or data.startswith("fw_toggle_layout_"):
        idx = int(data.split("fw_toggle_layout_")[1])
        if idx < len(bot_settings["fw_groups"]):
            grp = bot_settings["fw_groups"][idx]
            cur = grp.get("layout", "classic")
            grp["layout"] = "modern" if cur == "classic" else "classic"
            save_db()
            answer_callback(call["id"], f"✅ Layout switched to {grp['layout'].upper()}!", show_alert=False)
            edit_message(chat_id, msg_id,
                         render_body_text(f"⚙️ Group: <code>{grp['chat_id']}</code>"),
                         reply_markup=specific_fw_group_keyboard(idx))

    elif data.startswith("fw_edit_btn1_") or data.startswith("fw_edit_btn2_"):
        which = "btn1" if "btn1" in data else "btn2"
        idx = int(data.split(f"fw_edit_{which}_")[1])
        user_states[chat_id] = f"wait_fw_{which}_{idx}"
        temp_data[chat_id] = {"msg_id": msg_id, "fw_idx": idx, "which": which}
        grp = bot_settings["fw_groups"][idx] if idx < len(bot_settings["fw_groups"]) else {}
        cur_text = grp.get(f"{which}_text", "")
        cur_url = grp.get(f"{which}_url", "")
        edit_message(chat_id, msg_id, render_body_text(
            f"📝 Edit <b>{which.upper()}</b> for group <code>{grp.get('chat_id','?')}</code>\n\n"
            f"Current: <b>{cur_text}</b> → <code>{cur_url}</code>\n\n"
            f"Send new value in format:\n<code>Button Label | https://t.me/link</code>"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": f"manage_fw_{idx}", "style": "danger"}]]})

    elif data == "xty_ref_per_otp":
        user_states[chat_id] = "wait_xty_ref_per_otp"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            f"💰 <b>Referral Per OTP Bonus</b>\n\nCurrent: <b>{bot_settings.get('refer_per_otp', 0.0)} BDT</b>\n\n"
            f"Enter new amount (0 to disable):"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "xty_control", "style": "danger"}]]})

    elif data == "xty_ref_max_otps":
        user_states[chat_id] = "wait_xty_ref_max_otps"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            f"📊 <b>Max Referral OTPs</b>\n\nCurrent: <b>{bot_settings.get('refer_max_otps', 50)}</b>\n\n"
            f"Enter max number of OTPs to count per referral:"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "xty_control", "style": "danger"}]]})

    elif data == "reset_all_balance_confirm":
        kb = [
            [{"text": "⚠️ YES, Reset ALL", "callback_data": "reset_all_balance_do", "style": "danger"},
             {"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]
        ]
        edit_message(chat_id, msg_id, render_body_text("⚠️ <b>WARNING!</b>\n\nThis will reset ALL users' balance to 0. This cannot be undone!\n\nAre you sure?"), reply_markup={"inline_keyboard": kb})

    elif data == "reset_all_balance_do":
        users_db_r = _load_users_db()
        for uid in users_db_r:
            users_db_r[uid]["balance"] = 0.0
        _save_users_db(users_db_r)
        user_cache.clear()
        answer_callback(call["id"], "✅ All balances have been reset to 0!", show_alert=True)
        edit_message(chat_id, msg_id, render_body_text("✅ <b>All balances reset to 0 BDT.</b>"), reply_markup={"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "primary"}]]})

    elif data == "set_bonus_rate":
        # Admin sets bonus rate for a specific user
        user_states[chat_id] = "wait_for_bonus_uid"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Enter the User ID to set bonus rate for:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "user_management", "style": "danger"}]]})


    elif data == "back_to_admin":
        if chat_id in user_states: del user_states[chat_id]
        edit_message(chat_id, msg_id, get_admin_text(), reply_markup=admin_panel_keyboard())
        
    elif data == "system_settings":
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['gear']} <b>System Settings</b>\nManage advanced bot configurations below:"), reply_markup=system_settings_keyboard())

    elif data == "manage_fj":
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "toggle_fj":
        bot_settings["fj_on"] = not bot_settings["fj_on"]
        save_db()
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "add_fj":
        user_states[chat_id] = "wait_for_add_fj"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send Channel Username or Invite Link:\n<i>(Note: For private channels, use the numeric ID like -100...)</i>"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_fj", "style": "danger"}]]})

    elif data.startswith("del_fj_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fj_channels"]):
            del bot_settings["fj_channels"][idx]
            save_db()
            answer_callback(call["id"], "✅ Channel deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text(f"{PEM['link']} <b>FORCE JOIN SYSTEM</b>\nManage channels below:"), reply_markup=fj_settings_keyboard())

    elif data == "manage_admins":
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['user']} <b>ADMIN MANAGEMENT</b>\nManage your bot admins below:"), reply_markup=admin_settings_keyboard())

    elif data == "add_adm":
        user_states[chat_id] = "wait_for_add_adm"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the User ID of the new Admin:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_admins", "style": "danger"}]]})

    elif data.startswith("del_adm_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["admins"]):
            del bot_settings["admins"][idx]
            save_db()
            answer_callback(call["id"], "✅ Admin deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text(f"{PEM['user']} <b>ADMIN MANAGEMENT</b>\nManage your bot admins below:"), reply_markup=admin_settings_keyboard())

    elif data == "manage_otp_groups":
        edit_message(chat_id, msg_id, render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())

    elif data == "add_fw":
        user_states[chat_id] = "wait_for_add_fw_id"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Group ID/Username to forward messages to:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "danger"}]]})

    elif data.startswith("manage_fw_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            grp_id = bot_settings["fw_groups"][idx]["chat_id"]
            edit_message(chat_id, msg_id, render_body_text(f"🛡 <b>Manage Group:</b> {grp_id}"), reply_markup=specific_fw_group_keyboard(idx))

    elif data.startswith("add_fwbtn_"):
        idx = int(data.split("_")[2])
        user_states[chat_id] = "wait_for_add_fw_btn"
        temp_data[chat_id] = {"msg_id": msg_id, "fw_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send Custom Inline Button format:\n<code>Button Text - https://link.com</code>"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"manage_fw_{idx}", "style": "danger"}]]})

    elif data.startswith("del_fwbtn_"):
        parts = data.split("_")
        idx, b_idx = int(parts[2]), int(parts[3])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            if 0 <= b_idx < len(bot_settings["fw_groups"][idx]["buttons"]):
                del bot_settings["fw_groups"][idx]["buttons"][b_idx]
                save_db()
                answer_callback(call["id"], "✅ Button deleted!", show_alert=True)
                edit_message(chat_id, msg_id, render_body_text(f"🛡 <b>Manage Group:</b> {bot_settings['fw_groups'][idx]['chat_id']}"), reply_markup=specific_fw_group_keyboard(idx))

    elif data.startswith("del_fw_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["fw_groups"]):
            del bot_settings["fw_groups"][idx]
            save_db()
            answer_callback(call["id"], "✅ Group deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text("🛡 <b>OTP GROUP MANAGEMENT</b>\nManage settings below:"), reply_markup=otp_groups_list_keyboard())

    elif data == "edit_otp_link":
        user_states[chat_id] = "wait_for_otp_link"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the new OTP Group Link:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_otp_groups", "style": "danger"}]]})

    elif data == "toggle_used_mode":
        cur = bot_settings.get("num_used_mode", "classic")
        new_mode = "modern" if cur == "classic" else "classic"
        bot_settings["num_used_mode"] = new_mode
        save_db()
        mode_desc = {
            "classic": "Allocate = Used (original)",
            "modern": "OTP Received = Used (new)"
        }
        answer_callback(call["id"], f"✅ Switched to {new_mode.upper()} mode!\n{mode_desc[new_mode]}", show_alert=True)
        edit_message(chat_id, msg_id, render_body_text(
            f"✅ <b>Used System: {new_mode.upper()}</b>\n\n"
            f"📌 <b>Classic:</b> Number marked used when allocated\n"
            f"📌 <b>Modern:</b> Number marked used only when OTP is received"
        ), reply_markup=system_settings_keyboard())

    elif data == "cpt_templates":
        templates = load_panel_templates()
        if not templates:
            txt = render_body_text("📋 <b>CPT Panel Templates</b>\n\nNo templates yet.\nUpload a .txt file or add manually.")
        else:
            txt = render_body_text(f"📋 <b>CPT Panel Templates</b>\n\n{len(templates)} template(s) available.\nSelect to add a panel:")
        edit_message(chat_id, msg_id, txt, reply_markup=panel_templates_keyboard())

    elif data == "api_templates":
        templates = load_api_templates()
        if not templates:
            txt = render_body_text("📋 <b>API Panel Templates</b>\n\nNo templates yet.\nUpload a .txt file or add manually.")
        else:
            txt = render_body_text(f"📋 <b>API Panel Templates</b>\n\n{len(templates)} template(s) available.\nSelect to add a panel:")
        edit_message(chat_id, msg_id, txt, reply_markup=api_templates_keyboard())

    elif data == "upload_cpt_tmpl_file":
        user_states[chat_id] = "wait_for_cpt_tmpl_file"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            "📤 <b>Upload CPT Panel Template File</b>\n\n"
            "Format (each panel separated by blank line):\n"
            "<code>PanelName\nlogin_url\ndata_url\nNumber3\nSMS5</code>\n\n"
            "Send the .txt file now:"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "cpt_templates", "style": "danger"}]]})

    elif data == "upload_api_tmpl_file":
        user_states[chat_id] = "wait_for_api_tmpl_file"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            "📤 <b>Upload API Panel Template File</b>\n\n"
            "Format (each panel separated by blank line):\n"
            "<code>ProviderName\nhttps://api.example.com/get?key={key}\nOptional notes</code>\n\n"
            "Send the .txt file now:"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "api_templates", "style": "danger"}]]})

    elif data == "add_cpt_tmpl_manual":
        user_states[chat_id] = "wait_for_cpt_tmpl_block"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            "✏️ <b>Add CPT Panel Template</b>\n\n"
            "Send all info in one message, line by line:\n\n"
            "<code>PanelName\nhttp://login_url\nhttp://data_url\nNumber3\nSMS5</code>"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "cpt_templates", "style": "danger"}]]})

    elif data == "add_api_tmpl_manual":
        user_states[chat_id] = "wait_for_api_tmpl_block"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text(
            "✏️ <b>Add API Panel Template</b>\n\n"
            "Send all info in one message, line by line:\n\n"
            "<code>ProviderName\nhttps://api.url?key={key}\nOptional notes</code>"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "api_templates", "style": "danger"}]]})

    elif data.startswith("use_cpt_tmpl_"):
        tmpl_idx = int(data.split("use_cpt_tmpl_")[1])
        templates = load_panel_templates()
        if tmpl_idx >= len(templates):
            answer_callback(call["id"], "❌ Template not found!", show_alert=True)
            return
        t = templates[tmpl_idx]
        temp_data[chat_id] = {"msg_id": msg_id, "tmpl_idx": tmpl_idx, "tmpl": t}
        user_states[chat_id] = "wait_for_cpt_tmpl_username"
        edit_message(chat_id, msg_id, render_body_text(
            f"📡 <b>{t['name']}</b>\n\n"
            f"🔗 Login: <code>{t['login_url']}</code>\n\n"
            f"👤 Enter <b>username</b>:"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "cpt_templates", "style": "danger"}]]})

    elif data.startswith("use_api_tmpl_"):
        tmpl_idx = int(data.split("use_api_tmpl_")[1])
        templates = load_api_templates()
        if tmpl_idx >= len(templates):
            answer_callback(call["id"], "❌ Template not found!", show_alert=True)
            return
        t = templates[tmpl_idx]
        temp_data[chat_id] = {"msg_id": msg_id, "tmpl_idx": tmpl_idx, "tmpl": t}
        user_states[chat_id] = "wait_for_api_tmpl_key"
        edit_message(chat_id, msg_id, render_body_text(
            f"🌐 <b>{t['name']}</b>\n\n"
            f"URL: <code>{t['url_template']}</code>\n"
            f"{t.get('notes','')}\n\n"
            f"🔑 Enter your <b>API Key</b>:"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "api_templates", "style": "danger"}]]})

    elif data == "cpt_delay_yes":
        user_states[chat_id] = "wait_for_cpt_delay"
        edit_message(chat_id, msg_id, render_body_text(
            "⏱ Enter delay in seconds (e.g. <code>16</code>):"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "manage_cpt_panels", "style": "danger"}]]})

    elif data == "cpt_delay_no":
        msg_id_t = temp_data.get(chat_id, {}).get("msg_id")
        try:
            # Template flow?
            if _require_temp(chat_id, "tmpl", "tmpl_user", "tmpl_pass"):
                t = temp_data[chat_id]["tmpl"]
                _save_cpt_from_template(chat_id, t, temp_data[chat_id]["tmpl_user"],
                                        temp_data[chat_id]["tmpl_pass"], 5, msg_id_t)
            # Manual p_data flow?
            elif _require_temp(chat_id, "p_data"):
                temp_data[chat_id]["p_data"]["delay_seconds"] = 5
                bot_settings["panels"].append(temp_data[chat_id]["p_data"])
                save_db()
                _cleanup_state(chat_id)
                edit_message(chat_id, msg_id, render_body_text("✅ Panel added! (5s default delay)"), reply_markup=admin_panel_keyboard())
            else:
                answer_callback(call["id"], "❌ Session expired!", show_alert=True)
        except Exception as e:
            send_message(chat_id, render_body_text(f"❌ Panel add করতে সমস্যা হয়েছে:\n<code>{e}</code>"), reply_markup=admin_panel_keyboard())

    elif data == "panel_delay_yes":
        if not _require_temp(chat_id, "p_name"):
            answer_callback(call["id"], "❌ Session expired!", show_alert=True)
            return
        user_states[chat_id] = "wait_for_p_delay"
        edit_message(chat_id, msg_id, render_body_text(
            f"⏱ Panel: <b>{temp_data[chat_id]['p_name']}</b>\n\n"
            f"Enter delay in seconds between requests (e.g. <code>16</code>):"
        ), reply_markup={"inline_keyboard": [[{"text": "Cancel", "callback_data": "manage_panels", "style": "danger"}]]})

    elif data == "panel_delay_no":
        if not _require_temp(chat_id, "p_name"):
            answer_callback(call["id"], "❌ Session expired!", show_alert=True)
            return
        p_name = temp_data[chat_id]["p_name"]
        bot_settings["panels"].append({
            "name": p_name, "type": "API Panel", "status": "OFF",
            "api_url": "", "token": "", "records": 0, "delay_seconds": 5
        })
        save_db()
        _cleanup_state(chat_id)
        handle_callback({**call, "data": "manage_api_panels"})

    elif data == "manage_panels":
        api_count = len([p for p in bot_settings["panels"] if p.get("type") == "API Panel"])
        cpt_count = len([p for p in bot_settings["panels"] if p.get("type") == "Auto Captcha Panel"])
        xisora_count = len([p for p in bot_settings["panels"] if p.get("type") == "Xisora Panel"])
        text = f"{PEM['gear']} <b>Panel Management</b>\n\nSelect which type of panel system you want to manage:"
        kb = {"inline_keyboard": [
            [{"text": f"🌐 API Panels ({api_count})", "icon_custom_emoji_id": "5336972142066047577", "callback_data": "manage_api_panels", "style": "primary"}],
            [{"text": f"🔐 Auto Captcha Panels ({cpt_count})", "icon_custom_emoji_id": "5353022963132174959", "callback_data": "manage_cpt_panels", "style": "success"}],
            [{"text": f"⚡ Xisora Panels ({xisora_count})", "icon_custom_emoji_id": "5352694861990501856", "callback_data": "manage_xisora_panels", "style": "danger"}],
            [{"text": "Back to System", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "system_settings", "style": "danger"}]
        ]}
        edit_message(chat_id, msg_id, render_body_text(text), reply_markup=kb)

    elif data in ["manage_api_panels", "manage_cpt_panels", "manage_xisora_panels"]:
        if data == "manage_api_panels":
            p_type = "API Panel"
        elif data == "manage_cpt_panels":
            p_type = "Auto Captcha Panel"
        else:
            p_type = "Xisora Panel"
        count = len([p for p in bot_settings["panels"] if p.get("type") == p_type])
        txt = render_body_text(f"📡 <b>{p_type}</b>\n\nTotal: <b>{count}</b> panels")
        kb = typed_panels_list_keyboard(p_type)
        # Add template button for CPT and API panels
        if data == "manage_cpt_panels":
            kb["inline_keyboard"].insert(-1, [{"text": "📋 Panel Templates", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "cpt_templates", "style": "success"}])
        elif data == "manage_api_panels":
            kb["inline_keyboard"].insert(-1, [{"text": "📋 API Templates", "icon_custom_emoji_id": "5353001161878182134", "callback_data": "api_templates", "style": "success"}])
        edit_message(chat_id, msg_id, txt, reply_markup=kb)

    elif data in ["add_api_panel", "add_cpt_panel", "add_xisora_panel"]:
        user_states[chat_id] = "wait_for_panel_name"
        if data == "add_api_panel":
            p_type = "api"
            back_cb = "manage_api_panels"
        elif data == "add_cpt_panel":
            p_type = "logc"
            back_cb = "manage_cpt_panels"
        else:
            p_type = "xisora"
            back_cb = "manage_api_panels"
        temp_data[chat_id] = {"msg_id": msg_id, "add_type": p_type}
        edit_message(chat_id, msg_id, render_body_text("📝 Please send the name of the New Provider:"),
                     reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": back_cb, "style": "danger"}]]})

    elif data.startswith("add_ptype_"):
        pass

    elif data in ["list_del_api", "list_del_cpt", "list_del_xisora"]:
        if data == "list_del_api":
            p_type = "API Panel"
            back_cb = "manage_api_panels"
        elif data == "list_del_cpt":
            p_type = "Auto Captcha Panel"
            back_cb = "manage_cpt_panels"
        else:
            p_type = "Xisora Panel"
            back_cb = "manage_xisora_panels"
        kb = []
        for idx, p in enumerate(bot_settings["panels"]):
            if p.get("type", "API Panel") == p_type:
                kb.append([{"text": f"Delete {p['name']}", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"do_del_pnl_{idx}", "style": "danger"}])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": back_cb, "style": "primary"}])
        edit_message(chat_id, msg_id, render_body_text(f"{PEM['trash']} <b>Select a Provider to Delete:</b>"), reply_markup={"inline_keyboard": kb})

    elif data.startswith("do_del_pnl_"):
        idx = int(data.split("_")[3])
        if 0 <= idx < len(bot_settings["panels"]):
            p_type = bot_settings["panels"][idx].get("type", "API Panel")
            del bot_settings["panels"][idx]
            save_db()
            answer_callback(call["id"], "✅ Provider Deleted!", show_alert=True)
            if p_type == "Auto Captcha Panel":
                back_data = "manage_cpt_panels"
            elif p_type == "Xisora Panel":
                back_data = "manage_xisora_panels"
            else:
                back_data = "manage_api_panels"
            handle_callback({"message": {"chat": {"id": chat_id}, "message_id": msg_id}, "data": back_data, "id": "internal"})

    elif data.startswith("tog_pnl_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["panels"]):
            p = bot_settings["panels"][idx]
            
            p["status"] = "ON" if p["status"] == "OFF" else "OFF"
            save_db()
            
            if p["type"] == "Auto Captcha Panel":
                text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>Login Status:</b> {p.get('login_status', 'Unknown')}\n<b>Login URL:</b> <code>{p.get('login_url', 'None')}</code>\n<b>User:</b> <code>{p.get('username', 'None')}</code>"
            else:
                text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>"
            edit_message(chat_id, msg_id, render_body_text(text), reply_markup=panel_config_keyboard(idx))

    elif data.startswith("conf_pnl_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["panels"]):
            p = bot_settings["panels"][idx]
            if p["type"] == "Auto Captcha Panel":
                text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>Login Status:</b> {p.get('login_status', 'Unknown')}\n<b>Login URL:</b> <code>{p.get('login_url', 'None')}</code>\n<b>User:</b> <code>{p.get('username', 'None')}</code>\n<b>Num Col:</b> {p.get('num_col_name')} (Idx: {p.get('num_col_idx')})\n<b>Msg Col:</b> {p.get('msg_col_name')} (Idx: {p.get('msg_col_idx')})"
            else:
                text = f"⚙️ <b>Configure {p['name']}</b>\n\n<b>Type:</b> {p['type']}\n<b>Status:</b> {'🟢 Monitoring' if p['status'] == 'ON' else '🔴 Stopped'}\n<b>API URL:</b> <code>{p.get('api_url', 'None')}</code>\n<b>Token:</b> <code>{p.get('token', 'None')}</code>\n<b>Full API URL:</b> <code>{p.get('full_api_url', 'None')}</code>"
            edit_message(chat_id, msg_id, render_body_text(text), reply_markup=panel_config_keyboard(idx))

    elif data.startswith("set_p_api_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_api"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the API URL for this provider:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_tok_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_tok"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the Token for this provider:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_fapi_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_fapi"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the FULL API URL (Example: http://api.com/get?key=YOUR_TOKEN&start=0):"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("set_p_rec_"):
        idx = int(data.split("_")[3])
        user_states[chat_id] = "wait_for_p_rec"
        temp_data[chat_id] = {"msg_id": msg_id, "p_idx": idx}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the number of records to fetch (e.g. 10).\nType <code>0</code> for Unlimited:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"conf_pnl_{idx}", "style": "danger"}]]})

    elif data.startswith("test_p_conn_"):
        idx = int(data.split("_")[3])
        p = bot_settings["panels"][idx]
        wait_msg = send_message(chat_id, render_body_text("⏳ Testing connection. Please wait..."))
        wait_msg_id = wait_msg.get("result", {}).get("message_id") if wait_msg else None
        answer_callback(call["id"])
        
        try:
            parsed = []
            raw_text = ""
            
            if p["type"] == "Auto Captcha Panel":
                sess = panel_sessions.get(idx)
                if not sess:
                    success = attempt_auto_login(p, idx)
                    if not success:
                        if wait_msg_id: delete_message(chat_id, wait_msg_id)
                        send_message(chat_id, render_body_text(f"❌ <b>Auto Login Failed!</b>\nReason: {html.escape(str(p.get('login_status', 'Unknown')))}"))
                        return
                    sess = panel_sessions.get(idx)
                    
                login_url = p.get("login_url", "").strip()
                if not login_url.startswith("http"): login_url = "http://" + login_url
                msg_link = p.get("msg_link", "").strip()
                if not msg_link.startswith("http") and msg_link != "": msg_link = "http://" + msg_link
                check_url = msg_link if msg_link else f"{login_url.split('/login')[0]}/client/SMSCDRStats"
                
                # 🌟 test connection supports sAjaxSource & HTML table parser
                parsed, raw_text = fetch_cpt_panel_cdrs(p, sess, check_url)
                
            else:
                full_url = p.get("full_api_url", "").strip()
                url = p.get("api_url", "").strip()
                token = p.get("token", "").strip()
                if not full_url and not url:
                    if wait_msg_id: delete_message(chat_id, wait_msg_id)
                    send_message(chat_id, render_body_text("❌ Please Set API URL or Full API URL first!"))
                    return
                
                urls_to_try = []
                if full_url:
                    urls_to_try.append(full_url)
                else:
                    if "{token}" in url or "{key}" in url:
                        urls_to_try.append(url.replace("{token}", token).replace("{key}", token))
                    elif "token=" in url or "key=" in url:
                        urls_to_try.append(url)
                    else:
                        sep = '&' if '?' in url else '?'
                        urls_to_try.append(f"{url}{sep}token={token}")
                        urls_to_try.append(f"{url}{sep}key={token}&start=0")
                        urls_to_try.append(f"{url}{sep}key={token}")
                    
                parsed = []
                raw_text = ""
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                for try_url in urls_to_try:
                    try:
                        res = requests.get(try_url, headers=headers, timeout=10)
                        raw_text = res.text
                        parsed = parse_panel_response(raw_text, p)
                        if parsed:
                            if not full_url and try_url != url and token:
                                p["api_url"] = try_url.replace(token, "{token}")
                                save_db()
                            break
                    except: pass
                 
            if wait_msg_id: delete_message(chat_id, wait_msg_id)
                 
            if parsed:
                txt = f"✅ <b>Connection Successful!</b>\n\n🎯 <b>Parsed Data Sample (Max 3):</b>\n\n"
                
                for i, sample in enumerate(parsed[:3]):
                    num = sample['number']
                    msg = sample['message']
                    otp = sample['otp']
                    
                    detected_app = detect_service(msg)
                    app_name = detected_app if detected_app else p.get("name", "Unknown")
                    app_full_name, prem_app_html = get_service_info_html(app_name, msg)
                    
                    txt += f"<b>{i+1}.</b> {prem_app_html} <b>{app_full_name}</b>\n"
                    txt += f"📱 Number: <code>{num}</code>\n"
                    txt += f"📝 Full Msg: <code>{html.escape(msg)}</code>\n"
                    txt += f"🔐 OTP: <code>{otp}</code>\n"
                    txt += "➖" * 12 + "\n"
                    
                send_message(chat_id, render_body_text(txt))
            else:
                if p["type"] == "Auto Captcha Panel":
                    try:
                        soup = BeautifulSoup(raw_text, 'html.parser')
                        tables = soup.find_all('table')
                        if tables:
                            full_table_data = "🔍 FULL TABLE DATA (A-Z)\n" + "="*50 + "\n\n"
                            for t_idx, table in enumerate(tables):
                                full_table_data += f"--- Table {t_idx+1} ---\n"
                                rows = table.find_all('tr')
                                for r_idx, row in enumerate(rows):
                                    cols = row.find_all(['th', 'td'])
                                    col_texts = [f"[{c_idx+1}] {c.get_text(separator=' ', strip=True)}" for c_idx, c in enumerate(cols)]
                                    full_table_data += f"Row {r_idx+1}: {' | '.join(col_texts)}\n"
                                full_table_data += "\n" + "="*50 + "\n"
                            
                            send_document(chat_id, f"Full_Panel_Data_{idx}.txt", full_table_data.encode('utf-8'))
                            fail_txt = f"⚠️ <b>Connected, but couldn't parse OTP data!</b>\n\n<i>আমি ওই লিংকের সম্পূর্ণ (A-Z) ডাটা একটি Text File এ পাঠিয়েছি। ফাইলটি ওপেন করে সঠিক Column Number (যেমন: [1], [3]) চেক করে প্যানেলে আপডেট করে নাও।</i>"
                            send_message(chat_id, render_body_text(fail_txt))
                        else:
                            send_message(chat_id, render_body_text(f"⚠️ <b>Connected, but no HTML Table found!</b>\nMake sure the message link is correct."))
                    except Exception as e:
                        send_message(chat_id, render_body_text(f"❌ <b>Error parsing HTML:</b> {html.escape(str(e))}"))
                else:
                    safe_html = html.escape(str(raw_text)[:300])
                    send_message(chat_id, render_body_text(f"⚠️ <b>Connected, but couldn't find/parse OTP data.</b>\n\n<i>Make sure your API config is correct.</i>\n\nRaw HTML/Data (excerpt):\n<code>{safe_html}...</code>"))
        except Exception as e:
            if wait_msg_id: delete_message(chat_id, wait_msg_id)
            send_message(chat_id, render_body_text(f"❌ <b>Connection Failed!</b>\nError: {html.escape(str(e))}"))

    elif data == "xty_control":
        if chat_id in user_states: del user_states[chat_id]
        edit_message(chat_id, msg_id, render_body_text("🕹 <b>XTY CONTROL PANEL</b>"), reply_markup=xty_control_keyboard())

    elif data == "xty_toggle_w":
        bot_settings["withdraw_on"] = not bot_settings["withdraw_on"]
        save_db()
        
        if bot_settings["withdraw_on"]:
            def broadcast_withdraw_open():
                import requests as _req, time as _t
                b_session = _req.Session()
                url = f"{BASE_URL}/sendMessage"
                bcast = "━━━━━━━━━━━━━━━\n💸 <b>WITHDRAWAL IS NOW OPEN!</b>\n━━━━━━━━━━━━━━━\n✅ You can now withdraw your balance.\nGo to <b>My Profile → Withdrawal</b>\n━━━━━━━━━━━━━━━"
                for u_id in list(all_known_users):
                    try:
                        b_session.post(url, json={"chat_id": u_id, "text": bcast, "parse_mode": "HTML"}, timeout=5)
                    except: pass
                    _t.sleep(0.035)
            threading.Thread(target=broadcast_withdraw_open, daemon=True).start()
        
        edit_message(chat_id, msg_id, render_body_text("🕹 <b>XTY CONTROL PANEL</b>"), reply_markup=xty_control_keyboard())

    elif data == "manage_w_methods":
        edit_message(chat_id, msg_id, render_body_text("💳 <b>WITHDRAWAL METHODS</b>\n\nManage your withdrawal methods below:"), reply_markup=w_methods_keyboard())

    elif data == "add_wm":
        user_states[chat_id] = "wait_for_add_wm"
        temp_data[chat_id] = {"msg_id": msg_id}
        edit_message(chat_id, msg_id, render_body_text("📝 Send the name of the new Withdrawal Method:"), reply_markup={"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "manage_w_methods", "style": "danger"}]]})

    elif data.startswith("del_wm_"):
        idx = int(data.split("_")[2])
        if 0 <= idx < len(bot_settings["w_methods"]):
            del bot_settings["w_methods"][idx]
            save_db()
            answer_callback(call["id"], "✅ Method deleted!", show_alert=True)
            edit_message(chat_id, msg_id, render_body_text("💳 <b>WITHDRAWAL METHODS</b>\n\nManage your withdrawal methods below:"), reply_markup=w_methods_keyboard())

    elif data.startswith("xty_"):
        key = data.replace("xty_", "")
        key_map = {"min_w": "min_withdraw", "otp_r": "otp_reward", "ref_r": "refer_reward", "cool": "cooldown", "num_req": "num_req", "num_share": "num_share", "sup_link": "support_link", "w_group": "w_group"}
        if key in key_map:
            temp_data[chat_id] = {"msg_id": msg_id, "key": key_map[key]}
            user_states[chat_id] = "set_xty"
            cancel_kb = {"inline_keyboard": [[{"text": "Cancel", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "cancel_xty_edit", "style": "danger"}]]}
            edit_message(chat_id, msg_id, render_body_text(f"📝 Please send the new value for <code>{key_map[key]}</code>:"), reply_markup=cancel_kb)
            answer_callback(call["id"])

    elif data == "get_number_menu":
        # Back button from country list → service list
        local_srvs = set([b["service"] for b in number_batches.values() if b["numbers"]])
        if not local_srvs:
            edit_message(chat_id, msg_id, render_body_text(f"{PEM['no']} No numbers available!"))
            return
        c_msg = bot_settings["custom_messages"].get("get_number", {})
        txt = render_body_text(c_msg.get("text", f"{PEM['pin']} Select Service"))
        apps_db = bot_settings.get("premium_apps", {})
        kb = []
        for s in local_srvs:
            emoji_id = "5352694861990501856"
            for app_key, app_data in apps_db.items():
                if s.upper() == app_key or s.upper() in app_key or app_key in s.upper():
                    if "id" in app_data: emoji_id = app_data["id"]; break
            kb.append([{"text": s, "icon_custom_emoji_id": emoji_id, "callback_data": f"g_s_{s}", "style": "primary"}])
        for b in c_msg.get("buttons", []):
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}])
        edit_message(chat_id, msg_id, txt, reply_markup={"inline_keyboard": kb})

    elif data.startswith("g_s_"):
        service = data.split("g_s_")[1]

        batches_for_svc = {
            b_id: b for b_id, b in number_batches.items()
            if b["service"] == service and b["numbers"]
        }

        c_msg = bot_settings["custom_messages"].get("select_country", {})
        raw_txt = c_msg.get("text", "📌 Select a country for {service}:").replace("{service}", service)
        txt = render_body_text(raw_txt)

        flags_db = bot_settings.get("premium_flags", {})
        kb = []
        country_buttons = []

        for b_id, b_data in batches_for_svc.items():
            c_name  = b_data.get("country_name", b_data.get("country", "Unknown"))
            c_iso   = b_data.get("country", "XX")
            rate    = b_data.get("rate", 0.0)
            count   = len(b_data["numbers"])

            # Flag: try ISO match first, then phonenumbers-based detect from first number
            emoji_id = "5780471598922337683"
            fd_match = flags_db.get(c_iso.upper()) if c_iso else None
            if fd_match:
                emoji_id = fd_match.get("id", emoji_id)
            elif b_data["numbers"]:
                # Method 2: detect from first number in batch using phonenumbers
                first_n = b_data["numbers"][0]["num"].replace("+", "").replace(" ", "")
                _, det_iso, det_eid = get_flag_info_from_num(first_n)
                if det_eid:
                    emoji_id = det_eid

            rate_str = f" • {rate} BDT"
            display_name = c_iso if c_iso and c_iso != "XX" else c_name[:3].upper()
            btn_text = f"{display_name}{rate_str}"
            country_buttons.append({
                "text": btn_text,
                "icon_custom_emoji_id": emoji_id,
                "callback_data": f"g_c_{service}__bid_{b_id}",
                "style": "success"
            })

        for i in range(0, len(country_buttons), 2):
            kb.append(country_buttons[i:i+2])

        for b in c_msg.get("buttons", []):
            b_copy = b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])

        # Back button → go back to service list
        kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176",
                    "callback_data": "get_number_menu", "style": "danger"}])
        edit_message(chat_id, msg_id, txt, reply_markup={"inline_keyboard": kb})

    elif data.startswith("g_c_") or data.startswith("c_n_"):
        # ১. গ্লোবাল কুলডাউন চেক (সকল নাম্বার মেথডের জন্য)
        now = time.time()
        if now - user_cooldowns.get(chat_id, 0) < bot_settings["cooldown"]:
            answer_callback(call["id"], f"⌛ Please wait {int(bot_settings['cooldown'] - (now - user_cooldowns.get(chat_id, 0)))}s.", show_alert=True)
            return
        
        # কুলডাউন আপডেট
        user_cooldowns[chat_id] = now
        
        # আগের নাম্বার এক্সপায়ার করা
        expire_previous_number(chat_id)

        # যদি সার্চ নাম্বার থেকে আসে
        if data.startswith("c_n_s_"):
            parts_s = data.split("_", 4)
            query = parts_s[3] if len(parts_s) > 3 else ""
            service_from_cb = parts_s[4] if len(parts_s) > 4 else None
            
            edit_message(chat_id, msg_id, render_body_text("⌛ <i>Processing... Finding Number...</i>"))
            wait_msg_id = msg_id
            

            fetched_nums = []
            search_cb_rate = float(bot_settings.get("otp_reward", 0.1))

            with _batch_lock:
                found_indices = []
                for b_id, b_data in number_batches.items():
                    for idx, n_obj in enumerate(b_data["numbers"]):
                        if n_obj["num"].replace("+", "").startswith(query) and (chat_id not in n_obj.get("used_by", []) and chat_id not in n_obj.get("allocated_to", [])):
                            found_indices.append((b_id, idx))
                if found_indices:
                    used_mode = bot_settings.get("num_used_mode", "classic")
                    random.shuffle(found_indices)
                    for b_id, idx in found_indices:
                        if len(fetched_nums) >= bot_settings.get("num_req", 1): break
                        n_obj = number_batches[b_id]["numbers"][idx]
                        num_str = n_obj["num"]
                        fetched_nums.append(num_str)
                        if len(fetched_nums) == 1:
                            search_cb_rate = float(number_batches[b_id].get("rate", bot_settings.get("otp_reward", 0.1)))
                        total_assigned_stats += 1
                        if used_mode == "classic":
                            n_obj["shares"] += 1
                            n_obj["used_by"].append(chat_id)
                            if n_obj["shares"] >= bot_settings.get("num_share", 1):
                                n_obj["to_remove"] = True
                                used_numbers_list.append(num_str)
                        else:
                            n_obj.setdefault("allocated_to", [])
                            if chat_id not in n_obj["allocated_to"]:
                                n_obj["allocated_to"].append(chat_id)
                    if used_mode == "classic":
                        for b_id in number_batches:
                            number_batches[b_id]["numbers"] = [n for n in number_batches[b_id]["numbers"] if not n.get("to_remove")]
                    save_db()
            if not fetched_nums:
                answer_callback(call["id"], "❌ Number out of stock!", show_alert=True)
                delete_message(chat_id, wait_msg_id)
                return

            kb = []
            if service_from_cb:
                app_full_name, _ = get_service_info_html(service_from_cb)
                emoji_id_srv = "5337302974806922068"
                for app_key, app_data in bot_settings.get("premium_apps", {}).items():
                    if service_from_cb.upper() == app_key or service_from_cb.upper() in app_key or app_key in service_from_cb.upper():
                        if "id" in app_data: emoji_id_srv = app_data["id"]; break
                kb.append([{"text": f"{app_full_name}", "icon_custom_emoji_id": emoji_id_srv, "callback_data": "ignore", "style": "success"}])

            flags_db = bot_settings.get("premium_flags", {})
            for num in fetched_nums:
                display_num = f"+{num}" if not str(num).startswith("+") else str(num)
                s_emoji_id = "5337302974806922068"
                if service_from_cb:
                    for app_key, app_data in bot_settings.get("premium_apps", {}).items():
                        if service_from_cb.upper() == app_key or service_from_cb.upper() in app_key or app_key in service_from_cb.upper():
                            if "id" in app_data: s_emoji_id = app_data["id"]; break
                kb.append([{"text": display_num, "icon_custom_emoji_id": s_emoji_id, "copy_text": {"text": display_num}, "style": "primary"}])
            
            srv_ext = f"_{service_from_cb}" if service_from_cb else ""
            kb.append([{"text": "Change Number", "icon_custom_emoji_id": "5465368548702446780", "callback_data": f"c_n_s_{query}{srv_ext}", "style": "success"},
                       {"text": "OTP Group", "icon_custom_emoji_id": "5190447043545438788", "url": bot_settings["otp_link"], "style": "success"}])
            
            c_btns = bot_settings["custom_messages"].get("search_number", {}).get("buttons", [])
            for c_b in c_btns: 
                b_copy = c_b.copy()
                if "style" not in b_copy: b_copy["style"] = "primary"
                kb.append([b_copy])
            kb.append([{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "danger"}])
            
            edit_message(chat_id, wait_msg_id, "ㅤ\n", reply_markup={"inline_keyboard": kb})
            user_active_sessions[chat_id] = {"msg_id": wait_msg_id, "nums": fetched_nums, "rate": search_cb_rate, "_ts": time.time()}
            return


        # যদি আপলোড করা বা সার্ভিস থেকে আসে
        # Format: g_c_{service}__bid_{batch_id}  OR  old: g_c_{service}_{country}
        if "__bid_" in data:
            # New format — direct batch_id
            after_gc = data[len("g_c_"):]
            service, bid_part = after_gc.split("__bid_", 1)
            target_batch_id = bid_part
        else:
            # Old format fallback
            parts = data.split("_")
            service = parts[2]
            country = parts[3] if len(parts) > 3 else ""
            target_batch_id = None

        available_indices = []
        fetched_nums = []
        batch_rate = float(bot_settings.get("otp_reward", 0.1))

        with _batch_lock:
            for b_id, b_data in number_batches.items():
                # Match by batch_id (new) or by service+country (old fallback)
                if target_batch_id:
                    if b_id != target_batch_id:
                        continue
                else:
                    if not (b_data["service"] == service and b_data["country"] == country):
                        continue
                for idx, n_obj in enumerate(b_data["numbers"]):
                    if (chat_id not in n_obj.get("used_by", []) and chat_id not in n_obj.get("allocated_to", [])):
                        available_indices.append((b_id, idx))

            if not available_indices:
                answer_callback(call["id"], "❌ Number out of stock!", show_alert=True)
                if data.startswith("c_n_"): delete_message(chat_id, msg_id)
                return

            used_mode = bot_settings.get("num_used_mode", "classic")
            random.shuffle(available_indices)
            for b_id, idx in available_indices:
                if len(fetched_nums) >= bot_settings.get("num_req", 1): break
                n_obj = number_batches[b_id]["numbers"][idx]
                num_str_gc = n_obj["num"]
                fetched_nums.append(num_str_gc)
                if len(fetched_nums) == 1:
                    batch_rate = float(number_batches[b_id].get("rate", bot_settings.get("otp_reward", 0.1)))
                total_assigned_stats += 1
                if used_mode == "classic":
                    n_obj["shares"] += 1
                    n_obj["used_by"].append(chat_id)
                    if n_obj["shares"] >= bot_settings.get("num_share", 1):
                        n_obj["to_remove"] = True
                        used_numbers_list.append(num_str_gc)
                else:
                    n_obj.setdefault("allocated_to", [])
                    if chat_id not in n_obj["allocated_to"]:
                        n_obj["allocated_to"].append(chat_id)

            if used_mode == "classic":
                for b_id in number_batches:
                    number_batches[b_id]["numbers"] = [n for n in number_batches[b_id]["numbers"] if not n.get("to_remove")]
            save_db()

        if not fetched_nums:
            answer_callback(call["id"], "❌ Number out of stock!", show_alert=True)
            if data.startswith("c_n_"): delete_message(chat_id, msg_id)
            return

        # Country name and flag from batch data directly
        target_b_data = None
        if target_batch_id and target_batch_id in number_batches:
            target_b_data = number_batches[target_batch_id]
        elif not target_batch_id:
            # old format - find by service+country
            for b_id, b_data in number_batches.items():
                if b_data.get("service") == service and b_data.get("country") == country:
                    target_b_data = b_data
                    break

        if target_b_data:
            country = target_b_data.get("country", "XX")
            country_name = target_b_data.get("country_name", country)
        else:
            country_name = country if 'country' in dir() else "Unknown"

        flags_db_h = bot_settings.get("premium_flags", {})
        flag_emoji_id_h = "5780471598922337683"
        for flag_code, flag_data in flags_db_h.items():
            if flag_data.get("iso", "").upper() == country.upper():
                if "id" in flag_data: flag_emoji_id_h = flag_data["id"]
                break

        # Service emoji
        app_full_name, _ = get_service_info_html(service)
        svc_emoji_id = "5337302974806922068"
        apps_db = bot_settings.get("premium_apps", {})
        for app_key, app_data in apps_db.items():
            if service.upper() == app_key or service.upper() in app_key or app_key in service.upper():
                if "id" in app_data:
                    svc_emoji_id = app_data["id"]
                    break

        # message text-এ premium emoji সহ header info
        flag_html = get_flag_info_html(country)
        svc_char = "📱"
        for app_key, app_data in bot_settings.get("premium_apps", {}).items():
            if service.upper() == app_key or service.upper() in app_key or app_key in service.upper():
                svc_char = app_data.get("char", "📱")
                break
        svc_html = f'<tg-emoji emoji-id="{svc_emoji_id}">{svc_char}</tg-emoji>'
        money_emoji = '<tg-emoji emoji-id="5409048419211682843">💰</tg-emoji>'
        header_text = render_body_text(f"{flag_html} {country} {svc_html} {app_full_name} {batch_rate} BDT {money_emoji}")

        kb = []
        for num in fetched_nums:
            display_num = f"+{num}" if not num.startswith("+") else num
            kb.append([{"text": display_num, "icon_custom_emoji_id": svc_emoji_id, "copy_text": {"text": display_num}, "style": "primary"}])

        kb.append([{"text": "Change Number", "icon_custom_emoji_id": "5465368548702446780", 
                    "callback_data": f"g_c_{service}__bid_{target_batch_id}" if target_batch_id else f"c_n_{service}_{country}", 
                    "style": "success"},
                   {"text": "OTP Group", "icon_custom_emoji_id": "5190447043545438788", "url": bot_settings["otp_link"], "style": "success"}])

        c_btns = bot_settings["custom_messages"].get("get_number", {}).get("buttons", [])
        for c_b in c_btns:
            b_copy = c_b.copy()
            if "style" not in b_copy: b_copy["style"] = "primary"
            kb.append([b_copy])

        kb.append([{"text": "Change Country", "icon_custom_emoji_id": "5267490665117275176", "callback_data": f"g_s_{service}", "style": "danger"}])

        try:
            edit_message(chat_id, msg_id, header_text, reply_markup={"inline_keyboard": kb})
            user_active_sessions[chat_id] = {"msg_id": msg_id, "nums": fetched_nums, "service": service, "country": country, "rate": batch_rate, "_ts": time.time()}
        except:
            msg_res = send_message(chat_id, header_text, reply_markup={"inline_keyboard": kb})
            if msg_res and "result" in msg_res:
                user_active_sessions[chat_id] = {"msg_id": msg_res["result"]["message_id"], "nums": fetched_nums, "service": service, "country": country, "rate": batch_rate, "_ts": time.time()}

    elif data == "confirm_withdraw":
        if chat_id not in temp_data or "amount" not in temp_data.get(chat_id, {}):
            answer_callback(call["id"], "❌ Session expired. Please start again.", show_alert=True)
            return

        method = temp_data[chat_id].get("method", "")
        amount = temp_data[chat_id].get("amount", 0)
        number = temp_data[chat_id].get("number", "")
        full_name = temp_data[chat_id].get("full_name", str(chat_id))

        # ── Fresh balance check & atomic deduct inside lock ──────────────────
        with _balance_lock:
            users_db_w = _load_users_db()
            uid_str_w = str(chat_id)
            if uid_str_w not in users_db_w:
                users_db_w[uid_str_w] = _default_user(chat_id)
            fresh_bal = float(users_db_w[uid_str_w].get("balance", 0.0))
            min_w = float(bot_settings.get("min_withdraw", 10))

            if fresh_bal < amount:
                answer_callback(call["id"], f"❌ Insufficient balance! Current: {fresh_bal:.4f} BDT", show_alert=True)
                if chat_id in user_states: del user_states[chat_id]
                if chat_id in temp_data: del temp_data[chat_id]
                return
            if amount < min_w:
                answer_callback(call["id"], f"❌ Minimum withdrawal is {min_w} BDT", show_alert=True)
                return

            # Deduct balance atomically
            users_db_w[uid_str_w]["balance"] = round(fresh_bal - float(amount), 4)
            _save_users_db(users_db_w)
            if chat_id in user_cache:
                user_cache[chat_id]["balance"] = users_db_w[uid_str_w]["balance"]

        req_id = f"W_{str(uuid.uuid4())[:6].upper()}"
        pending_withdrawals[req_id] = {
            "user_id": chat_id, "amount": amount,
            "method": method, "number": number, "full_name": full_name
        }
        _save_pending_withdrawals()

        # Save to log (atomic)
        _W_LOG = "withdrawals_log.json"
        try:
            w_log = []
            if os.path.exists(_W_LOG):
                with open(_W_LOG, "r", encoding="utf-8") as wf:
                    w_log = json.load(wf)
            w_log.append({"req_id": req_id, "user_id": str(chat_id), "amount": amount,
                          "method": method, "status": "pending", "number": number,
                          "full_name": full_name, "timestamp": time.time()})
            tmp_w = _W_LOG + ".tmp"
            with open(tmp_w, "w", encoding="utf-8") as wf:
                json.dump(w_log, wf, indent=2)
            os.replace(tmp_w, _W_LOG)
        except Exception:
            pass

        # Notify admin
        if bot_settings.get("w_group"):
            admin_msg = (
                f"🎙 <b>NEW WITHDRAWAL REQUEST</b>\n\n"
                f"👤 <b>USER:</b> <a href='tg://user?id={chat_id}'>{full_name}</a> (<code>{chat_id}</code>)\n"
                f"💳 <b>AMOUNT:</b> {amount} BDT\n"
                f"📱 <b>NUMBER:</b> <code>{number}</code>\n"
                f"🏦 <b>METHOD:</b> {method}\n\n"
                f"🧾 <b>REQ ID:</b> {req_id}"
            )
            kb = {"inline_keyboard": [[
                {"text": "✅ APPROVE", "icon_custom_emoji_id": "5352694861990501856", "callback_data": f"wapp_{req_id}", "style": "success"},
                {"text": "❌ REJECT", "icon_custom_emoji_id": "5420130255174145507", "callback_data": f"wrej_{req_id}", "style": "danger"}
            ]]}
            send_message(bot_settings["w_group"], render_body_text(admin_msg), reply_markup=kb)

        success_text = (
            f"✅ <b>Withdrawal Submitted!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🧾 Req ID: <b>{req_id}</b>\n"
            f"💰 Amount: <b>{amount} BDT</b>\n"
            f"🏦 Method: <b>{method}</b>\n"
            f"📱 Number: <code>{number}</code>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<i>Your request is under review.</i>"
        )
        kb = {"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "primary"}]]}
        edit_message(chat_id, msg_id, render_body_text(success_text), reply_markup=kb)

        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]

    elif data == "cancel_withdraw":
        if chat_id in user_states: del user_states[chat_id]
        if chat_id in temp_data: del temp_data[chat_id]
        edit_message(chat_id, msg_id, render_body_text("❌ Withdrawal cancelled."), reply_markup={"inline_keyboard": [[{"text": "Back", "icon_custom_emoji_id": "5267490665117275176", "callback_data": "close_msg", "style": "primary"}]]})

    elif data.startswith("wapp_") or data.startswith("wrej_"):
        user_id_clicked = call["from"]["id"]
        if not is_admin(user_id_clicked):
            answer_callback(call["id"], "🚫 Only Bot Admins can process withdrawals!", show_alert=True)
            return

        action = "APPROVE" if data.startswith("wapp_") else "REJECT"
        req_id = data.replace("wapp_", "").replace("wrej_", "")

        if req_id in pending_withdrawals:
            req_data = pending_withdrawals[req_id]
            u_id, amt = req_data["user_id"], req_data["amount"]
            num = req_data["number"]
            full_name = req_data.get("full_name", u_id)

            if action == "APPROVE" and len(str(num)) >= 7:
                masked_num = f"{num[:4]}XTY{num[-3:]}"
            else:
                masked_num = num

            status_text = "APPROVED ✅" if action == "APPROVE" else "REJECTED ❌"
            emoji_icon_id = "5352694861990501856" if action == "APPROVE" else "5420130255174145507"
            new_text = (
                f"🎙 <b>WITHDRAWAL {status_text}</b>\n\n"
                f"👤 <b>USER:</b> <a href='tg://user?id={u_id}'>{full_name}</a>\n"
                f"💳 <b>AMOUNT:</b> {amt} BDT\n"
                f"📱 <b>NUMBER:</b> <code>{masked_num}</code>\n"
                f"🏦 <b>METHOD:</b> {req_data['method']}\n\n"
                f"🧾 <b>REQ ID:</b> {req_id}"
            )

            kb = {"inline_keyboard": [[{"text": status_text, "icon_custom_emoji_id": emoji_icon_id, "callback_data": "ignore", "style": "success" if action == "APPROVE" else "danger"}]]}
            edit_message(chat_id, msg_id, render_body_text(new_text), reply_markup=kb)

            # Update withdrawal log (atomic)
            _W_LOG = "withdrawals_log.json"
            try:
                w_log = []
                if os.path.exists(_W_LOG):
                    with open(_W_LOG, "r", encoding="utf-8") as wf:
                        w_log = json.load(wf)
                for w in w_log:
                    if w.get("req_id") == req_id:
                        w["status"] = "approved" if action == "APPROVE" else "rejected"
                        break
                tmp_w = _W_LOG + ".tmp"
                with open(tmp_w, "w", encoding="utf-8") as wf:
                    json.dump(w_log, wf, indent=2)
                os.replace(tmp_w, _W_LOG)
            except Exception:
                pass

            if action == "REJECT":
                # Refund atomically via lock
                with _balance_lock:
                    users_db_r = _load_users_db()
                    uid_str_r = str(u_id)
                    if uid_str_r not in users_db_r:
                        users_db_r[uid_str_r] = _default_user(u_id)
                    users_db_r[uid_str_r]["balance"] = round(
                        float(users_db_r[uid_str_r].get("balance", 0.0)) + float(amt), 4)
                    _save_users_db(users_db_r)
                    if u_id in user_cache:
                        user_cache[u_id]["balance"] = users_db_r[uid_str_r]["balance"]
                send_message(u_id, render_body_text(f"❌ Your <b>{amt} BDT</b> withdrawal was rejected. Balance refunded."))
            else:
                send_message(u_id, render_body_text(f"✅ Your <b>{amt} BDT</b> withdrawal has been paid successfully!"))

            del pending_withdrawals[req_id]
            _save_pending_withdrawals()
        else:
            answer_callback(call["id"], "❌ Request already processed!", show_alert=True)

# ==========================================
# Polling Loop (Legacy - kept for compatibility)
# ==========================================
def poll_otp_with_status(number_id, num_str, owner_id, api_key):
    # Max 150 attempts × 4s = 10 minutes then stops automatically
    for attempt in range(150):
        try:
            res = requests.get(f"{NEXA_BASE_URL}/api/v1/numbers/{number_id}/sms",
                               headers={"X-API-Key": api_key}, timeout=10)
            data = res.json()
            if data.get("success") and data.get("otp"):
                otp = str(data["otp"])
                msg_text = data.get("message", f"Your code is {otp}")
                
                # 🌟 সম্পূর্ণ মেসেজ থেকে ড্যাশসহ বা বড় OTP খোঁজার ফিক্স
                extracted_otp = extract_otp_code(msg_text)
                if extracted_otp and len(extracted_otp) > len(otp):
                    otp = extracted_otp
                    
                # 🌟 সম্পূর্ণ মেসেজ থেকে সার্ভিস/অ্যাপ চেনার ফিক্স
                app_name = data.get("service", "Nexa Service")
                detected_app = detect_service(msg_text)
                if detected_app:
                    app_name = detected_app
                
                unique_id = f"POLL_{number_id}_{otp}".replace(" ", "").replace("-", "")
                if unique_id not in processed_otps:
                    processed_otps[unique_id] = time.time()
                    
                    char, iso = get_flag_and_code(num_str)
                    app_full_name, prem_app_html = get_service_info_html(app_name, msg_text)
                    
                    global recent_traffic
                    current_time = time.time()
                    recent_traffic = [t for t in recent_traffic if current_time - t.get("time", 0) <= 3600]
                    recent_traffic.append({"service": app_full_name, "iso": iso, "flag": char, "number": num_str, "time": current_time})
                    save_local_db()
                    
                    display_num = f"+{num_str}" if not str(num_str).startswith("+") else str(num_str)
                    masked = mask_number(display_num)
                    lang = detect_language(msg_text)
                    
                    display_msg = render_body_text(f"╔═══════════════╗\n║ {prem_app_html} {get_flag_info_html(display_num)} {masked} {lang}\n╚═══════════════╝")
                    
                    for fw in bot_settings.get("fw_groups", []):
                        try:
                            if fw.get("layout", "classic") == "modern":
                                send_modern_otp_to_group(fw, display_num, otp, msg_text, app_full_name)
                            else:
                                kb = [[{"text": f"{otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                                for btn in fw.get("buttons", []):
                                    b_obj = {"text": btn["text"], "url": btn["url"], "style": "primary"}
                                    if "icon_custom_emoji_id" in btn: b_obj["icon_custom_emoji_id"] = btn["icon_custom_emoji_id"]
                                    kb.append([b_obj])
                                send_message(fw["chat_id"], display_msg, reply_markup={"inline_keyboard": kb})
                        except Exception:
                            pass
                    
                    # Calculate reward and send inbox OTP message
                    not_earn_services = bot_settings.get("not_earn_services", [])
                    svc_name_key = str(app_full_name)
                    if svc_name_key.upper() not in [s.upper() for s in not_earn_services]:
                        session_info = user_active_sessions.get(owner_id, {})
                        session_rate = float(session_info.get("rate", bot_settings.get("otp_reward", 0.1)))
                        total_earn = session_rate  # bonus_rate update_balance_and_otp এর ভেতরে যোগ হবে
                    else:
                        total_earn = 0.0
                    new_bal, actual_earn = update_balance_and_otp(owner_id, total_earn, apply_bonus=True)
                    flag_html_inbox = get_flag_info_html(display_num)
                    inbox_msg = render_body_text(
                        f"New OTP Received ⚡\n\n"
                        f"Service: {prem_app_html} {svc_name_key}\n"
                        f"Number: {display_num} {flag_html_inbox}\n"
                        f"OTP: {otp} 🚀\n"
                        f"Earn: +{actual_earn} BDT 💰\n"
                        f"Balance: {new_bal} BDT"
                    )
                    inbox_kb = [[{"text": f"📋 Copy OTP: {otp}", "icon_custom_emoji_id": "5353022963132174959", "copy_text": {"text": otp}, "style": "success"}]]
                    send_message(owner_id, inbox_msg, reply_markup={"inline_keyboard": inbox_kb})
                break
        except: pass
        time.sleep(4)

def main():
    global BOT_USERNAME
    res = api_call("getMe")
    if res.get("ok"): BOT_USERNAME = res["result"]["username"]
    print(f"🤖 Bot is starting... @{BOT_USERNAME}")
    
    threading.Thread(target=panel_monitor_thread, daemon=True).start()
    print("📡 Background APIs & Panel Monitor Started!")
    
    executor = ThreadPoolExecutor(max_workers=500)
    
    offset = None
    _last_cleanup = time.time()

    while True:
        try:
            updates = api_call(f"getUpdates?timeout=50&offset={offset}")
            if updates and "result" in updates:
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        executor.submit(handle_message, update["message"])
                    elif "callback_query" in update:
                        executor.submit(handle_callback, update["callback_query"])

            # ── Periodic cleanup every 10 minutes ──────────────────────────
            now_c = time.time()
            if now_c - _last_cleanup > 600:
                _last_cleanup = now_c
                # Remove stale active sessions (older than 2 hours)
                stale_ids = [uid for uid, s in list(user_active_sessions.items())
                             if now_c - s.get("_ts", now_c) > 7200]
                for uid in stale_ids:
                    user_active_sessions.pop(uid, None)
                # Trim user_cooldowns (keep only last 1 hour)
                stale_cd = [uid for uid, ts in list(user_cooldowns.items())
                            if now_c - ts > 3600]
                for uid in stale_cd:
                    user_cooldowns.pop(uid, None)

        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    main()    