import os, json, time, threading, urllib.request, urllib.error, base64, uuid, queue, shutil, random, socket, ssl, sqlite3
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app, session, url_for
from flask_login import current_user, login_required
from app import get_db

bp = Blueprint("api", __name__)

_concurrent_lock = threading.Lock()
_concurrent_count = {"text": 0}
_image_worker_threads = []
_image_worker_lock = threading.RLock()
_image_worker_apps = set()
_image_worker_started = False
_IMAGE_USER_AGENT = "PSM-Teaching-Site/1.0"
_IMAGE_DOWNLOAD_TIMEOUT = 20

FALLBACK_TEXT = [
    "AI小助手暂时休息了，试试自己想一个答案吧！",
    "网络有点慢，先和旁边同学讨论一下？",
    "AI正在思考中...不如先画画你的想法？",
]

# Fine-grained tag mapping: specific animal/object → tag
# Order matters: more specific matches checked first
_SPECIFIC_TAG_MAP = {
    "tiger": ["虎", "老虎", "tiger", "华南虎", "东北虎"],
    "cat": ["小猫", "猫", "猫咪", "kitten", "cat", "小猫咪"],
    "dog": ["小狗", "狗", "狗狗", "dog", "puppy"],
    "rabbit": ["兔", "兔子", "小兔", "rabbit", "bunny"],
    "panda": ["熊猫", "大熊猫", "panda"],
    "bird": ["鸟", "小鸟", "bird", "鸽子", "鹦鹉"],
    "fish": ["鱼", "小鱼", "金鱼", "fish"],
    "elephant": ["大象", "elephant"],
    "monkey": ["猴子", "monkey"],
    "lion": ["狮子", "lion"],
    "bear": ["熊", "小熊", "bear"],
    "horse": ["马", "小马", "horse"],
    "dinosaur": ["恐龙", "dinosaur", "龙"],
}

# Broad category tags
_BROAD_TAG_MAP = {
    "robot": ["机器人", "ai", "人工智能", "助手", "机甲"],
    "space": ["太空", "宇宙", "星球", "月球", "火箭", "飞船"],
    "animal": ["动物"],
    "landscape": ["风景", "森林", "海", "山", "城市", "校园", "天空"],
    "portrait": ["头像", "人物", "同学", "老师", "画家", "画像"],
    "story": ["故事", "冒险", "城堡", "魔法", "童话"],
}


def _prompt_tags(prompt):
    """Extract tags from prompt. Returns set of specific + broad tags."""
    text = (prompt or "").lower()
    tags = set()
    # Specific tags first
    for tag, words in _SPECIFIC_TAG_MAP.items():
        if any(w in text for w in words):
            tags.add(tag)
    # Broad tags
    for tag, words in _BROAD_TAG_MAP.items():
        if any(w in text for w in words):
            tags.add(tag)
    # If specific animal tags found, also add "animal" as parent
    specific_animals = {"tiger", "cat", "dog", "rabbit", "panda", "bird", "fish",
                        "elephant", "monkey", "lion", "bear", "horse", "dinosaur"}
    if tags & specific_animals:
        tags.add("animal")
    return tags


def _check_quota(student_id, lesson_id, api_type):
    db = get_db()
    row = db.execute(
        "SELECT used FROM quota_ledger WHERE student_id=? AND lesson_id=? AND api_type=?",
        (student_id, lesson_id, api_type),
    ).fetchone()
    used = row["used"] if row else 0
    limit_key = f"QUOTA_{api_type.upper()}_PER_LESSON"
    limit = current_app.config.get(limit_key, 10)
    return used < limit, used, limit


def _inc_quota(student_id, lesson_id, api_type):
    db = get_db()
    db.execute(
        "INSERT INTO quota_ledger(student_id, lesson_id, api_type, used) VALUES(?,?,?,1) "
        "ON CONFLICT(student_id, lesson_id, api_type) DO UPDATE SET used=used+1",
        (student_id, lesson_id, api_type),
    )
    db.commit()


