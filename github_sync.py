"""
GitHub Real-Time Sync Module
============================
যেকোনো ফাইল change হলে automatically GitHub-এ push করে।
Background queue-তে চলে — বট slow হয় না।
"""

import os
import base64
import json
import time
import threading
import queue
import logging
from datetime import datetime

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "-q", "--break-system-packages"])
    import requests

logger = logging.getLogger(__name__)

# ─── CONFIG (bot.py থেকে set হবে) ────────────────────────────────
GITHUB_TOKEN = ""
GITHUB_OWNER = "sultanmahamud26"
GITHUB_REPO  = "Motion_Host"
GITHUB_BRANCH = "main"

# এই ফাইলগুলো sync করবে না
IGNORE_PATTERNS = {
    ".tmp",             # temp files
    "__pycache__",
    ".pyc",
    ".log",
}

# ─── INTERNAL STATE ───────────────────────────────────────────────
_sync_queue = queue.Queue()
_sha_cache = {}          # path → sha (GitHub-এর current sha)
_lock = threading.RLock()
_initialized = False

# ─── GITHUB API ───────────────────────────────────────────────────
def _headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def _api(path):
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"

def _get_sha(repo_path):
    """GitHub-এ ফাইলটার current SHA নেওয়া (update করতে লাগে)"""
    with _lock:
        if repo_path in _sha_cache:
            return _sha_cache[repo_path]
    try:
        r = requests.get(_api(repo_path), headers=_headers(), timeout=15)
        if r.status_code == 200:
            sha = r.json().get("sha", "")
            with _lock:
                _sha_cache[repo_path] = sha
            return sha
    except Exception:
        pass
    return None

def _push_file(local_path, repo_path):
    """একটা ফাইল GitHub-এ push করা"""
    try:
        if not os.path.exists(local_path):
            # ফাইল নেই — delete করতে হবে
            return _delete_file(repo_path)

        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()

        sha = _get_sha(repo_path)
        payload = {
            "message": f"🔄 Auto-sync: {repo_path} [{datetime.now().strftime('%H:%M:%S')}]",
            "content": content,
            "branch": GITHUB_BRANCH
        }
        if sha:
            payload["sha"] = sha

        r = requests.put(_api(repo_path), headers=_headers(), json=payload, timeout=30)

        if r.status_code in (200, 201):
            new_sha = r.json().get("content", {}).get("sha", "")
            with _lock:
                _sha_cache[repo_path] = new_sha
            logger.info(f"✅ Synced: {repo_path}")
            return True
        else:
            logger.warning(f"⚠️ Sync failed {repo_path}: {r.status_code} {r.text[:200]}")
            return False

    except Exception as e:
        logger.error(f"❌ Push error {repo_path}: {e}")
        return False

def _delete_file(repo_path):
    """GitHub থেকে ফাইল delete করা"""
    try:
        sha = _get_sha(repo_path)
        if not sha:
            return True  # already deleted
        payload = {
            "message": f"🗑 Auto-sync delete: {repo_path}",
            "sha": sha,
            "branch": GITHUB_BRANCH
        }
        r = requests.delete(_api(repo_path), headers=_headers(), json=payload, timeout=15)
        if r.status_code == 200:
            with _lock:
                _sha_cache.pop(repo_path, None)
            logger.info(f"🗑 Deleted from GitHub: {repo_path}")
            return True
    except Exception as e:
        logger.error(f"❌ Delete error {repo_path}: {e}")
    return False

# ─── IGNORE CHECK ─────────────────────────────────────────────────
def _should_ignore(local_path, base_dir):
    rel = os.path.relpath(local_path, base_dir)
    for pat in IGNORE_PATTERNS:
        if pat in rel:
            return True
    return False

def _to_repo_path(local_path, base_dir):
    """Local path → GitHub repo path"""
    rel = os.path.relpath(local_path, base_dir)
    # Windows path separator fix
    return rel.replace("\\", "/")

# ─── QUEUE WORKER ─────────────────────────────────────────────────
def _worker(base_dir):
    """Background thread — queue থেকে sync tasks process করে"""
    # Debounce: একই ফাইলে rapid changes একসাথে করার জন্য
    pending = {}  # path → (local_path, repo_path, timestamp)
    DEBOUNCE = 2.0  # seconds

    while True:
        try:
            # নতুন items নাও
            try:
                item = _sync_queue.get(timeout=0.5)
                local_path, repo_path = item
                pending[repo_path] = (local_path, repo_path, time.time())
                _sync_queue.task_done()
            except queue.Empty:
                pass

            # Debounce check — 2 সেকেন্ড পুরনো items push করো
            now = time.time()
            ready = {rp: v for rp, v in pending.items() if now - v[2] >= DEBOUNCE}
            for rp, (lp, rpath, _) in ready.items():
                _push_file(lp, rpath)
                del pending[rp]

        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(1)

# ─── PUBLIC API ───────────────────────────────────────────────────
def setup(token, base_dir, owner="sultanmahamud26", repo="Motion_Host", branch="main"):
    """
    bot.py থেকে এটা call করো:
    
    import github_sync
    github_sync.setup(
        token="github_pat_...",
        base_dir=BASE_DIR
    )
    """
    global GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH, _initialized

    GITHUB_TOKEN = token
    GITHUB_OWNER = owner
    GITHUB_REPO  = repo
    GITHUB_BRANCH = branch

    if _initialized:
        return

    # Worker thread start
    t = threading.Thread(target=_worker, args=(base_dir,), daemon=True)
    t.start()

    # Startup sync — সব existing files একবার push করো
    threading.Thread(target=_initial_sync, args=(base_dir,), daemon=True).start()

    _initialized = True
    logger.info(f"🚀 GitHub Sync started → {owner}/{repo}")

def sync_file(local_path, base_dir):
    """
    যেকোনো ফাইল change হলে এটা call করো।
    Non-blocking — queue-তে add করে return করে।
    """
    if not GITHUB_TOKEN:
        return
    if _should_ignore(local_path, base_dir):
        return
    repo_path = _to_repo_path(local_path, base_dir)
    _sync_queue.put((local_path, repo_path))

def sync_delete(local_path, base_dir):
    """ফাইল delete হলে GitHub থেকেও delete করো"""
    if not GITHUB_TOKEN:
        return
    if _should_ignore(local_path, base_dir):
        return
    repo_path = _to_repo_path(local_path, base_dir)
    # Immediately delete (debounce না)
    threading.Thread(target=_delete_file, args=(repo_path,), daemon=True).start()

def sync_dir(dir_path, base_dir):
    """একটা পুরো directory sync করো"""
    if not os.path.exists(dir_path):
        return
    for root, dirs, files in os.walk(dir_path):
        # __pycache__ skip
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fname in files:
            fpath = os.path.join(root, fname)
            sync_file(fpath, base_dir)

def _initial_sync(base_dir):
    """Startup-এ সব files একবার sync করো"""
    time.sleep(3)  # বট fully start হতে দাও
    logger.info("📤 Initial sync শুরু হচ্ছে...")

    synced = 0
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fname in files:
            fpath = os.path.join(root, fname)
            if not _should_ignore(fpath, base_dir):
                repo_path = _to_repo_path(fpath, base_dir)
                _sync_queue.put((fpath, repo_path))
                synced += 1

    logger.info(f"📤 Initial sync: {synced} files queued")
