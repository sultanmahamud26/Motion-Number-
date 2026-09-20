import telebot
import os
import sys
import json
import subprocess
import threading
import zipfile
import shutil
import time
import re
import secrets
import html as html_lib
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─── CONFIG ───────────────────────────────────────────────────────
BOT_TOKEN = "8339740358:AAFB1lOmpKbpNFHie39PSoqDRO-bkykWel4"
ADMIN_IDS = [8348555334]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_FILE = os.path.join(BASE_DIR, "data.json")
BACKUP_SETTINGS_FILE = os.path.join(BASE_DIR, "backup_settings.json")

os.makedirs(PROJECTS_DIR, exist_ok=True)

# ─── GITHUB BACKUP SYSTEM: সম্পূর্ণরূপে সরিয়ে ফেলা হয়েছে ──────────
# এখন backup হচ্ছে "Universal Backup / Restore" সিস্টেম দিয়ে (নিচে দেখো),
# যেটা সব প্রজেক্ট একসাথে ZIP করে বটেই পাঠিয়ে দেয়, GitHub লাগে না।
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

# ─── PROCESS MANAGER ──────────────────────────────────────────────
processes = {}
_proc_lock = threading.RLock()

def get_python_cmd():
    """
    সার্ভারভেদে কখনো 'python', কখনো 'python3' কমান্ড কাজ করে।
    সবচেয়ে নিরাপদ উপায় হলো sys.executable — যেই interpreter দিয়ে এই
    ম্যানেজার বটটাই চলছে, ঠিক সেটা দিয়েই child bot চালানো। এটা সবসময় থাকে।
    শুধু sys.executable কোনো কারণে না পাওয়া গেলে python3 → python → py fallback করে।
    """
    if sys.executable:
        return sys.executable
    for cand in ("python3", "python", "py"):
        found = shutil.which(cand)
        if found:
            return found
    return "python3"

PYTHON_CMD = get_python_cmd()

# ─── PER-PROJECT PYTHON VERSION (pyenv-based auto install) ────────
# ম্যানেজার ডিফল্টভাবে নিজের interpreter (sys.executable) দিয়েই child বট
# চালানোর চেষ্টা করে — কিন্তু client-এর বট যদি অন্য Python ভার্সন চায়
# (যেমন match-case, নতুন syntax ইত্যাদির জন্য), তাহলে সেটা এমনি এমনি
# ক্র্যাশ করবে। নিচের হেল্পারগুলো pyenv ব্যবহার করে দরকারি ভার্সন
# সার্ভারে অটোমেটিকলি ইনস্টল করে সেটা দিয়েই বট চালায় — client-কে
# ম্যানুয়ালি কিছু করতে হয় না।
#
# সার্ভারে একবার pyenv + build dependencies (build-essential, libssl-dev,
# zlib1g-dev, libbz2-dev, libreadline-dev, libsqlite3-dev ইত্যাদি) থাকতে
# হবে যাতে pyenv নতুন ভার্সন কম্পাইল করতে পারে। pyenv না থাকলে এই
# ফিচারটা silently স্কিপ হয়ে যাবে এবং ডিফল্ট PYTHON_CMD ব্যবহার হবে।
PYENV_ROOT = os.environ.get("PYENV_ROOT", os.path.expanduser("~/.pyenv"))
PYENV_BIN = os.path.join(PYENV_ROOT, "bin", "pyenv")

def _pyenv_cmd():
    return shutil.which("pyenv") or (PYENV_BIN if os.path.exists(PYENV_BIN) else None)

def list_installed_pyenv_versions():
    cmd = _pyenv_cmd()
    if not cmd:
        return []
    try:
        out = subprocess.run([cmd, "versions", "--bare"], capture_output=True, text=True, timeout=15)
        return [v.strip() for v in out.stdout.splitlines() if v.strip()]
    except Exception:
        return []