def _urlopen_with_retries(req, timeout, attempts=None, total_timeout=None):
    """Open with finite retries and a wall-clock deadline; TLS verification stays on."""
    attempts = max(1, int(attempts or current_app.config.get("IMAGE_NETWORK_RETRIES", 2)))
    total_timeout = float(total_timeout or (float(timeout) * attempts + 1))
    deadline = time.monotonic() + total_timeout
    for attempt in range(attempts):
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("image request retry deadline exceeded")
            return urllib.request.urlopen(req, timeout=min(float(timeout), remaining))
        except (urllib.error.URLError, TimeoutError, socket.timeout, ssl.SSLError):
            if attempt + 1 >= attempts:
                raise
            delay = min(0.25 * (2 ** attempt), max(0, deadline - time.monotonic()))
            if delay <= 0:
                raise TimeoutError("image request retry deadline exceeded")
            time.sleep(delay)
    raise RuntimeError("network retry configuration invalid")


def _friendly_image_error(exc):
    if isinstance(exc, (urllib.error.URLError, TimeoutError, socket.timeout, ssl.SSLError)):
        return "图片服务暂时不可用"
    return "图片生成失败"


def _agnes_call(api_type, prompt, max_tokens=200):
    cfg = current_app.config
    key = cfg.get("AGNES_API_KEY", "")
    if not key:
        raise RuntimeError("AGNES_API_KEY未配置")
    base = cfg.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
    if api_type == "image":
        model = cfg.get("AGNES_IMAGE_MODEL", "agnes-image-2.1-flash")
        url = base.rstrip("/") + "/images/generations"
        data = json.dumps({"model": model, "prompt": prompt, "size": "1024x1024", "n": 1}).encode()
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": _IMAGE_USER_AGENT}
        req = urllib.request.Request(url, data=data, headers=headers)
        with _urlopen_with_retries(
            req,
            timeout=cfg.get("IMAGE_POST_TIMEOUT", 35),
            total_timeout=cfg.get("IMAGE_POST_TOTAL_TIMEOUT", 75),
        ) as r:
            body = json.loads(r.read().decode("utf-8", "ignore"))
        items = body.get("data", [])
        if items:
            d = items[0]
            if d.get("b64_json"):
                return "data:image/png;base64," + d["b64_json"]
            if d.get("url"):
                return d["url"]
        return ""
    model = cfg.get("AGNES_TEXT_MODEL", "agnes-2.0-flash")
    url = base.rstrip("/") + "/chat/completions"
    data = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}).encode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.loads(r.read().decode("utf-8", "ignore"))
    return body.get("choices", [{}])[0].get("message", {}).get("content", "")


def _student_lesson_save_dir(sid, lid):
    student_dir = f"student_{sid}"
    lesson_dir = f"lesson_{lid}" if lid else "lesson_0"
    rel_dir = f"uploads/{student_dir}/{lesson_dir}"
    save_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], student_dir, lesson_dir)
    os.makedirs(save_dir, exist_ok=True)
    return save_dir, rel_dir


def _save_image_bytes(img_bytes, sid, lid):
    save_dir, rel_dir = _student_lesson_save_dir(sid, lid)
    fname = f"{uuid.uuid4().hex}.png"
    abs_path = os.path.join(save_dir, fname)
    with open(abs_path, "wb") as f:
        f.write(img_bytes)
    static_path = current_app.static_url_path or "/static"
    return static_path.rstrip("/") + f"/{rel_dir}/{fname}", abs_path


def _content_to_bytes(content):
    if content and content.startswith("data:image"):
        return base64.b64decode(content.split(",", 1)[-1])
    if content and content.startswith("http"):
        req2 = urllib.request.Request(content, headers={"User-Agent": _IMAGE_USER_AGENT})
        cfg = current_app.config
        with _urlopen_with_retries(
            req2,
            timeout=cfg.get("IMAGE_DOWNLOAD_TIMEOUT", 20),
            total_timeout=cfg.get("IMAGE_DOWNLOAD_TOTAL_TIMEOUT", 45),
        ) as r2:
            return r2.read()
    return None


