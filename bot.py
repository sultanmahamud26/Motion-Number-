import telebot
import os
import json
import subprocess
import threading
import zipfile
import shutil
import time
import secrets
import html as html_lib
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─── CONFIG ───────────────────────────────────────────────────────
BOT_TOKEN = "8793859455:AAGXnO5IUhjR9_7ey50CJgPFErv9yY1cnQQ"
ADMIN_IDS = [8348555334]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_FILE = os.path.join(BASE_DIR, "data.json")

os.makedirs(PROJECTS_DIR, exist_ok=True)

# ─── GITHUB SYNC SETUP ────────────────────────────────────────────
import github_sync

GITHUB_PAT = "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"

github_sync.setup(
    token=GITHUB_PAT,
    base_dir=BASE_DIR,
    owner="sultanmahamud26",
    repo="Motion_Host",
    branch="main"
)
# ──────────────────────────────────────────────────────────────────

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ─── THREAD-SAFE DATA ─────────────────────────────────────────────
_data_lock = threading.RLock()

def load():
    with _data_lock:
        if not os.path.exists(DATA_FILE):
            _save_raw({"users": {}, "projects": {}})
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"users": {}, "projects": {}}

def save(data):
    with _data_lock:
        _save_raw(data)

def _save_raw(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)
    # GitHub sync
    github_sync.sync_file(DATA_FILE, BASE_DIR)

# ─── PROCESS MANAGER ──────────────────────────────────────────────
processes = {}
_proc_lock = threading.RLock()

def start_bot(pid):
    data = load()
    proj = data["projects"].get(pid)
    if not proj:
        return False, "Project not found"

    proj_dir = os.path.join(PROJECTS_DIR, pid)
    main_file = proj.get("main_file", "bot.py")

    if not os.path.exists(os.path.join(proj_dir, main_file)):
        return False, f"❌ {main_file} not found"

    # Stop existing process first
    _kill_process(pid)

    # Install requirements
    req = os.path.join(proj_dir, "requirements.txt")
    if os.path.exists(req):
        subprocess.run(
            ["pip", "install", "-r", req, "-q", "--break-system-packages"],
            capture_output=True, timeout=120, cwd=proj_dir
        )

    # Load .env
    env = os.environ.copy()
    env_path = os.path.join(proj_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()

    try:
        proc = subprocess.Popen(
            ["python", "-u", main_file],
            cwd=proj_dir, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1, env=env
        )
        with _proc_lock:
            processes[pid] = {
                "process": proc, "logs": [],
                "start_time": datetime.now().isoformat(), "pid": proc.pid
            }

        def read_logs():
            for line in iter(proc.stdout.readline, ""):
                if line:
                    ts = datetime.now().strftime("%H:%M:%S")
                    with _proc_lock:
                        if pid in processes:
                            processes[pid]["logs"].append(f"[{ts}] {line.rstrip()}")
                            if len(processes[pid]["logs"]) > 500:
                                processes[pid]["logs"] = processes[pid]["logs"][-500:]

        threading.Thread(target=read_logs, daemon=True).start()

        # Auto restart watcher
        def watcher():
            proc.wait()
            time.sleep(1)
            d2 = load()
            p2 = d2["projects"].get(pid, {})
            if p2.get("auto_restart") and p2.get("status") == "running":
                with _proc_lock:
                    if pid in processes:
                        processes[pid]["logs"].append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Crashed — restarting in 5s..."
                        )
                time.sleep(5)
                # Only restart if still marked running
                d3 = load()
                if d3["projects"].get(pid, {}).get("status") == "running":
                    start_bot(pid)

        threading.Thread(target=watcher, daemon=True).start()

        data["projects"][pid]["status"] = "running"
        data["projects"][pid]["last_started"] = datetime.now().isoformat()
        save(data)
        return True, f"✅ Started (PID: {proc.pid})"
    except Exception as e:
        return False, str(e)

def _kill_process(pid):
    with _proc_lock:
        entry = processes.get(pid)
        if entry and entry.get("process"):
            try:
                entry["process"].terminate()
                entry["process"].wait(timeout=5)
            except Exception:
                try:
                    entry["process"].kill()
                except Exception:
                    pass
            entry["process"] = None

def stop_bot(pid):
    _kill_process(pid)
    data = load()
    if pid in data["projects"]:
        data["projects"][pid]["status"] = "stopped"
        save(data)
    return True

def is_running(pid):
    with _proc_lock:
        entry = processes.get(pid)
        return bool(entry and entry.get("process") and entry["process"].poll() is None)

def get_logs(pid, n=50):
    with _proc_lock:
        if pid not in processes:
            return []
        return list(processes[pid]["logs"][-n:])

# ─── AUTH ─────────────────────────────────────────────────────────
def is_authorized(uid):
    if uid in ADMIN_IDS:
        return True
    data = load()
    return str(uid) in data.get("users", {})

def is_admin(uid):
    return uid in ADMIN_IDS

def user_projects(uid):
    """Return projects visible to this user."""
    data = load()
    all_projects = data["projects"]
    if is_admin(uid):
        return all_projects
    # Users see only their own projects
    return {pid: p for pid, p in all_projects.items() if p.get("created_by") == str(uid)}

# ─── CALLBACK KEY HELPERS ─────────────────────────────────────────
# Use separator "|" instead of "_" to avoid PID collision
SEP = "|"

def cb(action, *args):
    return action + SEP + SEP.join(str(a) for a in args)

def cb_parse(data_str, action, n=1):
    """Parse callback data. Returns list of n parts after action."""
    prefix = action + SEP
    if not data_str.startswith(prefix):
        return None
    rest = data_str[len(prefix):]
    parts = rest.split(SEP, n - 1)
    return parts if len(parts) == n else None