def pyenv_install_version(version):
    """pyenv দিয়ে নির্দিষ্ট Python ভার্সন সার্ভারে ইনস্টল করে (আগে থেকে থাকলে skip করে)।"""
    cmd = _pyenv_cmd()
    if not cmd:
        return False, "pyenv সার্ভারে ইনস্টল করা নেই"
    try:
        r = subprocess.run([cmd, "install", "-s", version], capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            return False, (r.stderr or "install failed")[-500:]
        return True, "installed"
    except Exception as e:
        return False, str(e)

def get_python_for_version(version):
    """pyenv version string থেকে python বাইনারির পাথ বের করে; না থাকলে অটো-ইনস্টল করে।"""
    if not _pyenv_cmd():
        return None
    if version not in list_installed_pyenv_versions():
        ok, _msg = pyenv_install_version(version)
        if not ok:
            return None
    py_path = os.path.join(PYENV_ROOT, "versions", version, "bin", "python")
    return py_path if os.path.exists(py_path) else None

def detect_runtime_version(proj_dir):
    """
    প্রজেক্ট ফোল্ডারে runtime.txt থাকলে সেখান থেকে দরকারি Python ভার্সন বের করে।
    Heroku-স্টাইল ফরম্যাট সাপোর্ট করে: 'python-3.11.6' অথবা শুধু '3.11.6' / '3.11'
    """
    rt = os.path.join(proj_dir, "runtime.txt")
    if not os.path.exists(rt):
        return None
    try:
        with open(rt) as f:
            line = f.read().strip()
        m = re.search(r"(\d+\.\d+(?:\.\d+)?)", line)
        return m.group(1) if m else None
    except Exception:
        return None

def get_latest_stable_pyenv_version():
    """pyenv-এ ইনস্টলযোগ্য সবচেয়ে নতুন স্টেবল Python 3.x.x ভার্সন বের করে।"""
    cmd = _pyenv_cmd()
    if not cmd:
        return None
    try:
        out = subprocess.run([cmd, "install", "--list"], capture_output=True, text=True, timeout=20)
        candidates = [ln.strip() for ln in out.stdout.splitlines() if re.fullmatch(r"3\.\d+\.\d+", ln.strip())]
        if not candidates:
            return None
        candidates.sort(key=lambda s: tuple(int(x) for x in s.split(".")))
        return candidates[-1]
    except Exception:
        return None

def looks_like_version_error(text):
    """স্টার্টআপ ক্র্যাশ লগ দেখে বোঝার চেষ্টা করে যে এটা Python ভার্সন-সংক্রান্ত সমস্যা কিনা।"""
    if not text:
        return False
    low = text.lower()
    return ("syntaxerror" in low) or ("invalid syntax" in low) or ("requires python" in low)

def resolve_python_cmd(proj_dir, proj):
    """
    এই নির্দিষ্ট প্রজেক্টের জন্য সঠিক Python interpreter ঠিক করে:
    1) প্রজেক্টে আগে থেকে auto-detect করা / সেট করা python_version থাকলে সেটা
    2) না থাকলে প্রজেক্টের runtime.txt থেকে
    3) ভার্সন পাওয়া গেলে pyenv দিয়ে দরকারে অটো-ইনস্টল করে সেই ভার্সনের পাথ রিটার্ন করে
    4) কিছুই না মিললে ডিফল্ট PYTHON_CMD (ম্যানেজার নিজে যেই interpreter এ চলছে)
    রিটার্ন করে: (python_path, forced_version_or_None)
    """
    version = proj.get("python_version") or detect_runtime_version(proj_dir)
    if version:
        py = get_python_for_version(version)
        if py:
            return py, version
    return PYTHON_CMD, None

def _watch_for_version_issue(pid, had_forced_version):
    """
    যদি বট explicit ভার্সন ছাড়াই স্টার্ট হওয়ার সাথে সাথে ক্র্যাশ করে এবং লগে
    Python ভার্সন-মিসম্যাচের চিহ্ন দেখা যায়, তাহলে সার্ভারে সবচেয়ে নতুন
    Python ভার্সন অটোমেটিক ইনস্টল করে সেটা দিয়ে আবার বট চালানোর চেষ্টা করে।
    """
    if had_forced_version:
        return
    time.sleep(4)
    with _proc_lock:
        entry = processes.get(pid)
        if not entry:
            return
        proc = entry.get("process")
        recent_logs = "\n".join(entry.get("logs", []))
    if proc is None or proc.poll() in (None, 0):
        return  # এখনো চলছে বা normally exit করেছে — সমস্যা নেই
    if not looks_like_version_error(recent_logs):
        return
    latest = get_latest_stable_pyenv_version()
    if not latest:
        return
    py = get_python_for_version(latest)
    if not py:
        return
    data2 = load()
    if pid in data2["projects"]:
        data2["projects"][pid]["python_version"] = latest
        save(data2)
    with _proc_lock:
        if pid in processes:
            processes[pid]["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Python ভার্সন মিসম্যাচ ধরা পড়েছে — "
                f"Python {latest} অটো-ইনস্টল করে বট আবার চালু করা হচ্ছে..."
            )
    start_bot(pid)

def start_bot(pid):
    data = load()
    proj = data["projects"].get(pid)
    if not proj:
        return False, "Project not found"

    owner = proj.get("created_by")
    if owner and is_user_expired(owner):
        return False, "⛔ এই ক্লায়েন্টের মেয়াদ শেষ হয়ে গেছে — বট চালু করা যাবে না। ফাইল সুরক্ষিত আছে; এক্সপায়ারি বাড়ালে আবার চালানো যাবে।"

    proj_dir = os.path.join(PROJECTS_DIR, pid)
    main_file = proj.get("main_file", "bot.py")

    if not os.path.exists(os.path.join(proj_dir, main_file)):
        return False, f"❌ {main_file} not found"

    # Stop existing process first
    _kill_process(pid)

    python_cmd, forced_version = resolve_python_cmd(proj_dir, proj)

    # Install requirements — ওই একই (resolve করা) interpreter দিয়ে pip module
    # চালানো হচ্ছে, তাই "pip" vs "pip3" নাম নিয়ে সমস্যা হয় না
    req = os.path.join(proj_dir, "requirements.txt")
    if os.path.exists(req):
        subprocess.run(
            [python_cmd, "-m", "pip", "install", "-r", req, "-q", "--break-system-packages"],
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
            [python_cmd, "-u", main_file],
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
        threading.Thread(target=_watch_for_version_issue, args=(pid, forced_version is not None), daemon=True).start()

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

# ─── UNIVERSAL BACKUP / RESTORE ───────────────────────────────────
def create_universal_backup():
    """সব প্রজেক্ট + data.json + ai_settings.json একটা ZIP এ প্যাক করো।"""
    zip_path = os.path.join(BASE_DIR, f"universal_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(PROJECTS_DIR):
            for file in files:
                fp = os.path.join(root, file)
                z.write(fp, os.path.relpath(fp, BASE_DIR))
        if os.path.exists(DATA_FILE):
            z.write(DATA_FILE, os.path.relpath(DATA_FILE, BASE_DIR))
        if os.path.exists(AI_SETTINGS_FILE):
            z.write(AI_SETTINGS_FILE, os.path.relpath(AI_SETTINGS_FILE, BASE_DIR))
    return zip_path

def load_backup_settings():
    if not os.path.exists(BACKUP_SETTINGS_FILE):
        default = {"enabled": False, "interval_minutes": 30}
        with open(BACKUP_SETTINGS_FILE, "w") as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(BACKUP_SETTINGS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"enabled": False, "interval_minutes": 30}

def save_backup_settings(s):
    with open(BACKUP_SETTINGS_FILE, "w") as f:
        json.dump(s, f, indent=2)

def auto_backup_worker():
    """প্রতি নির্দিষ্ট ইন্টারভালে সব প্রজেক্টের ব্যাকআপ Admin-দের কাছে পাঠায়।"""
    while True:
        s = load_backup_settings()
        if not s.get("enabled"):
            time.sleep(30)
            continue
        mins = s.get("interval_minutes", 30)
        try:
            mins = max(1, int(mins))
        except (TypeError, ValueError):
            mins = 30
        time.sleep(mins * 60)
        s2 = load_backup_settings()
        if not s2.get("enabled"):
            continue
        try:
            zip_path = create_universal_backup()
            for admin_id in ADMIN_IDS:
                try:
                    with open(zip_path, "rb") as f:
                        bot.send_document(
                            admin_id, f, visible_file_name=os.path.basename(zip_path),
                            caption=f"🗄 Auto Backup — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        )
                except Exception:
                    pass
            os.remove(zip_path)
        except Exception as e:
            print(f"⚠️ Auto backup error: {e}")

# ─── AUTO MAIN-FILE DETECTION ──────────────────────────────────────
def auto_normalize_main_file(pid):
    """
    প্রজেক্টের রুটে যদি ঠিক একটাই .py ফাইল থাকে (অন্য কোনো .py ফাইল না থাকে),
    তাহলে সেটা automatic bot.py তে rename করে main_file হিসেবে সেট করে দেয়।
    একাধিক .py ফাইল থাকলে কিছুই পরিবর্তন হয় না — ইউজার নিজে main file বেছে নেবে।
    """
    proj_dir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(proj_dir):
        return
    py_files = [f for f in os.listdir(proj_dir)
                if f.endswith(".py") and os.path.isfile(os.path.join(proj_dir, f))]
    if len(py_files) != 1:
        return
    only = py_files[0]
    if only != "bot.py":
        src = os.path.join(proj_dir, only)
        dst = os.path.join(proj_dir, "bot.py")
        try:
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
        except Exception:
            return
    data = load()
    if pid in data["projects"]:
        data["projects"][pid]["main_file"] = "bot.py"
        save(data)

# ─── AUTH ─────────────────────────────────────────────────────────
def is_authorized(uid):
    if uid in ADMIN_IDS:
        return True
    data = load()
    return str(uid) in data.get("users", {})

def is_admin(uid):
    return uid in ADMIN_IDS

# ─── CLIENT EXPIRY ──────────────────────────────────────────────────
# expiry_date হলো "YYYY-MM-DD" ফরম্যাটের একটা string, data["users"][uid] এ
# সেভ করা থাকে। মেয়াদ শেষ হলে শুধু client-এর চলমান বটগুলো স্টপ করা হয় —
# প্রজেক্ট/ফাইল কিচ্ছু ডিলিট হয় না। এক্সপায়ারি বাড়িয়ে দিলেই আবার normally
# Start করা যাবে।
def parse_expiry(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        return None

def is_user_expired(uid):
    try:
        if int(uid) in ADMIN_IDS:
            return False  # admin-দের কখনো expiry দিয়ে আটকানো হয় না
    except (TypeError, ValueError):
        pass
    data = load()
    info = data.get("users", {}).get(str(uid), {})
    exp = info.get("expiry_date")
    if not exp:
        return False
    dt = parse_expiry(exp)
    if not dt:
        return False
    # এক্সপায়ারি দিনের শেষ (23:59:59) পর্যন্ত অ্যাক্সেস valid থাকবে
    return datetime.now() > dt.replace(hour=23, minute=59, second=59)

def expiry_checker_worker():
    """
    প্রতি ৫ মিনিটে সব ক্লায়েন্টের expiry_date চেক করে। মেয়াদ শেষ হয়ে গেলে
    শুধুমাত্র তার চলমান বটগুলো স্টপ করে দেয় (ফাইল/প্রজেক্ট সুরক্ষিত থাকে),
    client ও admin-কে নোটিফাই করে। এক্সপায়ারি পরে বাড়ানো হলে ফ্ল্যাগ রিসেট হয়ে
    যায় যাতে আবার normally বট চালানো যায়।
    """
    while True:
        try:
            data = load()
            changed = False
            for u_id, info in data.get("users", {}).items():
                expired_now = is_user_expired(u_id)
                if expired_now and not info.get("expired_notified"):
                    for pid, proj in data["projects"].items():
                        if proj.get("created_by") == u_id and proj.get("status") == "running":
                            stop_bot(pid)
                    info["expired_notified"] = True
                    changed = True
                    try:
                        bot.send_message(
                            int(u_id),
                            "⛔ তোমার অ্যাক্সেসের মেয়াদ শেষ হয়ে গেছে। তোমার সব বট স্টপ করে দেওয়া "
                            "হয়েছে — ফাইল/প্রজেক্ট কিছুই ডিলিট হয়নি। অ্যাক্সেস আবার চালু করতে "
                            "অ্যাডমিনের সাথে যোগাযোগ করো।"
                        )
                    except Exception:
                        pass
                    for admin_id in ADMIN_IDS:
                        try:
                            name = info.get("display_name", u_id)
                            bot.send_message(
                                admin_id,
                                f"⏳ ক্লায়েন্ট <b>{name}</b> (<code>{u_id}</code>) এর মেয়াদ শেষ হয়েছে — "
                                f"তার চলমান বটগুলো স্টপ করা হয়েছে।"
                            )
                        except Exception:
                            pass
                elif not expired_now and info.get("expired_notified"):
                    info["expired_notified"] = False
                    changed = True
            if changed:
                save(data)
        except Exception as e:
            print(f"⚠️ Expiry checker error: {e}")
        time.sleep(300)

def user_projects(uid):
    """Return ALL projects visible to this user (admin sees everyone's, for stats)."""
    data = load()
    all_projects = data["projects"]
    if is_admin(uid):
        return all_projects
    return own_projects_for(uid)

def own_projects_for(uid):
    """Return only the projects created by this specific uid (str or int)."""
    data = load()
    all_projects = data["projects"]
    return {pid: p for pid, p in all_projects.items() if p.get("created_by") == str(uid)}

# Alias used by limit-checking / project-creation code
own_projects = own_projects_for

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
    projects = own_projects_for(uid)
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
        InlineKeyboardButton("📁 Files", callback_data=cb("files", pid, "")),
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

def list_dir_entries(proj_dir, relpath):
    """proj_dir/relpath এর ভিতরের entries রিটার্ন করো: [(name, is_dir), ...] ফোল্ডার আগে, তারপর ফাইল।"""
    target = os.path.join(proj_dir, relpath) if relpath else proj_dir
    if not os.path.isdir(target):
        return []
    names = sorted(os.listdir(target))
    dirs = [(n, True) for n in names if os.path.isdir(os.path.join(target, n))]
    files = [(n, False) for n in names if os.path.isfile(os.path.join(target, n))]
    return dirs + files

def files_kb(pid, relpath, entries):
    kb = InlineKeyboardMarkup(row_width=1)
    icons = {"py": "🐍", "txt": "📄", "env": "🔐", "json": "📋", "md": "📝", "sh": "⚙️"}
    if relpath:
        parent = "/".join(relpath.split("/")[:-1])
        kb.add(InlineKeyboardButton("⬅️ .. (up)", callback_data=cb("files", pid, parent)))
    for name, is_dir in entries:
        rel = f"{relpath}/{name}" if relpath else name
        if is_dir:
            kb.add(InlineKeyboardButton(f"📂 {name}", callback_data=cb("files", pid, rel)))
        else:
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            icon = icons.get(ext, "📄")
            kb.add(InlineKeyboardButton(f"{icon} {name}", callback_data=cb("file", pid, rel)))
    kb.add(
        InlineKeyboardButton("📤 Upload File", callback_data=cb("upload", pid, relpath)),
        InlineKeyboardButton("🔙 Back", callback_data=cb("proj", pid))
    )
    return kb

def file_action_kb(pid, fname):
    parent = os.path.dirname(fname)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📥 Download", callback_data=cb("dlfile", pid, fname)),
        InlineKeyboardButton("✏️ View/Edit", callback_data=cb("viewfile", pid, fname)),
        InlineKeyboardButton("✏️ Rename", callback_data=cb("renamefile", pid, fname)),
        InlineKeyboardButton("🗑 Delete", callback_data=cb("delfile", pid, fname))
    )
    kb.add(InlineKeyboardButton("🔙 Files", callback_data=cb("files", pid, parent)))
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

def back_files_kb(pid, relpath=""):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Files", callback_data=cb("files", pid, relpath)))
    return kb

def admin_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👥 Users", callback_data="admin_users"),
        InlineKeyboardButton("➕ Add User", callback_data="admin_adduser"),
        InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton("🤖 AI Settings", callback_data="ai_settings"),
        InlineKeyboardButton("👨‍👩‍👧 Clients", callback_data="clients_list"),
        InlineKeyboardButton("🗄 Universal Backup", callback_data="universal_backup"),
        InlineKeyboardButton("♻️ Universal Restore", callback_data="universal_restore_prompt"),
        InlineKeyboardButton("⏱ Auto Backup Timer", callback_data="backup_timer_settings"),
        InlineKeyboardButton("🔙 Menu", callback_data="main_menu")
    )
    return kb

def client_list_kb():
    data = load()
    users = data.get("users", {})
    kb = InlineKeyboardMarkup(row_width=1)
    for u_id, info in users.items():
        label = info.get("display_name") or u_id
        proj_count = len(own_projects_for(u_id))
        mark = "⛔ " if is_user_expired(u_id) else ""
        kb.add(InlineKeyboardButton(f"{mark}👤 {label} ({proj_count})", callback_data=cb("clientprojects", u_id)))
    kb.add(InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"))
    return kb

def client_project_list_kb(client_uid):
    data = load()
    projects = own_projects_for(client_uid)
    kb = InlineKeyboardMarkup(row_width=2)
    items = []
    for pid, p in projects.items():
        status = "🟢" if is_running(pid) else "🔴"
        items.append(InlineKeyboardButton(f"{status} {p['name']}", callback_data=cb("proj", pid)))
    for i in range(0, len(items), 2):
        kb.row(*items[i:i+2])
    kb.add(InlineKeyboardButton("🔙 Clients", callback_data="clients_list"))
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
        default = {"gemini_api_key": "AQ.Ab8RN6KGJCEmuXDv20FBDly161Lh7tyLlbnUo67GP7aCn1Jejw", "model": "gemini-2.5-flash"}
        with open(AI_SETTINGS_FILE, "w") as f:
            json.dump(default, f, indent=2)
        return default
    with open(AI_SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_ai_settings(settings):
    with open(AI_SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def ask_ai(prompt):
    try:
        import requests as req
        cfg = load_ai_settings()
        api_key = cfg.get("gemini_api_key", "")
        if not api_key:
            return "❌ AI API Key সেট করা নেই। Admin Panel → AI Settings থেকে সেট করো।"
        model = cfg.get("model", "gemini-2.5-flash")
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
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
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
    projects = own_projects_for(uid)
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
    if not w or w["action"] not in ("upload_file", "universal_restore"):
        bot.send_message(uid, "ℹ️ Use Files menu → Upload File to upload.")
        return

    finfo = bot.get_file(msg.document.file_id)
    downloaded = bot.download_file(finfo.file_path)
    fname = msg.document.file_name

    # ── Universal restore (admin only) ──
    if w["action"] == "universal_restore":
        if not is_admin(uid):
            waiting.pop(uid, None)
            return
        if not fname.endswith(".zip"):
            bot.send_message(uid, "❌ শুধুমাত্র .zip ব্যাকআপ ফাইল পাঠাও।")
            return
        tmp_zip = os.path.join(BASE_DIR, f"_restore_{secrets.token_hex(4)}.zip")
        with open(tmp_zip, "wb") as f:
            f.write(downloaded)
        try:
            # সব চলমান বট বন্ধ করো (ফাইল ওভাররাইট হবে বলে)
            for pid in list(processes.keys()):
                stop_bot(pid)
            with zipfile.ZipFile(tmp_zip, "r") as z:
                z.extractall(BASE_DIR)
            bot.send_message(uid, "✅ <b>Universal Restore সম্পন্ন!</b>\n\nসব প্রজেক্ট restore হয়ে গেছে।", reply_markup=admin_kb())
        except Exception as e:
            bot.send_message(uid, f"❌ Restore failed: {e}")
        finally:
            if os.path.exists(tmp_zip):
                os.remove(tmp_zip)
        waiting.pop(uid, None)
        return

    # ── Normal project file upload ──
    pid = w["data"]["pid"]
    subpath = w["data"].get("subpath", "")
    proj_dir = os.path.join(PROJECTS_DIR, pid)
    target_dir = os.path.join(proj_dir, subpath) if subpath else proj_dir
    os.makedirs(target_dir, exist_ok=True)

    fpath = os.path.join(target_dir, fname)
    with open(fpath, "wb") as f:
        f.write(downloaded)

    if fname.endswith(".zip"):
        try:
            with zipfile.ZipFile(fpath, "r") as z:
                z.extractall(target_dir)
            os.remove(fpath)
            auto_normalize_main_file(pid)
            bot.send_message(uid, f"✅ <b>{fname}</b> extracted!", reply_markup=back_files_kb(pid, subpath))
        except Exception as e:
            bot.send_message(uid, f"❌ ZIP extract failed: {e}", reply_markup=back_files_kb(pid, subpath))
    else:
        auto_normalize_main_file(pid)
        bot.send_message(uid, f"✅ <b>{fname}</b> uploaded ({fmt_size(len(downloaded))})", reply_markup=back_files_kb(pid, subpath))

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
            display_name = str(new_uid)
            try:
                chat = bot.get_chat(new_uid)
                display_name = chat.username or chat.first_name or str(new_uid)
            except Exception:
                pass
            data = load()
            data["users"][str(new_uid)] = {
                "added_by": str(uid), "added": datetime.now().isoformat(),
                "display_name": display_name, "max_bots": 0
            }
            save(data)
            waiting[uid] = {"action": "add_user_limit", "data": {"new_uid": new_uid}}
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("♾ Unlimited (0)", callback_data="skip_userlimit"))
            bot.send_message(uid,
                f"👤 User <code>{new_uid}</code> ({display_name}) authorized.\n\n"
                f"🔢 সে সর্বোচ্চ কয়টা বট চালাতে পারবে? (সংখ্যা পাঠাও, 0 = unlimited):",
                reply_markup=kb
            )
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

    elif action == "rename_file":
        pid = w["data"]["pid"]
        old_fname = w["data"]["fname"]
        proj_dir = os.path.join(PROJECTS_DIR, pid)
        old_path = os.path.join(proj_dir, old_fname)
        # নতুন নাম, কিন্তু ফোল্ডার (parent path) আগেরটাই থাকবে
        parent = os.path.dirname(old_fname)
        new_name_only = os.path.basename(text.strip())
        new_fname = f"{parent}/{new_name_only}" if parent else new_name_only
        new_path = os.path.join(proj_dir, new_fname)
        if not os.path.exists(old_path):
            bot.send_message(uid, "❌ Original file পাওয়া যায়নি।")
            waiting.pop(uid, None)
            return
        try:
            os.rename(old_path, new_path)
            # যদি এইটা main_file ছিল, তাহলে data.json এ ও নাম আপডেট করো
            data = load()
            proj = data["projects"].get(pid, {})
            if proj.get("main_file") == old_fname:
                proj["main_file"] = new_fname
                save(data)
            waiting.pop(uid, None)
            bot.send_message(uid, f"✅ <b>{old_fname}</b> → <b>{new_fname}</b> renamed!",
                              reply_markup=back_files_kb(pid, parent))
        except Exception as e:
            bot.send_message(uid, f"❌ Rename failed: {e}")

    elif action == "add_user_limit":
        pid_data = w["data"]
        try:
            limit = int(text.strip())
        except ValueError:
            bot.send_message(uid, "❌ শুধু সংখ্যা পাঠাও (0 = unlimited)।")
            return
        data = load()
        new_uid = pid_data["new_uid"]
        data["users"][str(new_uid)]["max_bots"] = limit
        save(data)
        waiting.pop(uid, None)
        limit_txt = "Unlimited" if limit <= 0 else str(limit)
        bot.send_message(uid, f"✅ User <code>{new_uid}</code> added! Max bots: <b>{limit_txt}</b>",
                          reply_markup=admin_kb())

    elif action == "edit_user_limit":
        target = w["data"]["target"]
        try:
            limit = int(text.strip())
        except ValueError:
            bot.send_message(uid, "❌ শুধু সংখ্যা পাঠাও (0 = unlimited)।")
            return
        data = load()
        if target in data.get("users", {}):
            data["users"][target]["max_bots"] = limit
            save(data)
        waiting.pop(uid, None)
        limit_txt = "Unlimited" if limit <= 0 else str(limit)
        bot.send_message(uid, f"✅ <code>{target}</code> এর limit: <b>{limit_txt}</b>", reply_markup=admin_kb())

    elif action == "set_client_expiry":
        target = w["data"]["target"]
        dt = parse_expiry(text)
        if not dt:
            bot.send_message(uid, "❌ ফরম্যাট ভুল। YYYY-MM-DD ফরম্যাটে পাঠাও, যেমন: 2026-12-31")
            return
        data = load()
        if target in data.get("users", {}):
            data["users"][target]["expiry_date"] = text.strip()
            data["users"][target]["expired_notified"] = False
            save(data)
        waiting.pop(uid, None)
        bot.send_message(
            uid,
            f"✅ <code>{target}</code> এর এক্সপায়ারি সেট হয়েছে: <b>{text.strip()}</b>\n"
            f"এই তারিখের পর বট অটোমেটিক স্টপ হয়ে যাবে (ফাইল ডিলিট হবে না)।",
            reply_markup=admin_kb()
        )

    elif action == "set_backup_interval":
        try:
            mins = int(text.strip())
            if mins < 1:
                raise ValueError()
        except ValueError:
            bot.send_message(uid, "❌ শুধু positive সংখ্যা (মিনিট) পাঠাও।")
            return
        s = load_backup_settings()
        s["interval_minutes"] = mins
        s["enabled"] = True
        save_backup_settings(s)
        waiting.pop(uid, None)
        bot.send_message(uid, f"✅ Auto backup timer: প্রতি <b>{mins}</b> মিনিটে চালু হয়েছে।",
                          reply_markup=admin_kb())

def _project_limit_reached(uid):
    """Non-admin ইউজারের max_bots limit চেক করো। Returns (reached: bool, limit: int)"""
    if is_admin(uid):
        return False, 0
    data = load()
    user_info = data.get("users", {}).get(str(uid), {})
    limit = user_info.get("max_bots", 0)
    if limit and limit > 0:
        current = len(own_projects(uid))
        return current >= limit, limit
    return False, 0

def _create_project(uid, d, tags):
    reached, limit = _project_limit_reached(uid)
    if reached:
        bot.send_message(uid, f"⛔ তুমি সর্বোচ্চ <b>{limit}</b> টা বট তৈরি করতে পারবে। Limit শেষ।")
        waiting.pop(uid, None)
        return
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
        projects = own_projects_for(uid)
        running_count = sum(1 for pid in projects if is_running(pid))
        safe_edit(call,
            f"👋 <b>{name}</b> — BotManager Menu\n"
            f"📋 Projects: <b>{len(projects)}</b> | 🟢 Running: <b>{running_count}</b>",
            reply_markup=main_menu_kb(uid)
        )

    # ── List projects ──
    elif d == "list_projects":
        projects = own_projects_for(uid)
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

    # ── Files list (recursive folder browser) ──
    elif d.startswith("files" + SEP):
        parts = cb_parse(d, "files", 2)
        if not parts: return
        pid, relpath = parts
        proj_dir = os.path.join(PROJECTS_DIR, pid)
        os.makedirs(proj_dir, exist_ok=True)
        entries = list_dir_entries(proj_dir, relpath)
        data = load()
        proj = data["projects"].get(pid, {})
        loc = f" / {relpath}" if relpath else ""
        text = (f"📁 <b>{proj.get('name','?')}</b>{loc} — {len(entries)} item(s)" if entries
                else f"📁 <b>{proj.get('name','?')}</b>{loc} — No files yet")
        safe_edit(call, text, reply_markup=files_kb(pid, relpath, entries))

    # ── Upload prompt ──
    elif d.startswith("upload" + SEP):
        parts = cb_parse(d, "upload", 2)
        if not parts: return
        pid, relpath = parts
        waiting[uid] = {"action": "upload_file", "data": {"pid": pid, "subpath": relpath}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data=cb("files", pid, relpath)))
        loc = f" (📂 {relpath})" if relpath else ""
        safe_edit(call,
            f"📤 Send the file now{loc} (bot.py, .env, requirements.txt, .zip...)\n\n"
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
                bot.send_document(uid, f, visible_file_name=os.path.basename(fname),
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

    # ── Rename file ──
    elif d.startswith("renamefile" + SEP):
        parts = cb_parse(d, "renamefile", 2)
        if not parts: return
        pid, fname = parts
        waiting[uid] = {"action": "rename_file", "data": {"pid": pid, "fname": fname}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data=cb("file", pid, fname)))
        safe_edit(call,
            f"✏️ <b>{fname}</b> এর নতুন নাম পাঠাও:\n\n"
            "<i>(শুধু ফাইলের নাম, ফোল্ডারের ভিতরেই থাকবে)</i>",
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
        parent = os.path.dirname(fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            proj_dir = os.path.join(PROJECTS_DIR, pid)
            entries = list_dir_entries(proj_dir, parent)
            safe_edit(call, f"🗑 <b>{fname}</b> deleted.", reply_markup=files_kb(pid, parent, entries))
        else:
            safe_edit(call, f"❌ File not found.", reply_markup=back_files_kb(pid, parent))

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
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("📁 Upload Files", callback_data=cb("upload", pid, "")),
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
            lines = []
            for u_id, info in users.items():
                limit = info.get("max_bots", 0)
                limit_txt = "♾" if not limit or limit <= 0 else str(limit)
                name = info.get("display_name", u_id)
                proj_count = len(own_projects_for(u_id))
                exp = info.get("expiry_date")
                if not exp:
                    exp_txt = "♾ কোনো মেয়াদ নেই"
                elif is_user_expired(u_id):
                    exp_txt = f"⛔ Expired ({exp})"
                else:
                    exp_txt = f"⏳ {exp}"
                lines.append(f"• <code>{u_id}</code> ({name}) — added {info.get('added','')[:10]} — bots: {proj_count}/{limit_txt} — {exp_txt}")
            text = "👥 <b>Authorized Users:</b>\n\n" + "\n".join(lines)
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("➕ Add User", callback_data="admin_adduser"),
            InlineKeyboardButton("🗑 Remove User", callback_data="admin_removeuser"),
            InlineKeyboardButton("✏️ Edit Limit", callback_data="admin_editlimit"),
            InlineKeyboardButton("⏳ Set Expiry", callback_data="admin_setexpiry"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        )
        safe_edit(call, text, reply_markup=kb)

    elif d == "admin_editlimit":
        if not is_admin(uid): return
        data = load()
        users = data.get("users", {})
        if not users:
            bot.answer_callback_query(call.id, "No users to edit")
            return
        kb = InlineKeyboardMarkup(row_width=1)
        for u_id, info in users.items():
            name = info.get("display_name", u_id)
            kb.add(InlineKeyboardButton(f"✏️ {name} ({u_id})", callback_data=cb("editlimit", u_id)))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data="admin_users"))
        safe_edit(call, "Select user to edit limit:", reply_markup=kb)

    elif d.startswith("editlimit" + SEP):
        if not is_admin(uid): return
        parts = cb_parse(d, "editlimit", 1)
        if not parts: return
        target = parts[0]
        waiting[uid] = {"action": "edit_user_limit", "data": {"target": target}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="admin_users"))
        safe_edit(call, f"🔢 <code>{target}</code> এর নতুন max bots limit পাঠাও (0 = unlimited):", reply_markup=kb)

    elif d == "admin_setexpiry":
        if not is_admin(uid): return
        data = load()
        users = data.get("users", {})
        if not users:
            bot.answer_callback_query(call.id, "No users to edit")
            return
        kb = InlineKeyboardMarkup(row_width=1)
        for u_id, info in users.items():
            name = info.get("display_name", u_id)
            exp = info.get("expiry_date") or "কোনো মেয়াদ নেই"
            kb.add(InlineKeyboardButton(f"⏳ {name} ({u_id}) — {exp}", callback_data=cb("setexpiry", u_id)))
        kb.add(InlineKeyboardButton("🔙 Back", callback_data="admin_users"))
        safe_edit(call, "কোন ক্লায়েন্টের এক্সপায়ারি সেট/পরিবর্তন করবে?", reply_markup=kb)

    elif d.startswith("setexpiry" + SEP):
        if not is_admin(uid): return
        parts = cb_parse(d, "setexpiry", 1)
        if not parts: return
        target = parts[0]
        waiting[uid] = {"action": "set_client_expiry", "data": {"target": target}}
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("♾ মেয়াদ তুলে দাও (No expiry)", callback_data=cb("clearexpiry", target)),
            InlineKeyboardButton("❌ Cancel", callback_data="admin_setexpiry")
        )
        safe_edit(call,
            f"📅 <code>{target}</code> এর জন্য এক্সপায়ারি ডেট পাঠাও, ফরম্যাট: <code>YYYY-MM-DD</code>\n"
            f"(উদাহরণ: 2026-12-31)\n\n"
            f"এই তারিখের পর বটটা শুধু <b>স্টপ</b> হয়ে যাবে — ফাইল কখনো ডিলিট হবে না।",
            reply_markup=kb
        )

    elif d.startswith("clearexpiry" + SEP):
        if not is_admin(uid): return
        parts = cb_parse(d, "clearexpiry", 1)
        if not parts: return
        target = parts[0]
        data = load()
        if target in data.get("users", {}):
            data["users"][target]["expiry_date"] = ""
            data["users"][target]["expired_notified"] = False
            save(data)
        waiting.pop(uid, None)
        safe_edit(call, f"✅ <code>{target}</code> এর কোনো এক্সপায়ারি নেই এখন (unlimited access)।", reply_markup=admin_kb())

    # ── Clients section ──
    elif d == "clients_list":
        if not is_admin(uid): return
        data = load()
        users = data.get("users", {})
        if not users:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel"))
            safe_edit(call, "👨‍👩‍👧 কোনো ক্লায়েন্ট এখনো নেই।", reply_markup=kb)
            return
        safe_edit(call, "👨‍👩‍👧 <b>Clients</b>\n\nক্লায়েন্ট সিলেক্ট করো তার প্রজেক্ট দেখতে:", reply_markup=client_list_kb())

    elif d.startswith("clientprojects" + SEP):
        if not is_admin(uid): return
        parts = cb_parse(d, "clientprojects", 1)
        if not parts: return
        client_uid = parts[0]
        data = load()
        info = data.get("users", {}).get(client_uid, {})
        name = info.get("display_name", client_uid)
        projects = own_projects_for(client_uid)
        if not projects:
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🔙 Clients", callback_data="clients_list"))
            safe_edit(call, f"📋 <b>{name}</b> এর কোনো প্রজেক্ট নেই।", reply_markup=kb)
            return
        safe_edit(call, f"📋 <b>{name}</b> — {len(projects)} project(s):", reply_markup=client_project_list_kb(client_uid))

    # ── Universal Backup / Restore ──
    elif d == "universal_backup":
        if not is_admin(uid): return
        safe_edit(call, "⏳ সব প্রজেক্ট ব্যাকআপ হচ্ছে...")
        zip_path = None
        try:
            zip_path = create_universal_backup()
            with open(zip_path, "rb") as f:
                bot.send_document(uid, f, visible_file_name=os.path.basename(zip_path),
                                   caption="🗄 <b>Universal Backup</b> — সব প্রজেক্ট একসাথে")
        except Exception as e:
            bot.send_message(uid, f"❌ Backup failed: {e}")
        finally:
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
        safe_edit(call, "👑 <b>Admin Panel</b>", reply_markup=admin_kb())

    elif d == "universal_restore_prompt":
        if not is_admin(uid): return
        waiting[uid] = {"action": "universal_restore", "data": {}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="admin_panel"))
        safe_edit(call,
            "♻️ <b>Universal Restore</b>\n\n"
            "⚠️ Universal Backup থেকে পাওয়া .zip ফাইলটা এখন পাঠাও।\n"
            "সব প্রজেক্ট বর্তমান অবস্থা থেকে ওভাররাইট হয়ে যাবে!",
            reply_markup=kb
        )

    elif d == "backup_timer_settings":
        if not is_admin(uid): return
        s = load_backup_settings()
        enabled = s.get("enabled", False)
        mins = s.get("interval_minutes", 30)
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("⏱ Interval পরিবর্তন করো", callback_data="set_backup_interval"),
            InlineKeyboardButton(f"{'⏸ Timer বন্ধ করো' if enabled else '▶️ Timer চালু করো'}", callback_data="toggle_backup_timer"),
            InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
        )
        safe_edit(call,
            f"⏱ <b>Auto Backup Timer</b>\n{'─'*28}\n"
            f"স্ট্যাটাস: {'✅ ON' if enabled else '❌ OFF'}\n"
            f"ইন্টারভাল: প্রতি <b>{mins}</b> মিনিটে\n\n"
            f"চালু থাকলে প্রতি {mins} মিনিট পর পর সব প্রজেক্টের ব্যাকআপ zip Admin-দের কাছে পাঠানো হবে।",
            reply_markup=kb
        )

    elif d == "set_backup_interval":
        if not is_admin(uid): return
        waiting[uid] = {"action": "set_backup_interval", "data": {}}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("❌ Cancel", callback_data="backup_timer_settings"))
        safe_edit(call, "⏱ কত মিনিট পর পর auto backup পাঠাবে? (সংখ্যা পাঠাও, e.g. 30):", reply_markup=kb)

    elif d == "toggle_backup_timer":
        if not is_admin(uid): return
        s = load_backup_settings()
        s["enabled"] = not s.get("enabled", False)
        save_backup_settings(s)
        safe_edit(call, f"⏱ Timer: {'✅ ON' if s['enabled'] else '❌ OFF'}", reply_markup=None)
        # ছোট delay দিয়ে আবার settings screen দেখাও
        enabled = s.get("enabled", False)
        mins = s.get("interval_minutes", 30)
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("⏱ Interval পরিবর্তন করো", callback_data="set_backup_interval"),
            InlineKeyboardButton(f"{'⏸ Timer বন্ধ করো' if enabled else '▶️ Timer চালু করো'}", callback_data="toggle_backup_timer"),
            InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
        )
        safe_edit(call,
            f"⏱ <b>Auto Backup Timer</b>\n{'─'*28}\n"
            f"স্ট্যাটাস: {'✅ ON' if enabled else '❌ OFF'}\n"
            f"ইন্টারভাল: প্রতি <b>{mins}</b> মিনিটে",
            reply_markup=kb
        )

    elif d == "skip_userlimit":
        w = waiting.get(uid, {})
        if w.get("action") != "add_user_limit":
            return
        new_uid = w["data"]["new_uid"]
        data = load()
        if str(new_uid) in data.get("users", {}):
            data["users"][str(new_uid)]["max_bots"] = 0
            save(data)
        waiting.pop(uid, None)
        safe_edit(call, f"✅ User <code>{new_uid}</code> added! Max bots: <b>Unlimited</b>", reply_markup=admin_kb())

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
        model = cfg.get("model", "gemini-2.5-flash")
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
            "6️⃣ <b>Files → View/Edit/Rename</b> — সরাসরি file edit বা rename করো\n"
            "7️⃣ <b>Files → 📂 Folder</b> — ফোল্ডারে ক্লিক করে ভিতরে ঢোকো\n\n"
            "📦 ZIP upload করলে auto-extract হবে\n"
            "🐍 একটাই .py ফাইল থাকলে auto bot.py তে convert হবে\n"
            "🔄 Auto-restart — Settings এ on/off করো\n"
            "📥 Download ZIP — একটা প্রজেক্টের backup নাও\n"
            "🗄 Universal Backup — Admin: সব প্রজেক্ট একসাথে backup\n"
            "♻️ Universal Restore — Admin: সব প্রজেক্ট একসাথে restore\n"
            "⏱ Auto Backup Timer — Admin: নির্দিষ্ট সময় পর পর auto backup\n"
            "👨‍👩‍👧 Clients — Admin: প্রতি ক্লায়েন্টের প্রজেক্ট আলাদা সেকশনে\n"
            "📢 Broadcast — Admin: সব user কে message পাঠাও"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Menu", callback_data="main_menu"))
        safe_edit(call, text, reply_markup=kb)

# ─── RUN ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 BotManager starting...")
    print(f"Admin IDs: {ADMIN_IDS}")
    # Universal auto-backup timer thread
    threading.Thread(target=auto_backup_worker, daemon=True).start()
    # Client expiry checker thread
    threading.Thread(target=expiry_checker_worker, daemon=True).start()
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