def _validate_image(img_bytes):
    """Check if image is valid: decodable, >64x64, not solid color.
    Returns (is_valid, reason)"""
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        if w < 64 or h < 64:
            return False, f"image too small: {w}x{h}"
        # Check color diversity: convert to RGB, sample pixels
        rgb = img.convert("RGB")
        # Resize to small thumbnail and check pixel variance
        thumb = rgb.resize((32, 32))
        pixels = list(thumb.getdata())
        if len(pixels) < 10:
            return False, "too few pixels"
        # Calculate per-channel variance
        r_vals = [p[0] for p in pixels]
        g_vals = [p[1] for p in pixels]
        b_vals = [p[2] for p in pixels]
        import statistics
        r_var = statistics.variance(r_vals) if len(r_vals) > 1 else 0
        g_var = statistics.variance(g_vals) if len(g_vals) > 1 else 0
        b_var = statistics.variance(b_vals) if len(b_vals) > 1 else 0
        avg_var = (r_var + g_var + b_var) / 3
        # Solid/near-solid images have very low variance
        if avg_var < 50:
            return False, f"solid/near-solid color, variance={avg_var:.1f}"
        return True, "ok"
    except ImportError:
        # PIL not available; skip validation but log warning
        try:
            import io
            from PIL import Image
        except ImportError:
            # No PIL at all — try basic size check via imghdr
            import struct
            # Check PNG header
            if img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
                # Parse IHDR for dimensions
                if len(img_bytes) > 24:
                    w = struct.unpack('>I', img_bytes[16:20])[0]
                    h = struct.unpack('>I', img_bytes[20:24])[0]
                    if w < 64 or h < 64:
                        return False, f"image too small: {w}x{h}"
            return True, "ok (no PIL, limited check)"
    except Exception as e:
        return False, f"validation error: {e}"


def _pool_manifest():
    p = Path(current_app.root_path) / "static" / "images" / "pool" / "manifest.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("images", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _pick_pool_image(prompt, lesson_id):
    """Pick pool image with STRICT tag matching.
    Rules:
    - Pool item must match lesson_id or be 'general'
    - Specific tags (e.g. tiger) in prompt require SAME specific tag in item
    - If prompt has specific animal 'tiger', item with only generic 'animal' does NOT match
    - Generic tags (e.g. landscape) can match directly
    Returns (item, matched_tags) or (None, set())
    """
    images = _pool_manifest()
    if not images:
        return None, set()
    prompt_tags = _prompt_tags(prompt)
    if not prompt_tags:
        return None, set()

    # Separate specific animal tags from broad tags
    specific_animals = {"tiger", "cat", "dog", "rabbit", "panda", "bird", "fish",
                        "elephant", "monkey", "lion", "bear", "horse", "dinosaur"}
    prompt_specific = prompt_tags & specific_animals
    prompt_broad = prompt_tags - specific_animals

    scored = []
    for item in images:
        # Lesson match: exact lesson_id or general
        item_lesson = item.get("lesson_id")
        lesson_match = item_lesson in (lesson_id, 0, "general")
        if not lesson_match:
            continue
        item_tags = set(item.get("tags", []))

        # If prompt has specific animal tags, item MUST have matching specific tag
        if prompt_specific:
            item_specific = item_tags & specific_animals
            if not (prompt_specific & item_specific):
                # Item has no specific animal tag matching prompt — reject
                continue

        # Score: specific matches worth more
        score = 0
        specific_overlap = prompt_specific & item_tags
        broad_overlap = prompt_broad & item_tags
        score += len(specific_overlap) * 5
        score += len(broad_overlap) * 2
        # Bonus for lesson-specific over general
        if item_lesson == lesson_id:
            score += 1

        if score > 0:
            scored.append((score, item, specific_overlap | broad_overlap))

    if not scored:
        return None, set()
    top = max(s for s, _, _ in scored)
    top_items = [(i, m) for s, i, m in scored if s == top]
    chosen, matched = random.choice(top_items)
    return chosen, matched


def _copy_pool_to_student(item, sid, lid):
    rel = item.get("file") or ""
    src = Path(current_app.root_path) / "static" / rel
    if not src.exists():
        return None
    save_dir, rel_dir = _student_lesson_save_dir(sid, lid)
    fname = f"pool_{uuid.uuid4().hex}{src.suffix or '.png'}"
    dst = Path(save_dir) / fname
    shutil.copyfile(src, dst)
    return current_app.static_url_path.rstrip("/") + f"/{rel_dir}/{fname}"


