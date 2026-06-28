"""
GitHub Real-Time Sync Module
============================
যেকোনো ফাইল change হলে automatically GitHub-এ push করে।
Background queue-তে চলে — বট slow হয় না।

v2 আপডেট:
- পুরো BASE_DIR এখন একটা filesystem watcher (watchdog) দিয়ে monitor হয়।
  মানে মাদারবট নিজে sync_file() call করুক বা না করুক — child bot
  subprocess যেকোনো ফাইল লিখলে/বদলালে/ডিলিট করলে, সেটা automatic ধরা পড়ে
  এবং GitHub-এ push হয়। কোনো ম্যানুয়াল sync কল আর লাগবে না (থাকলেও
  ক্ষতি নেই, duplicate হলেও debounce handle করে নেয়)।
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

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "watchdog", "-q", "--break-system-packages"])
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
    ".venv",            # virtual environment — বিশাল, দরকার নেই
    "venv",
    ".git",
    "-journal",         # sqlite -wal/-journal/-shm churn ফাইল (db.sqlite3-journal)
    ".db-journal",
    ".db-wal",
    ".db-shm",
    ".swp",             # editor swap files
    "node_modules",
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
        # ref=GITHUB_BRANCH না দিলে এটা repo-র default branch চেক করে,
        # যা GITHUB_BRANCH থেকে আলাদা হতে পারে — সেই bug fix করা হলো।
        r = requests.get(
            _api(repo_path), headers=_headers(),
            params={"ref": GITHUB_BRANCH}, timeout=15
        )
        if r.status_code == 200:
            sha = r.json().get("sha", "")
            with _lock:
                _sha_cache[repo_path] = sha
            return sha
        elif r.status_code != 404:
            logger.warning(f"⚠️ SHA lookup failed {repo_path}: {r.status_code} {r.text[:150]}")
    except Exception as e:
        logger.error(f"❌ SHA lookup error {repo_path}: {e}")
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

# ─── FILESYSTEM WATCHER (NEW) ─────────────────────────────────────
# এটাই মূল ফিক্স: পুরো BASE_DIR recursively watch করে — মাদারবট নিজে
# sync_file() call করুক বা না করুক। child bot subprocess (যেমন
# projects/<pid>/bot.py যখন রান করে) নিজে যেকোনো ফাইল লিখলে/বদলালে/
# মুছলে, এই watcher সেটা automatically ধরে এবং queue-তে ফেলে দেয়।
_delete_queue = queue.Queue()

class _SyncEventHandler(FileSystemEventHandler):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir

    def _accept(self, path):
        if not path or os.path.isdir(path):
            return False
        if _should_ignore(path, self.base_dir):
            return False
        return True

    def on_created(self, event):
        if not event.is_directory and self._accept(event.src_path):
            repo_path = _to_repo_path(event.src_path, self.base_dir)
            _sync_queue.put((event.src_path, repo_path))

    def on_modified(self, event):
        if not event.is_directory and self._accept(event.src_path):
            repo_path = _to_repo_path(event.src_path, self.base_dir)
            _sync_queue.put((event.src_path, repo_path))

    def on_deleted(self, event):
        if event.is_directory:
            return
        if _should_ignore(event.src_path, self.base_dir):
            return
        repo_path = _to_repo_path(event.src_path, self.base_dir)
        _delete_queue.put(repo_path)

    def on_moved(self, event):
        # rename/move = পুরোনো path delete + নতুন path create
        if not event.is_directory:
            if self._accept(event.src_path):
                old_repo_path = _to_repo_path(event.src_path, self.base_dir)
                _delete_queue.put(old_repo_path)
            if self._accept(event.dest_path):
                new_repo_path = _to_repo_path(event.dest_path, self.base_dir)
                _sync_queue.put((event.dest_path, new_repo_path))

_observer = None

def _start_watcher(base_dir):
    """পুরো base_dir-এর উপর recursive watchdog observer চালু করো।"""
    global _observer
    if _observer is not None:
        return
    handler = _SyncEventHandler(base_dir)
    _observer = Observer()
    _observer.schedule(handler, base_dir, recursive=True)
    _observer.start()
    logger.info(f"👁️ Filesystem watcher চালু হলো → {base_dir} (recursive, সব subprocess/child bot সহ)")

def _delete_worker():
    """Background thread — delete events process করে (debounce ছাড়াই, দ্রুত)"""
    while True:
        try:
            repo_path = _delete_queue.get(timeout=1.0)
            _delete_file(repo_path)
            _delete_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Delete worker error: {e}")
            time.sleep(1)

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
                if not GITHUB_TOKEN:
                    logger.warning(f"⚠️ GITHUB_TOKEN খালি — sync skip: {rpath}")
                else:
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

    এটা পুরো base_dir-কে recursively watch করা শুরু করে — সাব-ফোল্ডারে
    child bot subprocess যা-ই লিখুক/বদলাক/মুছুক, automatic sync হবে।
    আগের মতো sync_file()/sync_dir()/sync_delete() ম্যানুয়াল কলও কাজ
    করবে (duplicate event হলেও debounce নিজেই handle করে নেয়), কিন্তু
    আর বাধ্যতামূলক না।
    """
    global GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH, _initialized

    GITHUB_TOKEN = token
    GITHUB_OWNER = owner
    GITHUB_REPO  = repo
    GITHUB_BRANCH = branch

    if not GITHUB_TOKEN:
        logger.warning("⚠️ GITHUB_TOKEN খালি/সেট করা নেই — sync কাজ করবে না, কোনো push হবে না!")

    if _initialized:
        return

    # Worker threads start
    threading.Thread(target=_worker, args=(base_dir,), daemon=True).start()
    threading.Thread(target=_delete_worker, daemon=True).start()

    # Filesystem watcher start — পুরো base_dir recursively
    _start_watcher(base_dir)

    # Startup sync — সব existing files একবার push করো
    threading.Thread(target=_initial_sync, args=(base_dir,), daemon=True).start()

    _initialized = True
    logger.info(f"🚀 GitHub Sync started → {owner}/{repo} (branch: {branch})")

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