# ─── KEYBOARDS ────────────────────────────────────────────────────
def main_menu_kb(uid):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📋 My Projects", callback_data="list_projects"),
        InlineKeyboardButton("➕ New Project", callback_data="new_project"),
        InlineKeyboardButton("📊 System Stats", callback_data="sys_stats"),
        InlineKeyboardButton("❓ Help", callback_data="help")
    )
    if is_admin(uid):
        kb.add(InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel"))
    return kb

def project_list_kb(uid):
    projects = user_projects(uid)
    kb = InlineKeyboardMarkup(row_width=2)
    items = []
    for pid, p in projects.items():
        status = "🟢" if is_running(pid) else "🔴"
        items.append(InlineKeyboardButton(
            f"{status} {p['name']}", callback_data=cb("proj", pid)
        ))
    # Add 2 per row
    for i in range(0, len(items), 2):
        row = items[i:i+2]
        kb.row(*row)
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    return kb

def project_kb(pid, running):
    kb = InlineKeyboardMarkup(row_width=2)
    if running:
        kb.add(
            InlineKeyboardButton("⏹ Stop", callback_data=cb("stop", pid)),
            InlineKeyboardButton("🔄 Restart", callback_data=cb("restart", pid))
        )
    else:
        kb.add(InlineKeyboardButton("▶️ Start", callback_data=cb("start", pid)))
    kb.add(
        InlineKeyboardButton("📁 Files", callback_data=cb("files", pid)),
        InlineKeyboardButton("📋 Logs", callback_data=cb("logs", pid))
    )
    kb.add(
        InlineKeyboardButton("🤖 AI Analyze", callback_data=cb("ai", pid)),
        InlineKeyboardButton("📦 Download ZIP", callback_data=cb("zip", pid))
    )
    kb.add(
        InlineKeyboardButton("⚙️ Settings", callback_data=cb("settings", pid)),
        InlineKeyboardButton("🗑 Delete", callback_data=cb("delete", pid))
    )
    kb.add(InlineKeyboardButton("🔙 Projects", callback_data="list_projects"))
    return kb

def files_kb(pid, files):
    kb = InlineKeyboardMarkup(row_width=1)
    icons = {"py": "🐍", "txt": "📄", "env": "🔐", "json": "📋", "md": "📝", "sh": "⚙️"}
    for f in files:
        ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
        icon = icons.get(ext, "📄")
        kb.add(InlineKeyboardButton(f"{icon} {f}", callback_data=cb("file", pid, f)))
    kb.add(
        InlineKeyboardButton("📤 Upload File", callback_data=cb("upload", pid)),
        InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid))
    )
    return kb

def file_action_kb(pid, fname):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📥 Download", callback_data=cb("dlfile", pid, fname)),
        InlineKeyboardButton("✏️ View/Edit", callback_data=cb("viewfile", pid, fname)),
        InlineKeyboardButton("🗑 Delete", callback_data=cb("delfile", pid, fname))
    )
    kb.add(InlineKeyboardButton("🔙 Files", callback_data=cb("files", pid)))
    return kb

def confirm_delfile_kb(pid, fname):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Yes, Delete", callback_data=cb("confirmdelfile", pid, fname)),
        InlineKeyboardButton("❌ Cancel", callback_data=cb("file", pid, fname))
    )
    return kb

def ai_kb(pid):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🐛 Analyze Errors", callback_data=cb("aimode", pid, "error")),
        InlineKeyboardButton("🔍 Code Review", callback_data=cb("aimode", pid, "review")),
        InlineKeyboardButton("📦 Auto Requirements", callback_data=cb("aimode", pid, "requirements")),
        InlineKeyboardButton("💡 Suggest Features", callback_data=cb("aimode", pid, "suggest"))
    )
    kb.add(InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid)))
    return kb

def back_proj_kb(pid):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid)))
    return kb

def back_files_kb(pid):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Files", callback_data=cb("files", pid)))
    return kb

def admin_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        InlineKeyboardButton("➕ Add User", callback_data="admin_adduser"),
        InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton("🤖 AI Settings", callback_data="ai_settings"),
        InlineKeyboardButton("🔙 Menu", callback_data="main_menu")
    )
    return kb

# ─── STATE ────────────────────────────────────────────────────────
waiting = {}

# ─── HELPERS ──────────────────────────────────────────────────────
def fmt_size(b):
    if b < 1024: return f"{b}B"
    elif b < 1024**2: return f"{b/1024:.1f}KB"
    return f"{b/1024/1024:.1f}MB"

def fmt_uptime(iso):
    diff = (datetime.now() - datetime.fromisoformat(iso)).total_seconds()
    if diff < 60: return f"{int(diff)}s"
    if diff < 3600: return f"{int(diff//60)}m {int(diff%60)}s"
    if diff < 86400: return f"{int(diff//3600)}h {int((diff%3600)//60)}m"
    return f"{int(diff//86400)}d {int((diff%86400)//3600)}h"

def project_info_text(pid, proj):
    running = is_running(pid)
    status = "🟢 Running" if running else "🔴 Stopped"
    uptime = ""
    if running and pid in processes:
        with _proc_lock:
            st = processes[pid].get("start_time", "")
        if st:
            uptime = f"\n⏱ Uptime: <code>{fmt_uptime(st)}</code>"
    tags = " ".join([f"#{t}" for t in proj.get("tags", [])]) or "—"
    return (
        f"<b>🤖 {proj['name']}</b>\n"
        f"{'─'*28}\n"
        f"📌 Status: {status}{uptime}\n"
        f"📄 Main: <code>{proj.get('main_file','bot.py')}</code>\n"
        f"🏷 Tags: {tags}\n"
        f"🔄 Auto-restart: {'✅' if proj.get('auto_restart') else '❌'}\n"
        f"📅 Created: {proj.get('created','')[:10]}\n"
        f"{'─'*28}\n"
        f"💬 {proj.get('description') or 'No description'}"
    )