def _set_job(job_id, **kwargs):
    now = time.time()
    db = get_db()
    with _image_worker_lock:
        row = db.execute("SELECT job_id FROM image_job WHERE job_id=?", (job_id,)).fetchone()
        values = {key: value for key, value in kwargs.items() if key != "queue_size"}
        values["updated_at"] = now
        if "matched_tags" in values:
            values["matched_tags"] = json.dumps(values["matched_tags"], ensure_ascii=False)
        if row is None:
            values.setdefault("status", "queued")
            values.setdefault("progress", 0)
            values.setdefault("message", "")
            values.setdefault("source", "")
            values.setdefault("prompt_final", "")
            values.setdefault("image_url", "")
            values.setdefault("error", "")
            values.setdefault("abs_path", "")
            values.setdefault("matched_tags", "[]")
            values.setdefault("attempt_count", 0)
            values["job_id"] = job_id
            values.setdefault("created_at", now)
            fields = list(values)
            db.execute("INSERT INTO image_job (" + ",".join(fields) + ") VALUES (" + ",".join("?" for _ in fields) + ")", tuple(values[f] for f in fields))
        else:
            values.pop("created_at", None)
            fields = [f for f in values if f in {"student_id", "lesson_id", "prompt", "prompt_final", "status", "progress", "message", "source", "image_url", "error", "abs_path", "matched_tags", "attempt_count", "updated_at"}]
            db.execute("UPDATE image_job SET " + ",".join(f"{f}=?" for f in fields) + " WHERE job_id=?", tuple(values[f] for f in fields) + (job_id,))
        db.commit()
    return _get_job(job_id)


def _get_job(job_id):
    row = get_db().execute("SELECT * FROM image_job WHERE job_id=?", (job_id,)).fetchone()
    if not row:
        return {}
    result = dict(row)
    try:
        result["matched_tags"] = json.loads(result.get("matched_tags") or "[]")
    except (TypeError, json.JSONDecodeError):
        result["matched_tags"] = []
    return result


def _queued_image_count():
    return get_db().execute("SELECT COUNT(*) AS n FROM image_job WHERE status IN ('queued','running')").fetchone()["n"]


def _claim_next_image_job():
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    row = db.execute("SELECT job_id FROM image_job WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
    if not row:
        db.commit()
        return None
    job_id = row["job_id"]
    db.execute("UPDATE image_job SET status='running', progress=35, message=?, updated_at=? WHERE job_id=? AND status='queued'", ("正在画图，请稍等...", time.time(), job_id))
    db.commit()
    return job_id


def _recover_image_jobs():
    db = get_db()
    db.execute("UPDATE image_job SET status='queued', progress=10, message=?, updated_at=? WHERE status IN ('queued','running')", ("服务已恢复，重新排队中。", time.time()))
    db.commit()


def _lesson_level_from_id(lesson_id):
    """Return course level L1-L10 for a database lesson id."""
    try:
        lid = int(lesson_id)
    except (TypeError, ValueError):
        return 1
    try:
        from app.blueprints.student import parse_lesson_level
        db = get_db()
        row = db.execute("SELECT name FROM lesson WHERE id=?", (lid,)).fetchone()
        if row:
            level = parse_lesson_level(row["name"])
            if level:
                return level
    except Exception:
        pass
    return lid if 1 <= lid <= 10 else 1


def _build_prompt_for_lesson(user_prompt, lesson_id):
    """Merge user prompt with lesson task context for Agnes image generation."""
    from app.blueprints.student import LESSON_CONTENT
    level = _lesson_level_from_id(lesson_id)
    content = LESSON_CONTENT.get(level)
    if not content:
        return user_prompt
    img_activities = [a for a in content.get("activities", []) if a.get("type") == "agnes_image"]
    if not img_activities:
        return user_prompt
    act = img_activities[0]
    expected_tags = ", ".join(act.get("expected_tags", []))
    pieces = []
    if act.get("prompt_hint"):
        pieces.append(f"课程任务：{act['prompt_hint']}")
    if act.get("default_prompt"):
        pieces.append(f"默认画面参考：{act['default_prompt']}")
    if expected_tags:
        pieces.append(f"期望标签：{expected_tags}")
    pieces.append(f"学生描述：{user_prompt}")
    return "；".join(p for p in pieces if p)


def _process_image_job(job_id, allow_retry=False):
    job = _get_job(job_id)
    if not job:
        return
    _set_job(job_id, status="running", progress=35, message="正在画图，请稍等...", attempt_count=int(job.get("attempt_count", 0)) + 1)
    try:
        sid, lid, raw_prompt = job["student_id"], job["lesson_id"], job["prompt"]
        prompt_final = _build_prompt_for_lesson(raw_prompt, lid)
        _set_job(job_id, progress=50, message="正在理解你的画面...")
        content = _agnes_call("image", prompt_final)
        _set_job(job_id, progress=80, message="正在保存到作品目录...")
        img_bytes = _content_to_bytes(content)
        if not img_bytes:
            raise RuntimeError("empty image response")
        valid, reason = _validate_image(img_bytes)
        if not valid:
            raise RuntimeError(f"invalid image: {reason}")
        image_url, abs_path = _save_image_bytes(img_bytes, sid, lid)
        _inc_quota(sid, lid, "image")
        _set_job(job_id, status="done", progress=100,
                 message="已生成，并保存到你的作品目录。", image_url=image_url,
                 source="agnes", prompt_final=prompt_final, abs_path=abs_path)
    except Exception as exc:
        level = _lesson_level_from_id(job.get("lesson_id", 0))
        attempts = int(job.get("attempt_count", 0))
        if allow_retry and attempts < max(1, int(current_app.config.get("IMAGE_JOB_MAX_ATTEMPTS", 2))):
            _set_job(job_id, status="queued", progress=10, message="本次生成未完成，正在有限重试。", error=_friendly_image_error(exc))
            return
        pool_item, matched_tags = _pick_pool_image(job.get("prompt", ""), level)
        image_url = _copy_pool_to_student(pool_item, job.get("student_id"), job.get("lesson_id")) if pool_item else None
        if image_url:
            _set_job(job_id, status="done", progress=100,
                     message="AI排队太忙，先给你一张课程备用图。", image_url=image_url,
                     source="pool_fallback", matched_tags=list(matched_tags),
                     error=_friendly_image_error(exc))
        else:
            _set_job(job_id, status="error", progress=100,
                     message="AI画师暂时休息了，稍后再试。", source="error",
                     error=_friendly_image_error(exc))


def _image_worker(app):
    with app.app_context():
        while True:
            job_id = _claim_next_image_job()
            if job_id:
                _process_image_job(job_id, allow_retry=True)
            else:
                time.sleep(app.config.get("IMAGE_WORKER_POLL_INTERVAL", 0.25))


def _ensure_image_worker():
    start_image_workers(current_app._get_current_object())


def start_image_workers(app):
    """Recover durable jobs and start a process-local worker pool once."""
    global _image_worker_started
    marker = id(app)
    with _image_worker_lock:
        if marker in _image_worker_apps:
            return
        with app.app_context():
            _recover_image_jobs()
        requested = max(1, int(app.config.get("IMAGE_WORKER_COUNT", 2)))
        limit = max(1, int(app.config.get("AI_CONCURRENT_LIMIT", 5)))
        count = min(max(2, requested), limit) if limit >= 2 else 1
        for index in range(count):
            thread = threading.Thread(target=_image_worker, args=(app,), daemon=True, name=f"psm-image-worker-{index + 1}")
            thread.start()
            _image_worker_threads.append(thread)
        _image_worker_apps.add(marker)
        _image_worker_started = True


@bp.route("/generate/text", methods=["POST"])
@login_required
def generate_text():
    if current_user.is_teacher:
        return jsonify({"error": "教师不使用AI生成"}), 403
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "prompt不能为空"}), 400
    sid = current_user.student_id
    lid = session.get("current_lesson_id", 0)
    ok, used, limit = _check_quota(sid, lid, "text")
    if not ok:
        return jsonify({"error": f"本课AI文字额度已用完({used}/{limit})"}), 429
    limit_cfg = current_app.config.get("AI_CONCURRENT_LIMIT", 5)
    with _concurrent_lock:
        if _concurrent_count["text"] >= limit_cfg:
            return jsonify({"error": "AI忙，请稍后再试"}), 429
        _concurrent_count["text"] += 1
    try:
        content = _agnes_call("text", prompt)
        _inc_quota(sid, lid, "text")
        return jsonify({"content": content, "source": "agnes"})
    except Exception as e:
        fb = FALLBACK_TEXT[used % len(FALLBACK_TEXT)]
        return jsonify({"content": fb, "source": "fallback", "error": str(e)[:100]})
    finally:
        with _concurrent_lock:
            _concurrent_count["text"] -= 1