def safe_edit(call, text, reply_markup=None):
    """Edit message, ignore MessageNotModified errors."""
    try:
        bot.edit_message_text(
            text, call.message.chat.id, call.message.message_id,
            reply_markup=reply_markup, parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            raise

# ─── GEMINI AI ────────────────────────────────────────────────────
AI_SETTINGS_FILE = os.path.join(BASE_DIR, "ai_settings.json")

def load_ai_settings():
    if not os.path.exists(AI_SETTINGS_FILE):
        default = {"gemini_api_key": "AQ.Ab8RN6JhUt-hAYGeyJVWtWjJvuwGcdhOKl5wbWVzQoAaA0vanA", "model": "gemini-2.0-flash"}
        with open(AI_SETTINGS_FILE, "w") as f:
            json.dump(default, f, indent=2)
        github_sync.sync_file(AI_SETTINGS_FILE, BASE_DIR)
        return default
    with open(AI_SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_ai_settings(settings):
    with open(AI_SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
    github_sync.sync_file(AI_SETTINGS_FILE, BASE_DIR)

def ask_ai(prompt):
    try:
        import requests as req
        cfg = load_ai_settings()
        api_key = cfg.get("gemini_api_key", "")
        if not api_key:
            return "❌ AI API Key সেট করা নেই। Admin Panel → AI Settings থেকে সেট করো।"
        model = cfg.get("model", "gemini-2.0-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        r = req.post(
            url,
            headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7}},
            timeout=40
        )
        result = r.json()
        if "error" in result:
            err = result["error"]
            code = err.get("code", "")
            msg = err.get("message", "Unknown error")
            if code == 400:
                return f"❌ API Key ভুল বা Invalid।\nAdmin Panel → AI Settings থেকে ঠিক করো।"
            if code == 429:
                return "❌ Rate limit হয়েছে। একটু পরে আবার চেষ্টা করো।"
            return f"❌ Gemini Error: {msg}"
        candidates = result.get("candidates", [])
        if not candidates:
            return "❌ AI কোনো response দেয়নি।"
        return candidates[0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ AI Error: {e}"

def ai_test_key(api_key):
    """API key টেস্ট করো"""
    try:
        import requests as req
        r = req.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
            json={"contents": [{"parts": [{"text": "Say OK"}]}],
                  "generationConfig": {"maxOutputTokens": 10}},
            timeout=15
        )
        result = r.json()
        if "error" in result:
            return False, result["error"].get("message", "Invalid key")
        return True, "✅ Key valid!"
    except Exception as e:
        return False, str(e)

def ai_analyze(pid, mode):
    data = load()
    proj = data["projects"].get(pid, {})
    proj_dir = os.path.join(PROJECTS_DIR, pid)

    if mode == "error":
        logs = get_logs(pid, 80)
        log_text = "\n".join(logs) if logs else "No logs available"
        prompt = (
            "তুমি একজন Python Telegram bot debugging expert।\n"
            f"Project: {proj.get('name', pid)}\n\n"
            f"নিচের logs analyze করো:\n{log_text}\n\n"
            "বাংলায় উত্তর দাও:\n"
            "1. কী সমস্যা হয়েছে (সহজ ভাষায়)\n"
            "2. কোন line/file এ সমস্যা\n"
            "3. exact fix কী"
        )
    elif mode == "review":
        mf = proj.get("main_file", "bot.py")
        fp = os.path.join(proj_dir, mf)
        if not os.path.exists(fp):
            return "❌ Main file পাওয়া যায়নি"
        with open(fp, "r", errors="ignore") as f:
            code = f.read()[:6000]
        prompt = (
            "এই Python Telegram bot code review করো।\n"
            "বাংলায় উত্তর দাও:\n"
            "1. Bugs বা errors\n"
            "2. Security সমস্যা\n"
            "3. Performance improvement\n"
            "4. Missing error handling\n\n"
            f"Code:\n{code}"
        )
    elif mode == "requirements":
        mf = proj.get("main_file", "bot.py")
        fp = os.path.join(proj_dir, mf)
        if not os.path.exists(fp):
            return "❌ Main file পাওয়া যায়নি"
        with open(fp, "r", errors="ignore") as f:
            code = f.read()[:6000]
        prompt = (
            "এই Python code analyze করে requirements.txt তৈরি করো।\n"
            "শুধু third-party packages লেখো (stdlib না)।\n"
            "শুধু package names, কোনো explanation না।\n\n"
            f"Code:\n{code}"
        )
    elif mode == "suggest":
        mf = proj.get("main_file", "bot.py")
        fp = os.path.join(proj_dir, mf)
        code = ""
        if os.path.exists(fp):
            with open(fp, "r", errors="ignore") as f:
                code = f.read()[:4000]
        prompt = (
            f"এই Telegram bot project \"{proj.get('name', pid)}\" এর জন্য\n"
            "5-8টা useful feature suggest করো যা add করলে bot আরো ভালো হবে।\n"
            "বাংলায় specific ও practical suggestion দাও।\n"
            + (f"\nCode:\n{code}" if code else "")
        )
    else:
        return "Unknown mode"

    result = ask_ai(prompt)

    if mode == "requirements" and not result.startswith("❌"):
        req_path = os.path.join(proj_dir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write(result.strip())
        github_sync.sync_file(req_path, BASE_DIR)
        return result + "\n\n✅ requirements.txt হিসেবে save হয়েছে"

    return result

# ─── /start ───────────────────────────────────────────────────────
@bot.message_handler(commands=["start", "menu"])
def cmd_start(msg):
    uid = msg.from_user.id
    if not is_authorized(uid):
        bot.send_message(uid, "⛔ Access denied. Contact admin.")
        return
    name = msg.from_user.first_name or "there"
    role = "👑 Admin" if is_admin(uid) else "👤 User"
    projects = user_projects(uid)
    running_count = sum(1 for pid in projects if is_running(pid))
    text = (
        f"👋 Welcome, <b>{name}</b>! [{role}]\n\n"
        f"⚡ <b>BotManager</b> — Multi-bot process manager\n\n"
        f"📋 Projects: <b>{len(projects)}</b> | 🟢 Running: <b>{running_count}</b>\n"
        f"Upload files, start/stop, view logs, AI analyze."
    )
    bot.send_message(uid, text, reply_markup=main_menu_kb(uid))

@bot.message_handler(commands=["admin"])
def cmd_admin(msg):
    uid = msg.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "⛔ Admins only.")
        return
    bot.send_message(uid, "👑 <b>Admin Panel</b>", reply_markup=admin_kb())

# ─── Handle file uploads ───────────────────────────────────────────
@bot.message_handler(content_types=["document"])
def handle_document(msg):
    uid = msg.from_user.id
    if not is_authorized(uid):
        return
    w = waiting.get(uid)
    if not w or w["action"] != "upload_file":
        bot.send_message(uid, "ℹ️ Use Files menu → Upload File to upload.")
        return

    pid = w["data"]["pid"]
    proj_dir = os.path.join(PROJECTS_DIR, pid)
    os.makedirs(proj_dir, exist_ok=True)

    fname = msg.document.file_name
    finfo = bot.get_file(msg.document.file_id)
    downloaded = bot.download_file(finfo.file_path)

    fpath = os.path.join(proj_dir, fname)
    with open(fpath, "wb") as f:
        f.write(downloaded)

    if fname.endswith(".zip"):
        try:
            with zipfile.ZipFile(fpath, "r") as z:
                z.extractall(proj_dir)
            os.remove(fpath)
            # ZIP extract হওয়া সব ফাইল sync করো
            github_sync.sync_dir(proj_dir, BASE_DIR)
            bot.send_message(uid, f"✅ <b>{fname}</b> extracted!", reply_markup=back_files_kb(pid))
        except Exception as e:
            bot.send_message(uid, f"❌ ZIP extract failed: {e}", reply_markup=back_files_kb(pid))
    else:
        # Single file sync
        github_sync.sync_file(fpath, BASE_DIR)
        bot.send_message(uid, f"✅ <b>{fname}</b> uploaded ({fmt_size(len(downloaded))})", reply_markup=back_files_kb(pid))

    waiting.pop(uid, None)

# ─── Handle text input ─────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(msg):
    uid = msg.from_user.id
    if not is_authorized(uid):
        return

    w = waiting.get(uid)
    if not w:
        return

    action = w["action"]
    text = msg.text.strip()

    if action == "new_project_name":
        waiting[uid] = {"action": "new_project_desc", "data": {"name": text}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("⏭ Skip", callback_data="skip_desc"))
        bot.send_message(uid, "📝 Description? (or tap Skip)", reply_markup=kb)

    elif action == "new_project_desc":
        desc = "" if text == "/skip" else text
        waiting[uid] = {"action": "new_project_mainfile", "data": {**w["data"], "desc": desc}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("⏭ Skip (bot.py)", callback_data="skip_mainfile"))
        bot.send_message(uid, "📄 Main file name? (default: bot.py)", reply_markup=kb)

    elif action == "new_project_mainfile":
        main_file = "bot.py" if text == "/skip" else text
        waiting[uid] = {"action": "new_project_tags", "data": {**w["data"], "main_file": main_file}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("⏭ Skip", callback_data="skip_tags"))
        bot.send_message(uid, "🏷 Tags? comma separated (e.g: otp,telegram)", reply_markup=kb)

    elif action == "new_project_tags":
        tags = [] if text == "/skip" else [t.strip() for t in text.split(",") if t.strip()]
        _create_project(uid, w["data"], tags)

    elif action == "add_user":
        try:
            new_uid = int(text)
            data = load()
            data["users"][str(new_uid)] = {"added_by": str(uid), "added": datetime.now().isoformat()}
            save(data)
            waiting.pop(uid, None)
            bot.send_message(uid, f"✅ User <code>{new_uid}</code> added!", reply_markup=admin_kb())
        except ValueError:
            bot.send_message(uid, "❌ Invalid ID. Send a number.")

    elif action == "broadcast":
        _do_broadcast(uid, text)
        waiting.pop(uid, None)

    elif action == "ai_set_key":
        new_key = text.strip()
        safe_msg = bot.send_message(uid, "🧪 Key টেস্ট করছি...")
        ok, result = ai_test_key(new_key)
        if ok:
            cfg = load_ai_settings()
            cfg["gemini_api_key"] = new_key
            save_ai_settings(cfg)
            waiting.pop(uid, None)
            bot.edit_message_text(
                f"✅ <b>API Key সেট হয়েছে!</b>\n\nAI features এখন কাজ করবে।",
                uid, safe_msg.message_id, parse_mode="HTML",
                reply_markup=admin_kb()
            )
        else:
            bot.edit_message_text(
                f"❌ <b>Key Invalid!</b>\n\n{result}\n\nআবার সঠিক key পাঠাও।",
                uid, safe_msg.message_id, parse_mode="HTML"
            )

    elif action == "edit_file":
        pid = w["data"]["pid"]
        fname = w["data"]["fname"]
        fpath = os.path.join(PROJECTS_DIR, pid, fname)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(text)
            github_sync.sync_file(fpath, BASE_DIR)
            waiting.pop(uid, None)
            bot.send_message(uid, f"✅ <b>{fname}</b> saved!", reply_markup=file_action_kb(pid, fname))
        except Exception as e:
            bot.send_message(uid, f"❌ Save failed: {e}")

    elif action == "rename_project":
        pid = w["data"]["pid"]
        data = load()
        if pid in data["projects"]:
            data["projects"][pid]["name"] = text
            save(data)
        waiting.pop(uid, None)
        bot.send_message(uid, f"✅ Renamed to <b>{text}</b>!", reply_markup=project_kb(pid, is_running(pid)))

    elif action == "change_mainfile":
        pid = w["data"]["pid"]
        data = load()
        if pid in data["projects"]:
            data["projects"][pid]["main_file"] = text
            save(data)
        waiting.pop(uid, None)
        bot.send_message(uid, f"✅ Main file changed to <code>{text}</code>!", reply_markup=project_kb(pid, is_running(pid)))

def _create_project(uid, d, tags):
    data = load()
    pid = d["name"].lower().replace(" ", "_")[:20] + "_" + secrets.token_hex(3)
    proj_dir = os.path.join(PROJECTS_DIR, pid)
    os.makedirs(proj_dir, exist_ok=True)
    data["projects"][pid] = {
        "name": d["name"], "description": d.get("desc", ""),
        "main_file": d.get("main_file", "bot.py"), "tags": tags,
        "status": "stopped", "auto_restart": False,
        "created": datetime.now().isoformat(), "created_by": str(uid)
    }
    save(data)
    # নতুন project folder sync করো
    github_sync.sync_dir(os.path.join(PROJECTS_DIR, pid), BASE_DIR)
    waiting.pop(uid, None)
    bot.send_message(uid,
        f"✅ Project <b>{d['name']}</b> created!\n\n"
        f"Now upload files via Files → Upload File.",
        reply_markup=project_kb(pid, False)
    )

def _do_broadcast(uid, text):
    data = load()
    all_uids = list(data.get("users", {}).keys()) + [str(a) for a in ADMIN_IDS]
    sent = 0
    for target in set(all_uids):
        try:
            bot.send_message(int(target), f"📢 <b>Broadcast:</b>\n\n{text}")
            sent += 1
        except Exception:
            pass
    bot.send_message(uid, f"✅ Broadcast sent to {sent} users.", reply_markup=admin_kb())

# ─── CALLBACKS ────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = call.from_user.id
    if not is_authorized(uid):
        bot.answer_callback_query(call.id, "⛔ Access denied")
        return

    d = call.data
    bot.answer_callback_query(call.id)

    try:
        _handle_callback(call, uid, d)
    except Exception as e:
        # parse_mode=HTML globally set আছে, তাই exception message escape করতে হবে
        bot.send_message(uid, f"❌ Error: {html_lib.escape(str(e))}")

def _handle_callback(call, uid, d):
    # ── Main menu ──
    if d == "main_menu":
        name = call.from_user.first_name or "there"
        projects = user_projects(uid)
        running_count = sum(1 for pid in projects if is_running(pid))
        safe_edit(call,
            f"👋 <b>{name}</b> — BotManager Menu\n"
            f"📋 Projects: <b>{len(projects)}</b> | 🟢 Running: <b>{running_count}</b>",
            reply_markup=main_menu_kb(uid)
        )

    # ── List projects ──
    elif d == "list_projects":
        projects = user_projects(uid)
        if not projects:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("➕ Create First Project", callback_data="new_project"))
            kb.add(InlineKeyboardButton("🔙 Menu", callback_data="main_menu"))
            safe_edit(call, "📋 No projects yet.", reply_markup=kb)
            return
        running = sum(1 for pid in projects if is_running(pid))
        safe_edit(call,
            f"📋 <b>Your Projects</b> ({len(projects)} total, {running} running):",
            reply_markup=project_list_kb(uid)
        )

    # ── New project ──
    elif d == "new_project":
        waiting[uid] = {"action": "new_project_name", "data": {}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="main_menu"))
        safe_edit(call, "📝 Project name দাও:", reply_markup=kb)

    # ── Skip buttons for new project flow ──
    elif d == "skip_desc":
        w = waiting.get(uid, {})
        if w.get("action") == "new_project_desc":
            waiting[uid] = {"action": "new_project_mainfile", "data": {**w["data"], "desc": ""}}
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⏭ Skip (bot.py)", callback_data="skip_mainfile"))
            safe_edit(call, "📄 Main file name? (default: bot.py)", reply_markup=kb)

    elif d == "skip_mainfile":
        w = waiting.get(uid, {})
        if w.get("action") == "new_project_mainfile":
            waiting[uid] = {"action": "new_project_tags", "data": {**w["data"], "main_file": "bot.py"}}
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("⏭ Skip", callback_data="skip_tags"))
            safe_edit(call, "🏷 Tags? comma separated", reply_markup=kb)

    elif d == "skip_tags":
        w = waiting.get(uid, {})
        if w.get("action") == "new_project_tags":
            _create_project(uid, w["data"], [])

    # ── Project detail ──
    elif d.startswith("proj" + SEP):
        parts = cb_parse(d, "proj", 1)
        if not parts: return
        pid = parts[0]
        data = load()
        proj = data["projects"].get(pid)
        if not proj:
            safe_edit(call, "❌ Project not found.")
            return
        safe_edit(call, project_info_text(pid, proj), reply_markup=project_kb(pid, is_running(pid)))

    # ── Start ──
    elif d.startswith("start" + SEP):
        parts = cb_parse(d, "start", 1)
        if not parts: return
        pid = parts[0]
        safe_edit(call, "⏳ Starting...")
        ok, msg_text = start_bot(pid)
        data = load()
        proj = data["projects"].get(pid, {})
        safe_edit(call, f"{msg_text}\n\n" + project_info_text(pid, proj),
                  reply_markup=project_kb(pid, ok))

    # ── Stop ──
    elif d.startswith("stop" + SEP):
        parts = cb_parse(d, "stop", 1)
        if not parts: return
        pid = parts[0]
        stop_bot(pid)
        data = load()
        proj = data["projects"].get(pid, {})
        safe_edit(call, "⏹ Stopped.\n\n" + project_info_text(pid, proj),
                  reply_markup=project_kb(pid, False))

    # ── Restart ──
    elif d.startswith("restart" + SEP):
        parts = cb_parse(d, "restart", 1)
        if not parts: return
        pid = parts[0]
        safe_edit(call, "🔄 Restarting...")
        stop_bot(pid)
        time.sleep(1)
        ok, msg_text = start_bot(pid)
        data = load()
        proj = data["projects"].get(pid, {})
        safe_edit(call, f"🔄 {msg_text}\n\n" + project_info_text(pid, proj),
                  reply_markup=project_kb(pid, ok))

    # ── Logs ──
    elif d.startswith("logs" + SEP):
        parts = cb_parse(d, "logs", 1)
        if not parts: return
        pid = parts[0]
        logs = get_logs(pid, 40)
        if not logs:
            text = "📋 No logs yet. Start the bot first."
        else:
            lines = "\n".join(logs[-35:])
            # html_lib.escape() দিয়ে <module> <listcomp> ইত্যাদি escape করা হচ্ছে
            # না করলে parse_mode=HTML এ Telegram 400 error দেয়
            escaped_lines = html_lib.escape(lines[:3800])
            text = f"📋 <b>Logs (last 35):</b>\n\n<pre>{escaped_lines}</pre>"
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("🔄 Refresh", callback_data=cb("logs", pid)),
            InlineKeyboardButton("🗑 Clear", callback_data=cb("clearlogs", pid)),
            InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid))
        )
        safe_edit(call, text, reply_markup=kb)

    # ── Clear logs ──
    elif d.startswith("clearlogs" + SEP):
        parts = cb_parse(d, "clearlogs", 1)
        if not parts: return
        pid = parts[0]
        with _proc_lock:
            if pid in processes:
                processes[pid]["logs"] = []
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid)))
        safe_edit(call, "🗑 Logs cleared.", reply_markup=kb)

    # ── Files list ──
    elif d.startswith("files" + SEP):
        parts = cb_parse(d, "files", 1)
        if not parts: return
        pid = parts[0]
        proj_dir = os.path.join(PROJECTS_DIR, pid)
        os.makedirs(proj_dir, exist_ok=True)
        files = sorted([f for f in os.listdir(proj_dir) if os.path.isfile(os.path.join(proj_dir, f))])
        data = load()
        proj = data["projects"].get(pid, {})
        text = (f"📁 <b>{proj.get('name','?')}</b> — {len(files)} file(s)" if files
                else f"📁 <b>{proj.get('name','?')}</b> — No files yet")
        safe_edit(call, text, reply_markup=files_kb(pid, files))

    # ── Upload prompt ──
    elif d.startswith("upload" + SEP):
        parts = cb_parse(d, "upload", 1)
        if not parts: return
        pid = parts[0]
        waiting[uid] = {"action": "upload_file", "data": {"pid": pid}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data=cb("files", pid)))
        safe_edit(call,
            "📤 Send the file now (bot.py, .env, requirements.txt, .zip...)\n\n"
            "<i>ZIP files will be auto-extracted</i>",
            reply_markup=kb
        )

    # ── File detail ──
    elif d.startswith("file" + SEP):
        parts = cb_parse(d, "file", 2)
        if not parts: return
        pid, fname = parts
        proj_dir = os.path.join(PROJECTS_DIR, pid)
        fpath = os.path.join(proj_dir, fname)
        size = fmt_size(os.path.getsize(fpath)) if os.path.exists(fpath) else "?"
        safe_edit(call,
            f"📄 <b>{fname}</b>\n📦 Size: {size}",
            reply_markup=file_action_kb(pid, fname)
        )

    # ── Download file ──
    elif d.startswith("dlfile" + SEP):
        parts = cb_parse(d, "dlfile", 2)
        if not parts: return
        pid, fname = parts
        fpath = os.path.join(PROJECTS_DIR, pid, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                bot.send_document(uid, f, visible_file_name=fname,
                                  caption=f"📥 <b>{fname}</b>")
        else:
            bot.send_message(uid, "❌ File not found")

    # ── View/Edit file ──
    elif d.startswith("viewfile" + SEP):
        parts = cb_parse(d, "viewfile", 2)
        if not parts: return
        pid, fname = parts
        fpath = os.path.join(PROJECTS_DIR, pid, fname)
        if not os.path.exists(fpath):
            bot.send_message(uid, "❌ File not found")
            return
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            preview = content[:3000]
            kb = InlineKeyboardMarkup(row_width=1)
            kb.add(
                InlineKeyboardButton("✏️ Edit (send new content)", callback_data=cb("startedit", pid, fname)),
                InlineKeyboardButton("🔙 Back", callback_data=cb("file", pid, fname))
            )
            safe_edit(call,
                f"📄 <b>{fname}</b>:\n\n<pre>{html_lib.escape(preview)}</pre>{'...(truncated)' if len(content)>3000 else ''}",
                reply_markup=kb
            )
        except Exception:
            bot.send_message(uid, "⚠️ Binary file — use Download instead.")

    # ── Start edit ──
    elif d.startswith("startedit" + SEP):
        parts = cb_parse(d, "startedit", 2)
        if not parts: return
        pid, fname = parts
        waiting[uid] = {"action": "edit_file", "data": {"pid": pid, "fname": fname}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data=cb("file", pid, fname)))
        safe_edit(call,
            f"✏️ Send new content for <b>{fname}</b>:\n\n"
            "<i>⚠️ This will replace the entire file!</i>",
            reply_markup=kb
        )

    # ── Delete file (confirm first) ──
    elif d.startswith("delfile" + SEP):
        parts = cb_parse(d, "delfile", 2)
        if not parts: return
        pid, fname = parts
        safe_edit(call,
            f"⚠️ Delete <b>{fname}</b>?\n\nThis cannot be undone.",
            reply_markup=confirm_delfile_kb(pid, fname)
        )

    # ── Confirm delete file ──
    elif d.startswith("confirmdelfile" + SEP):
        parts = cb_parse(d, "confirmdelfile", 2)
        if not parts: return
        pid, fname = parts
        fpath = os.path.join(PROJECTS_DIR, pid, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            # GitHub থেকেও delete করো
            github_sync.sync_delete(fpath, BASE_DIR)
            proj_dir = os.path.join(PROJECTS_DIR, pid)
            files = sorted([f for f in os.listdir(proj_dir) if os.path.isfile(os.path.join(proj_dir, f))])
            safe_edit(call, f"🗑 <b>{fname}</b> deleted.", reply_markup=files_kb(pid, files))
        else:
            safe_edit(call, f"❌ File not found.", reply_markup=back_files_kb(pid))

    # ── Download ZIP ──
    elif d.startswith("zip" + SEP):
        parts = cb_parse(d, "zip", 1)
        if not parts: return
        pid = parts[0]
        data = load()
        proj = data["projects"].get(pid, {})
        proj_dir = os.path.join(PROJECTS_DIR, pid)
        zip_path = os.path.join(BASE_DIR, f"{pid}_backup.zip")
        safe_edit(call, "⏳ Creating ZIP...")
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(proj_dir):
                    for file in files:
                        fp = os.path.join(root, file)
                        z.write(fp, os.path.relpath(fp, proj_dir))
            with open(zip_path, "rb") as f:
                bot.send_document(uid, f,
                    visible_file_name=f"{proj.get('name','project')}_backup.zip",
                    caption=f"📦 <b>{proj.get('name','?')}</b> backup")
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)
        data2 = load()
        proj2 = data2["projects"].get(pid, {})
        safe_edit(call, project_info_text(pid, proj2), reply_markup=project_kb(pid, is_running(pid)))

    # ── AI menu ──
    elif d.startswith("ai" + SEP):
        parts = cb_parse(d, "ai", 1)
        if not parts: return
        pid = parts[0]
        safe_edit(call, "🤖 <b>AI Analysis</b>\n\nSelect type:", reply_markup=ai_kb(pid))

    elif d.startswith("aimode" + SEP):
        parts = cb_parse(d, "aimode", 2)
        if not parts: return
        pid, mode = parts
        safe_edit(call, "🤖 AI analyzing... ⏳")
        result = ai_analyze(pid, mode)
        result_short = result[:3500] if len(result) > 3500 else result
        mode_names = {"error": "Error Analysis", "review": "Code Review",
                      "requirements": "Requirements", "suggest": "Feature Suggestions"}
        safe_edit(call,
            f"🤖 <b>AI {mode_names.get(mode, mode)}:</b>\n\n<pre>{html_lib.escape(result_short)}</pre>",
            reply_markup=back_proj_kb(pid)
        )

    # ── Settings ──
    elif d.startswith("settings" + SEP):
        parts = cb_parse(d, "settings", 1)
        if not parts: return
        pid = parts[0]
        data = load()
        proj = data["projects"].get(pid, {})
        ar = proj.get("auto_restart", False)
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton(
                f"🔄 Auto-restart: {'✅ ON' if ar else '❌ OFF'}",
                callback_data=cb("toggle_ar", pid)
            ),
            InlineKeyboardButton("✏️ Rename Project", callback_data=cb("rename", pid)),
            InlineKeyboardButton("📄 Change Main File", callback_data=cb("changemain", pid)),
            InlineKeyboardButton("🔁 Reset Project", callback_data=cb("reset", pid)),
            InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid))
        )
        safe_edit(call, f"⚙️ <b>{proj.get('name','?')}</b> Settings", reply_markup=kb)

    elif d.startswith("toggle_ar" + SEP):
        parts = cb_parse(d, "toggle_ar", 1)
        if not parts: return
        pid = parts[0]
        data = load()
        proj = data["projects"].get(pid, {})
        proj["auto_restart"] = not proj.get("auto_restart", False)
        save(data)
        ar = proj["auto_restart"]
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton(
                f"🔄 Auto-restart: {'✅ ON' if ar else '❌ OFF'}",
                callback_data=cb("toggle_ar", pid)
            ),
            InlineKeyboardButton("✏️ Rename Project", callback_data=cb("rename", pid)),
            InlineKeyboardButton("📄 Change Main File", callback_data=cb("changemain", pid)),
            InlineKeyboardButton("🔁 Reset Project", callback_data=cb("reset", pid)),
            InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid))
        )
        safe_edit(call, f"⚙️ Auto-restart: {'ON ✅' if ar else 'OFF ❌'}", reply_markup=kb)

    elif d.startswith("rename" + SEP):
        parts = cb_parse(d, "rename", 1)
        if not parts: return
        pid = parts[0]
        waiting[uid] = {"action": "rename_project", "data": {"pid": pid}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data=cb("settings", pid)))
        safe_edit(call, "✏️ Send new project name:", reply_markup=kb)

    elif d.startswith("changemain" + SEP):
        parts = cb_parse(d, "changemain", 1)
        if not parts: return
        pid = parts[0]
        waiting[uid] = {"action": "change_mainfile", "data": {"pid": pid}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data=cb("settings", pid)))
        safe_edit(call, "📄 Send new main file name (e.g. main.py):", reply_markup=kb)

    # ── Reset project ──
    elif d.startswith("reset" + SEP):
        parts = cb_parse(d, "reset", 1)
        if not parts: return
        pid = parts[0]
        data = load()
        proj = data["projects"].get(pid, {})
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("✅ Yes, Reset", callback_data=cb("confirmreset", pid)),
            InlineKeyboardButton("❌ Cancel", callback_data=cb("settings", pid))
        )
        proj_name = proj.get('name', '?')
        safe_edit(call,
            f"🔁 <b>Reset {proj_name}</b>?\n\n"
            f"⚠️ প্রজেক্টের সমস্ত ফাইল ডিলিট হবে!\n"
            f"শুধু প্রজেক্ট entry থাকবে — fresh start হবে।",
            reply_markup=kb
        )

    elif d.startswith("confirmreset" + SEP):
        parts = cb_parse(d, "confirmreset", 1)
        if not parts: return
        pid = parts[0]
        # বট বন্ধ করো
        stop_bot(pid)
        # প্রজেক্ট folder সম্পূর্ণ মুছে নতুন করো
        proj_dir = os.path.join(PROJECTS_DIR, pid)
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir)
        os.makedirs(proj_dir, exist_ok=True)
        # data.json এ status reset করো
        data = load()
        if pid in data["projects"]:
            data["projects"][pid]["status"] = "stopped"
            data["projects"][pid]["last_started"] = ""
            save(data)
        # GitHub sync — empty folder
        github_sync.sync_dir(proj_dir, BASE_DIR)
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("📁 Upload Files", callback_data=cb("upload", pid)),
            InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid))
        )
        safe_edit(call,
            "✅ <b>Project Reset সম্পন্ন!</b>\n\n"
            "সব ফাইল মুছে গেছে। এখন নতুন করে ফাইল আপলোড করো।",
            reply_markup=kb
        )

    # ── Delete project ──
    elif d.startswith("delete" + SEP):
        parts = cb_parse(d, "delete", 1)
        if not parts: return
        pid = parts[0]
        data = load()
        proj = data["projects"].get(pid, {})
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("✅ Yes, Delete", callback_data=cb("confirmdelete", pid)),
            InlineKeyboardButton("❌ Cancel", callback_data=cb("proj", pid))
        )
        safe_edit(call,
            f"⚠️ Delete <b>{proj.get('name','?')}</b>?\n\nThis will delete ALL files permanently!",
            reply_markup=kb
        )

    elif d.startswith("confirmdelete" + SEP):
        parts = cb_parse(d, "confirmdelete", 1)
        if not parts: return
        pid = parts[0]
        stop_bot(pid)
        proj_dir = os.path.join(PROJECTS_DIR, pid)
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir)
        data = load()
        name = data["projects"].get(pid, {}).get("name", "?")
        if pid in data["projects"]:
            del data["projects"][pid]
        save(data)
        with _proc_lock:
            processes.pop(pid, None)
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📋 Projects", callback_data="list_projects"))
        safe_edit(call, f"🗑 <b>{name}</b> deleted.", reply_markup=kb)

    # ── System stats ──
    elif d == "sys_stats":
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            data = load()
            all_proj = user_projects(uid)
            running_count = sum(1 for pid in all_proj if is_running(pid))
            text = (
                f"📊 <b>System Stats</b>\n{'─'*28}\n"
                f"🖥 CPU: <b>{cpu}%</b>\n"
                f"💾 RAM: <b>{mem.used//1024//1024}MB / {mem.total//1024//1024}MB</b> ({mem.percent}%)\n"
                f"💿 Disk: <b>{disk.used//1024//1024//1024}GB / {disk.total//1024//1024//1024}GB</b>\n"
                f"{'─'*28}\n"
                f"🤖 Running bots: <b>{running_count}</b>\n"
                f"📋 Total projects: <b>{len(all_proj)}</b>"
            )
        except ImportError:
            data = load()
            all_proj = user_projects(uid)
            running_count = sum(1 for pid in all_proj if is_running(pid))
            text = (
                f"📊 <b>Stats</b>\n"
                f"🤖 Running: <b>{running_count}</b>\n"
                f"📋 Projects: <b>{len(all_proj)}</b>\n\n"
                f"<i>Install psutil for full stats</i>"
            )
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("🔄 Refresh", callback_data="sys_stats"),
            InlineKeyboardButton("🔙 Menu", callback_data="main_menu")
        )
        safe_edit(call, text, reply_markup=kb)

    # ── Admin panel ──
    elif d == "admin_panel":
        if not is_admin(uid):
            bot.answer_callback_query(call.id, "⛔ Admins only")
            return
        safe_edit(call, "👑 <b>Admin Panel</b>", reply_markup=admin_kb())

    elif d == "admin_users":
        if not is_admin(uid): return
        data = load()
        users = data.get("users", {})
        if not users:
            text = "👥 No users added yet."
        else:
            lines = [f"• <code>{u_id}</code> — added {info.get('added','')[:10]}"
                     for u_id, info in users.items()]
            text = "?? <b>Authorized Users:</b>\n\n" + "\n".join(lines)
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("➕ Add User", callback_data="admin_adduser"),
            InlineKeyboardButton("🗑 Remove User", callback_data="admin_removeuser"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        )
        safe_edit(call, text, reply_markup=kb)

    elif d == "admin_adduser":
        if not is_admin(uid): return
        waiting[uid] = {"action": "add_user", "data": {}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="admin_panel"))
        safe_edit(call,
            "👤 Send the Telegram User ID to authorize:\n\n"
            "<i>User must /start the bot first</i>",
            reply_markup=kb
        )

    elif d == "admin_removeuser":
        if not is_admin(uid): return
        data = load()
        users = data.get("users", {})
        if not users:
            bot.answer_callback_query(call.id, "No users to remove")
            return
        kb = InlineKeyboardMarkup(row_width=1)
        for u_id in users:
            kb.add(InlineKeyboardButton(f"🗑 {u_id}", callback_data=cb("removeuser", u_id)))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data="admin_users"))
        safe_edit(call, "Select user to remove:", reply_markup=kb)

    elif d.startswith("removeuser" + SEP):
        if not is_admin(uid): return
        parts = cb_parse(d, "removeuser", 1)
        if not parts: return
        target = parts[0]
        data = load()
        if target in data["users"]:
            del data["users"][target]
            save(data)
        safe_edit(call, f"✅ User {target} removed.", reply_markup=admin_kb())

    elif d == "admin_broadcast":
        if not is_admin(uid): return
        waiting[uid] = {"action": "broadcast", "data": {}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="admin_panel"))
        safe_edit(call, "📢 Send broadcast message (HTML supported):", reply_markup=kb)

    # ── AI Settings ──
    elif d == "ai_settings":
        if not is_admin(uid): return
        cfg = load_ai_settings()
        key = cfg.get("gemini_api_key", "")
        key_display = f"<code>{key[:20]}...</code>" if len(key) > 20 else ("<code>সেট করা নেই</code>" if not key else f"<code>{key}</code>")
        model = cfg.get("model", "gemini-2.0-flash")
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("🔑 API Key পরিবর্তন করো", callback_data="ai_change_key"),
            InlineKeyboardButton("🧪 API Key টেস্ট করো", callback_data="ai_test"),
            InlineKeyboardButton("🗑 API Key মুছো", callback_data="ai_remove_key"),
            InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
        )
        safe_edit(call,
            f"🤖 <b>AI Settings</b>\n"
            f"{'─'*28}\n"
            f"🔑 Current Key: {key_display}\n"
            f"🧠 Model: <code>{model}</code>\n"
            f"{'─'*28}\n"
            f"📊 Free limit: 1500 req/day\n"
            f"🌐 Provider: Google Gemini",
            reply_markup=kb
        )

    elif d == "ai_change_key":
        if not is_admin(uid): return
        waiting[uid] = {"action": "ai_set_key", "data": {}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="ai_settings"))
        safe_edit(call,
            "🔑 নতুন Gemini API Key পাঠাও:\n\n"
            "👉 পেতে যাও: <a href='https://aistudio.google.com/apikey'>aistudio.google.com/apikey</a>",
            reply_markup=kb
        )

    elif d == "ai_test":
        if not is_admin(uid): return
        cfg = load_ai_settings()
        key = cfg.get("gemini_api_key", "")
        if not key:
            bot.answer_callback_query(call.id, "❌ Key সেট করা নেই!")
            return
        safe_edit(call, "🧪 Testing API Key...")
        ok, msg = ai_test_key(key)
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 AI Settings", callback_data="ai_settings"))
        safe_edit(call,
            f"{'✅' if ok else '❌'} <b>Test Result:</b>\n\n{msg}",
            reply_markup=kb
        )

    elif d == "ai_remove_key":
        if not is_admin(uid): return
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("✅ হ্যাঁ, মুছো", callback_data="ai_confirm_remove"),
            InlineKeyboardButton("❌ না", callback_data="ai_settings")
        )
        safe_edit(call, "⚠️ API Key মুছে ফেলবে?\nAI features কাজ করবে না।", reply_markup=kb)

    elif d == "ai_confirm_remove":
        if not is_admin(uid): return
        cfg = load_ai_settings()
        cfg["gemini_api_key"] = ""
        save_ai_settings(cfg)
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 AI Settings", callback_data="ai_settings"))
        safe_edit(call, "✅ API Key মুছে দেওয়া হয়েছে।", reply_markup=kb)

    # ── Help ──
    elif d == "help":
        text = (
            "❓ <b>How to use BotManager:</b>\n\n"
            "1️⃣ <b>New Project</b> — project তৈরি করো\n"
            "2️⃣ <b>Files → Upload</b> — bot.py, requirements.txt, .env পাঠাও\n"
            "3️⃣ <b>Start</b> — bot চালু করো\n"
            "4️⃣ <b>Logs</b> — real-time output দেখো\n"
            "5️⃣ <b>AI Analyze</b> — error fix, code review, feature suggestions\n"
            "6️⃣ <b>Files → View/Edit</b> — সরাসরি file edit করো\n\n"
            "📦 ZIP upload করলে auto-extract হবে\n"
            "🔄 Auto-restart — Settings এ on/off করো\n"
            "📥 Download ZIP — পুরো project backup নাও\n"
            "📢 Broadcast — Admin: সব user কে message পাঠাও"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Menu", callback_data="main_menu"))
        safe_edit(call, text, reply_markup=kb)

# ─── RUN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 BotManager starting...")
    print(f"Admin IDs: {ADMIN_IDS}")
    # Auto-start bots that were running before restart
    data = load()
    auto_started = 0
    for pid, proj in data["projects"].items():
        if proj.get("status") == "running" and proj.get("auto_restart"):
            ok, _ = start_bot(pid)
            if ok:
                auto_started += 1
    if auto_started:
        print(f"✅ Auto-started {auto_started} bots")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