@bp.route("/generate/image", methods=["POST"])
@login_required
def generate_image():
    if current_user.is_teacher:
        return jsonify({"error": "教师不使用AI生成"}), 403
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "prompt不能为空"}), 400
    sid = current_user.student_id
    lid = session.get("current_lesson_id", 0)
    lesson_level = _lesson_level_from_id(lid)
    prompt_final = _build_prompt_for_lesson(prompt, lid)
    if not current_app.config.get("AGNES_API_KEY", ""):
        pool_item, matched_tags = _pick_pool_image(prompt, lesson_level)
        if pool_item:
            image_url = _copy_pool_to_student(pool_item, sid, lid)
            if image_url:
                job_id = uuid.uuid4().hex
                _set_job(job_id, student_id=sid, lesson_id=lid, prompt=prompt,
                         status="done", progress=100,
                         message="Agnes未配置，已从课程图片池找到合适图片。",
                         image_url=image_url, source="pool",
                         prompt_final=prompt_final,
                         matched_tags=list(matched_tags),
                         queue_size=_queued_image_count())
                return jsonify(_get_job(job_id) | {"job_id": job_id})
        return jsonify({"error": "Agnes未配置，且课程图片池没有严格匹配图片。"}), 503
    # No pool match — queue AI generation
    ok, used, limit = _check_quota(sid, lid, "image")
    if not ok:
        return jsonify({"error": f"本课AI图片额度已用完({used}/{limit})"}), 429
    _ensure_image_worker()
    job_id = uuid.uuid4().hex
    _set_job(job_id, status="queued", progress=10,
             message="已进入生图队列，请不要重复点击。",
             prompt=prompt, student_id=sid, lesson_id=lid,
             source="queue", prompt_final=prompt_final,
             queue_size=_queued_image_count() + 1)
    _ensure_image_worker()
    return jsonify(_get_job(job_id) | {"job_id": job_id})


@bp.route("/generate/image/status/<job_id>")
@login_required
def image_status(job_id):
    job = _get_job(job_id)
    if not job:
        return jsonify({"error": "任务不存在或已过期"}), 404
    if job.get("student_id") and not current_user.is_teacher and job.get("student_id") != current_user.student_id:
        return jsonify({"error": "不能查看别人的任务"}), 403
    safe = {k: v for k, v in job.items() if k not in {"prompt", "abs_path"}}
    safe["job_id"] = job_id
    safe["queue_size"] = _queued_image_count()
    return jsonify(safe)


@bp.route("/quota")
@login_required
def get_quota():
    if current_user.is_teacher:
        return jsonify({"error": "教师无额度概念"}), 403
    sid = current_user.student_id
    lid = session.get("current_lesson_id", 0)
    db = get_db()
    text_row = db.execute(
        "SELECT used FROM quota_ledger WHERE student_id=? AND lesson_id=? AND api_type='text'",
        (sid, lid),
    ).fetchone()
    image_row = db.execute(
        "SELECT used FROM quota_ledger WHERE student_id=? AND lesson_id=? AND api_type='image'",
        (sid, lid),
    ).fetchone()
    return jsonify({
        "text_used": text_row["used"] if text_row else 0,
        "text_limit": current_app.config["QUOTA_TEXT_PER_LESSON"],
        "image_used": image_row["used"] if image_row else 0,
        "image_limit": current_app.config["QUOTA_IMAGE_PER_LESSON"],
    })


# --- Teacher: list students and their submissions ---
@bp.route("/teacher/students")
@login_required
def list_students_api():
    """API endpoint to list students with submission counts, filterable by lesson."""
    if not current_user.is_teacher:
        return jsonify({"error": "需要教师权限"}), 403
    from flask import request as req
    class_id = req.args.get("class_id", type=int)
    lesson_id = req.args.get("lesson_id", type=int)
    db = get_db()
    if not class_id:
        return jsonify({"error": "需要class_id"}), 400
    students = db.execute(
        "SELECT s.id, s.name, s.display_name FROM student s WHERE s.class_id=? ORDER BY s.id",
        (class_id,),
    ).fetchall()
    result = []
    for st in students:
        q = "SELECT COUNT(*) as cnt FROM submission WHERE student_id=?"
        params = [st["id"]]
        if lesson_id:
            q += " AND lesson_id=?"
            params.append(lesson_id)
        cnt = db.execute(q, params).fetchone()["cnt"]
        result.append({
            "id": st["id"],
            "name": st["name"],
            "display_name": st["display_name"],
            "submission_count": cnt,
        })
    return jsonify({"students": result})
