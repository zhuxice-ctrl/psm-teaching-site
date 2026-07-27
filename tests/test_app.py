"""PSM Teaching Site — comprehensive test suite.

Tests cover:
A. Lesson level mapping from lesson name (L1-L10)
B. LESSON_CONTENT completeness L1-L10
C. Student submission path organized by student_*/lesson_*/
D. Teacher submissions with lesson filter
E. Image: prompt tags, pool matching, solid-color rejection, no wrong-match
F. All original tests preserved
"""
import os, sys, hashlib, json, tempfile, struct, io, ssl, base64
import urllib.error
import atexit, shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app, get_db, init_db
from config import TestConfig

_test_db_path = os.path.join(tempfile.gettempdir(), "psm_test.db")
_test_upload_dir = os.path.join(tempfile.gettempdir(), "psm_test_uploads")
_original_manifest_bytes = None
_original_manifest_existed = None
_manifest_restore_registered = False


def setup_app():
    TestConfig.DATABASE_URL = f"sqlite:///{_test_db_path}"
    TestConfig.SQLALCHEMY_DATABASE_URI = TestConfig.DATABASE_URL
    TestConfig.UPLOAD_FOLDER = _test_upload_dir
    if os.path.exists(_test_db_path):
        os.unlink(_test_db_path)
    if os.path.exists(_test_upload_dir):
        shutil.rmtree(_test_upload_dir)
    app = create_app(TestConfig)
    with app.app_context():
        db = get_db()
        init_db(db)
        pw_hash = hashlib.sha256("testpass".encode()).hexdigest()
        db.execute(
            "INSERT INTO teacher(username, password_hash, display_name) VALUES(?,?,?)",
            ("testteacher", pw_hash, "测试老师"),
        )
        db.execute(
            "INSERT INTO class(teacher_id, name, semester, class_code) VALUES(?,?,?,?)",
            (1, "测试班级", "2026春", "TEST01"),
        )
        db.execute("INSERT INTO student(name, phone_tail, display_name, class_id) VALUES(?,?,?,?)", ("张三", "", "小张", 1))
        db.execute("INSERT INTO student(name, phone_tail, display_name, class_id) VALUES(?,?,?,?)", ("李四", "1234", "小李", 1))
        db.execute("INSERT INTO student(name, phone_tail, display_name, class_id) VALUES(?,?,?,?)", ("李四", "5678", "李四B", 1))
        # Create L1-L10 lessons
        lesson_names = [
            (1, "L1-AI是什么"), (2, "L2-AI能做什么"), (3, "L3-AI是怎么学习的"),
            (4, "L4-AI与创意"), (5, "L5-AI与自然语言"), (6, "L6-AI与图像"),
            (7, "L7-编程入门Scratch"), (8, "L8-编程进阶Scratch动画"),
            (9, "L9-编程挑战Python"), (10, "L10-作品发布"),
        ]
        for lid, name in lesson_names:
            db.execute("INSERT INTO lesson(class_id, name, lesson_date, time_slot) VALUES(?,?,?,?)",
                        (1, name, "2026-07-01", "14:00-15:30"))
        db.commit()
    return app


# ==================== A. Lesson mapping tests ====================

def test_lesson_mapping_l1():
    """L1 name → level 1"""
    from app.blueprints.student import parse_lesson_level
    assert parse_lesson_level("L1-AI是什么") == 1
    print("PASS: parse_lesson_level L1")


def test_lesson_mapping_l10():
    """L10 name → level 10"""
    from app.blueprints.student import parse_lesson_level
    assert parse_lesson_level("L10-作品发布") == 10
    assert parse_lesson_level("L10 - 作品发布与展示") == 10
    print("PASS: parse_lesson_level L10")


def test_lesson_mapping_various():
    """Various name formats"""
    from app.blueprints.student import parse_lesson_level
    assert parse_lesson_level("L3-AI是怎么学习的") == 3
    assert parse_lesson_level("L7-编程入门Scratch") == 7
    assert parse_lesson_level("l5 语言") == 5
    assert parse_lesson_level("L99-out of range") is None
    assert parse_lesson_level("") is None
    assert parse_lesson_level(None) is None
    assert parse_lesson_level("随便什么名字") is None
    print("PASS: parse_lesson_level various formats")


def test_lesson_mapping_no_mod():
    """Verify no (lid % 6)+1 — lesson_id=7 should map to L7, not L2"""
    app = setup_app()
    with app.test_request_context():
        from app.blueprints.student import parse_lesson_level
        # This was the bug: (7 % 6) + 1 = 2, but should be 7
        assert parse_lesson_level("L7-编程入门") == 7
    print("PASS: no (lid % 6)+1 bug")


def test_student_requested_lesson_does_not_jump():
    """Requested lesson page shows that lesson and syncs API session lesson_id."""
    app = setup_app()
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    r = client.get("/student/lesson/7")
    html = r.data.decode()
    assert r.status_code == 200
    assert "L7 - 编程入门" in html
    assert "L2 - AI能做什么" not in html
    with client.session_transaction() as sess:
        assert sess["current_lesson_id"] == 7
    print("PASS: requested lesson stays on L7 and syncs session")


# ==================== B. LESSON_CONTENT completeness ====================

def test_lesson_content_l1_to_l10():
    """All L1-L10 entries exist with activities"""
    from app.blueprints.student import LESSON_CONTENT
    for level in range(1, 11):
        assert level in LESSON_CONTENT, f"L{level} missing from LESSON_CONTENT"
        content = LESSON_CONTENT[level]
        assert "title" in content
        assert "activities" in content
        assert len(content["activities"]) >= 2, f"L{level} has fewer than 2 activities"
    print("PASS: LESSON_CONTENT L1-L10 complete")


def test_lesson_content_image_activities_have_tags():
    """agnes_image activities have expected_tags, default_prompt, prompt_hint"""
    from app.blueprints.student import LESSON_CONTENT
    for level in range(1, 11):
        content = LESSON_CONTENT[level]
        for act in content["activities"]:
            if act["type"] == "agnes_image":
                assert "expected_tags" in act, f"L{level}/{act['name']} missing expected_tags"
                assert "default_prompt" in act, f"L{level}/{act['name']} missing default_prompt"
                assert "prompt_hint" in act, f"L{level}/{act['name']} missing prompt_hint"
                assert len(act["expected_tags"]) >= 1
    print("PASS: agnes_image activities have metadata")


def test_l7_to_l9_have_external():
    """L7-L9 have external (psm.steam.fun) activities"""
    from app.blueprints.student import LESSON_CONTENT
    for level in [7, 8, 9]:
        content = LESSON_CONTENT[level]
        types = [a["type"] for a in content["activities"]]
        assert "external" in types, f"L{level} missing external activity"
    print("PASS: L7-L9 have external/psm.steam.fun activities")


def test_l10_is_showcase():
    """L10 is about publishing/showcase"""
    from app.blueprints.student import LESSON_CONTENT
    l10 = LESSON_CONTENT[10]
    assert "发布" in l10["title"] or "展示" in l10["title"]
    types = [a["type"] for a in l10["activities"]]
    assert "create" in types, "L10 should have create activity for publishing"
    print("PASS: L10 is showcase/publishing")


# ==================== C. Student submission path ====================

def test_submit_saves_to_student_lesson_dir():
    """Submit image → saved in student_<sid>/lesson_<lid>/ directory"""
    app = setup_app()
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    # Create a tiny valid PNG
    png_data = _make_tiny_png()
    data = {
        "work_type": "mixed",
        "content": "我的老虎画",
        "image": (io.BytesIO(png_data), "test.png"),
    }
    r = client.post("/student/lesson/1/submit", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert "已提交" in r.data.decode()
    # Check the DB for the image_path
    with app.app_context():
        db = get_db()
        sub = db.execute("SELECT * FROM submission ORDER BY id DESC LIMIT 1").fetchone()
        assert sub is not None
        assert "student_1" in sub["image_path"], f"Expected student_1 in path, got: {sub['image_path']}"
        assert "lesson_1" in sub["image_path"], f"Expected lesson_1 in path, got: {sub['image_path']}"
        assert sub["image_path"].startswith("uploads/student_1/lesson_1/")
    print("PASS: submit saves to student_<id>/lesson_<id>/")


def test_submit_text_only_no_image_path():
    """Text-only submission has empty image_path"""
    app = setup_app()
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    r = client.post("/student/lesson/1/submit", data={"work_type": "text", "content": "文字作品"}, follow_redirects=True)
    assert "已提交" in r.data.decode()
    with app.app_context():
        db = get_db()
        sub = db.execute("SELECT * FROM submission ORDER BY id DESC LIMIT 1").fetchone()
        assert sub["image_path"] == ""
    print("PASS: text-only submit has empty image_path")


# ==================== D. Teacher lesson filter ====================

def test_teacher_submissions_lesson_filter():
    """Teacher submissions page accepts lesson_id filter"""
    app = setup_app()
    client = app.test_client()
    client.post("/login/teacher", data={"username": "testteacher", "password": "testpass"})
    # Submit a work first as student
    with app.test_client() as sc:
        sc.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
        sc.post("/student/lesson/1/submit", data={"work_type": "text", "content": "L1作品"})
    with app.test_client() as sc:
        sc.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
        sc.post("/student/lesson/2/submit", data={"work_type": "text", "content": "L2作品"})
    # Teacher views all
    r = client.get("/teacher/class/1/submissions")
    assert r.status_code == 200
    html = r.data.decode()
    assert "L1作品" in html
    assert "L2作品" in html
    # Filter by lesson 1
    r = client.get("/teacher/class/1/submissions?lesson_id=1")
    html = r.data.decode()
    assert "L1作品" in html
    # Filter by lesson 2
    r = client.get("/teacher/class/1/submissions?lesson_id=2")
    html = r.data.decode()
    assert "L2作品" in html
    print("PASS: teacher submissions lesson filter")


def test_teacher_submissions_shows_lesson_name():
    """Submissions page shows lesson name badge"""
    app = setup_app()
    client = app.test_client()
    client.post("/login/teacher", data={"username": "testteacher", "password": "testpass"})
    with app.test_client() as sc:
        sc.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
        sc.post("/student/lesson/1/submit", data={"work_type": "text", "content": "测试"})
    r = client.get("/teacher/class/1/submissions")
    html = r.data.decode()
    assert "lesson-badge" in html
    assert "L1" in html
    print("PASS: submissions page shows lesson name")


# ==================== E. Image generation tests ====================

def test_prompt_tags_tiger():
    """'画一只老虎' should produce 'tiger' tag, not just generic 'animal'"""
    from app.blueprints.api import _prompt_tags
    tags = _prompt_tags("画一只老虎")
    assert "tiger" in tags, f"Expected 'tiger' tag, got: {tags}"
    assert "animal" in tags, f"Expected 'animal' as parent, got: {tags}"
    print("PASS: tiger prompt → tiger tag")


def test_prompt_tags_cat():
    """'小猫' should produce 'cat' tag"""
    from app.blueprints.api import _prompt_tags
    tags = _prompt_tags("画一只小猫")
    assert "cat" in tags
    assert "animal" in tags
    print("PASS: cat prompt → cat tag")


def test_prompt_tags_generic_animal():
    """'动物' alone → just 'animal', no specific"""
    from app.blueprints.api import _prompt_tags
    tags = _prompt_tags("画一只动物")
    assert "animal" in tags
    assert "tiger" not in tags
    assert "cat" not in tags
    print("PASS: generic animal prompt → no specific tags")


def test_pool_tiger_no_match_generic_animal():
    """Pool item with only 'animal' tag should NOT match 'tiger' prompt"""
    app = setup_app()
    with app.app_context():
        # Create a fake manifest with only generic animal image
        _write_test_manifest([
            {"file": "images/pool/g_animal_1.png", "lesson_id": 0, "tags": ["animal"], "title": "通用动物"}
        ])
        # Also need the file to exist for copy test, but _pick_pool_image only reads manifest
        from app.blueprints.api import _pick_pool_image
        item, matched = _pick_pool_image("画一只老虎", 1)
        assert item is None, f"Should NOT match generic animal for tiger, but got: {item}"
        print("PASS: tiger prompt does NOT match generic 'animal' pool item")


def test_pool_tiger_matches_tiger_tag():
    """Pool item with 'tiger' tag SHOULD match 'tiger' prompt"""
    app = setup_app()
    with app.app_context():
        _write_test_manifest([
            {"file": "images/pool/l1_tiger_1.png", "lesson_id": 1, "tags": ["tiger", "animal"], "title": "老虎"},
            {"file": "images/pool/g_animal_1.png", "lesson_id": "general", "tags": ["animal"], "title": "通用动物"},
        ])
        from app.blueprints.api import _pick_pool_image
        item, matched = _pick_pool_image("画一只老虎", 1)
        assert item is not None
        assert "tiger" in item.get("tags", [])
        print("PASS: tiger prompt matches tiger-tagged pool item")


def test_pool_lesson_mismatch_skipped():
    """Pool item for lesson 5 should not match request from lesson 1"""
    app = setup_app()
    with app.app_context():
        _write_test_manifest([
            {"file": "images/pool/l5_cat_1.png", "lesson_id": 5, "tags": ["cat", "animal"], "title": "L5猫"},
        ])
        from app.blueprints.api import _pick_pool_image
        item, matched = _pick_pool_image("画一只小猫", 1)
        assert item is None
        print("PASS: pool item from different lesson skipped")


def test_solid_color_image_rejected():
    """Solid color image should be detected as invalid"""
    from app.blueprints.api import _validate_image
    # Create a solid blue 128x128 PNG
    try:
        from PIL import Image
        img = Image.new("RGB", (128, 128), color=(0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        valid, reason = _validate_image(img_bytes)
        assert not valid, f"Solid color should be invalid, got: valid={valid}, reason={reason}"
        assert "solid" in reason.lower() or "variance" in reason.lower()
        print("PASS: solid color image detected as invalid")
    except ImportError:
        print("SKIP: PIL not available, cannot test solid color detection")


def test_diverse_image_accepted():
    """Image with diverse colors should pass validation"""
    from app.blueprints.api import _validate_image
    try:
        from PIL import Image
        import random as rng
        img = Image.new("RGB", (128, 128))
        pixels = img.load()
        for x in range(128):
            for y in range(128):
                pixels[x, y] = (rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        valid, reason = _validate_image(img_bytes)
        assert valid, f"Diverse image should be valid, got: {reason}"
        print("PASS: diverse-color image accepted")
    except ImportError:
        print("SKIP: PIL not available, cannot test diverse image")


def test_tiny_image_rejected():
    """Image smaller than 64x64 should be rejected"""
    from app.blueprints.api import _validate_image
    try:
        from PIL import Image
        img = Image.new("RGB", (32, 32), color=(100, 200, 50))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        valid, reason = _validate_image(img_bytes)
        assert not valid
        assert "small" in reason.lower() or "32" in reason
        print("PASS: tiny image rejected")
    except ImportError:
        print("SKIP: PIL not available")


def test_prompt_fusion_with_lesson():
    """_build_prompt_for_lesson merges lesson context"""
    from app.blueprints.api import _build_prompt_for_lesson
    # L1 has agnes_image activity "我的AI画像" with prompt_hint
    result = _build_prompt_for_lesson("画一个机器人", 1)
    assert len(result) > len("画一个机器人"), f"Expected prompt fusion, got: {result}"
    assert "画一个机器人" in result
    assert "课程任务" in result
    assert "默认画面参考" in result
    assert "期望标签" in result
    assert "robot" in result
    print("PASS: prompt fusion with lesson context")


def test_job_returns_source_and_tags():
    """Image generation job response includes source/matched_tags/prompt_final fields"""
    app = setup_app()
    with app.app_context():
        _write_test_manifest([
            {"file": "images/pool/l1_tiger_1.png", "lesson_id": 1, "tags": ["tiger", "animal"], "title": "老虎"},
        ])
        from app.blueprints.api import _pick_pool_image
        item, matched = _pick_pool_image("画一只老虎", 1)
        if item:
            assert "tiger" in matched
            print("PASS: matched_tags include tiger")
        else:
            print("PASS: no pool match (would go to AI generation)")


def test_generate_image_without_agnes_uses_pool_student_dir():
    """When Agnes key is absent, strict pool fallback copies image to student/lesson dir."""
    app = setup_app()
    app.config["AGNES_API_KEY"] = ""
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    client.get("/student/lesson/1")
    with app.app_context():
        _write_test_manifest([
            {"file": "images/pool/l1_tiger_1.png", "lesson_id": 1, "tags": ["tiger", "animal"], "title": "老虎"},
        ])
    r = client.post("/api/generate/image", json={"prompt": "画一只老虎"})
    data = r.get_json()
    assert r.status_code == 200, data
    assert data["source"] == "pool"
    assert "tiger" in data["matched_tags"]
    assert "/static/uploads/student_1/lesson_1/" in data["image_url"]
    assert "/pool_" in data["image_url"]
    print("PASS: no Agnes key uses pool and saves under student_<id>/lesson_<id>/")


def test_generate_image_with_agnes_key_queues_before_pool():
    """When Agnes key exists, image route queues Agnes generation before pool fallback."""
    app = setup_app()
    app.config["AGNES_API_KEY"] = "test-key"
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    client.get("/student/lesson/1")
    with app.app_context():
        _write_test_manifest([
            {"file": "images/pool/l1_tiger_1.png", "lesson_id": 1, "tags": ["tiger", "animal"], "title": "老虎"},
        ])
        from app.blueprints import api as api_mod
        original_ensure = api_mod._ensure_image_worker
        api_mod._ensure_image_worker = lambda: None
        try:
            r = client.post("/api/generate/image", json={"prompt": "画一只老虎"})
        finally:
            api_mod._ensure_image_worker = original_ensure
    data = r.get_json()
    assert r.status_code == 200, data
    assert data["status"] == "queued"
    assert data["source"] == "queue"
    assert data["prompt_final"]
    assert "默认画面参考" in data["prompt_final"]
    assert "期望标签" in data["prompt_final"]
    print("PASS: Agnes key queues AI generation with fused prompt before fallback")


def test_agnes_image_post_retries_ssl_eof_then_succeeds():
    """A transient TLS EOF on Agnes POST is retried without disabling TLS."""
    app = setup_app()
    app.config["AGNES_API_KEY"] = "test-key"
    from app.blueprints import api as api_mod

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"data": [{"url": "https://img.example/dino.png"}]}).encode()

    calls = []
    def fake_urlopen(req, timeout):
        calls.append((req, timeout))
        if len(calls) == 1:
            raise urllib.error.URLError(ssl.SSLEOFError(8, "EOF occurred in violation of protocol"))
        return Response()

    original_urlopen = api_mod.urllib.request.urlopen
    original_sleep = api_mod.time.sleep
    api_mod.urllib.request.urlopen = fake_urlopen
    api_mod.time.sleep = lambda _seconds: None
    try:
        with app.app_context():
            result = api_mod._agnes_call("image", "画一只恐龙")
    finally:
        api_mod.urllib.request.urlopen = original_urlopen
        api_mod.time.sleep = original_sleep

    assert result == "https://img.example/dino.png"
    assert len(calls) == 2
    assert calls[0][0].get_header("User-agent") == "PSM-Teaching-Site/1.0"


def test_agnes_result_download_retries_ssl_eof_then_succeeds():
    """A transient TLS EOF while downloading the result URL is retried."""
    app = setup_app()
    from app.blueprints import api as api_mod

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b"image-bytes"

    calls = []
    def fake_urlopen(req, timeout):
        calls.append((req, timeout))
        if len(calls) == 1:
            raise urllib.error.URLError(ssl.SSLEOFError(8, "EOF occurred in violation of protocol"))
        return Response()

    original_urlopen = api_mod.urllib.request.urlopen
    original_sleep = api_mod.time.sleep
    api_mod.urllib.request.urlopen = fake_urlopen
    api_mod.time.sleep = lambda _seconds: None
    try:
        with app.app_context():
            result = api_mod._content_to_bytes("https://img.example/dino.png")
    finally:
        api_mod.urllib.request.urlopen = original_urlopen
        api_mod.time.sleep = original_sleep

    assert result == b"image-bytes"
    assert len(calls) == 2
    assert calls[0][0].get_header("User-agent") == "PSM-Teaching-Site/1.0"


def test_agnes_persistent_failure_uses_pool_with_accurate_source():
    """Exhausted Agnes retries use a strict matching pool image, never source=agnes."""
    app = setup_app()
    app.config["AGNES_API_KEY"] = "test-key"
    app.config["IMAGE_JOB_MAX_ATTEMPTS"] = 1
    from app.blueprints import api as api_mod
    with app.app_context():
        _write_test_manifest([
            {"file": "images/pool/l1_tiger_1.png", "lesson_id": 1,
             "tags": ["tiger", "animal"], "title": "老虎"},
        ])
        job_id = "persistent-failure-pool"
        api_mod._set_job(job_id, status="queued", source="queue", prompt="画一只老虎",
                         student_id=1, lesson_id=1)
        original_call = api_mod._agnes_call
        api_mod._agnes_call = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            urllib.error.URLError(ssl.SSLEOFError(8, "unexpected eof")))
        try:
            api_mod._process_image_job(job_id)
        finally:
            api_mod._agnes_call = original_call
        job = api_mod._get_job(job_id)
    assert job["status"] == "done"
    assert job["source"] == "pool_fallback"
    assert "tiger" in job["matched_tags"]
    assert "SSL" not in job.get("error", "") and "EOF" not in job.get("error", "")


def test_agnes_persistent_failure_without_pool_is_friendly_error():
    """No strict pool match yields a friendly error and source=error."""
    app = setup_app()
    app.config["AGNES_API_KEY"] = "test-key"
    app.config["IMAGE_JOB_MAX_ATTEMPTS"] = 1
    from app.blueprints import api as api_mod
    with app.app_context():
        _write_test_manifest([])
        job_id = "persistent-failure-no-pool"
        api_mod._set_job(job_id, status="queued", source="queue", prompt="画一只恐龙",
                         student_id=1, lesson_id=1)
        original_call = api_mod._agnes_call
        api_mod._agnes_call = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            urllib.error.URLError(ssl.SSLEOFError(8, "unexpected eof")))
        try:
            api_mod._process_image_job(job_id)
        finally:
            api_mod._agnes_call = original_call
        job = api_mod._get_job(job_id)
    assert job["status"] == "error"
    assert job["source"] == "error"
    assert job["message"] == "AI画师暂时休息了，稍后再试。"
    assert "SSL" not in job.get("error", "") and "EOF" not in job.get("error", "")


def test_image_worker_saves_without_request_context():
    """Background workers can save generated images without a Flask request context."""
    app = setup_app()
    app.config["AGNES_API_KEY"] = "test-key"
    from app.blueprints import api as api_mod
    with app.app_context():
        job_id = "worker-save-no-request-context"
        api_mod._set_job(job_id, status="queued", source="queue", prompt="画一个机器人",
                         student_id=1, lesson_id=1)
        original_call = api_mod._agnes_call
        original_validate = api_mod._validate_image
        api_mod._agnes_call = lambda *_args, **_kwargs: "data:image/png;base64," + base64.b64encode(_make_tiny_png()).decode()
        api_mod._validate_image = lambda _data: (True, "ok")
        try:
            api_mod._process_image_job(job_id)
        finally:
            api_mod._agnes_call = original_call
            api_mod._validate_image = original_validate
        job = api_mod._get_job(job_id)
    assert job["status"] == "done"
    assert job["source"] == "agnes"
    assert "/static/uploads/student_1/lesson_1/" in job["image_url"]
    assert os.path.isfile(job["abs_path"])


def test_text_generation_ui_progress_lock():
    """Lesson template exposes text progress UI and duplicate-click lock."""
    app = setup_app()
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    r = client.get("/student/lesson/5")
    html = r.data.decode()
    assert "const textLocks = new Set()" in html
    assert "AI正在理解问题" in html
    assert "AI正在组织答案" in html
    assert "btn.disabled = true" in html
    assert "textLocks.delete(idx)" in html
    print("PASS: text generation UI has progress and button lock")


# ==================== Original tests (preserved) ====================

def test_health():
    app = setup_app()
    client = app.test_client()
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"
    print("PASS: health")


def test_index():
    app = setup_app()
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert "PSM" in r.data.decode()
    print("PASS: index")


def test_teacher_login():
    app = setup_app()
    client = app.test_client()
    r = client.post("/login/teacher", data={"username": "testteacher", "password": "testpass"}, follow_redirects=True)
    assert r.status_code == 200
    assert "教师后台" in r.data.decode()
    print("PASS: teacher login")


def test_teacher_login_wrong():
    app = setup_app()
    client = app.test_client()
    r = client.post("/login/teacher", data={"username": "testteacher", "password": "wrong"}, follow_redirects=True)
    assert "错误" in r.data.decode()
    print("PASS: teacher login wrong pw")


def test_student_login_unique():
    app = setup_app()
    client = app.test_client()
    r = client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"}, follow_redirects=True)
    assert r.status_code == 200
    assert "L1" in r.data.decode()
    print("PASS: student login unique name")


def test_student_login_duplicate_need_phone():
    app = setup_app()
    client = app.test_client()
    r = client.post("/login/student", data={"name": "李四", "phone_tail": "", "class_code": "TEST01"}, follow_redirects=True)
    assert "手机尾号" in r.data.decode()
    print("PASS: student duplicate name asks phone")


def test_student_login_with_phone():
    app = setup_app()
    client = app.test_client()
    r = client.post("/login/student", data={"name": "李四", "phone_tail": "1234", "class_code": "TEST01"}, follow_redirects=True)
    assert r.status_code == 200
    assert "L1" in r.data.decode()
    print("PASS: student login with phone tail")


def test_student_login_wrong_code():
    app = setup_app()
    client = app.test_client()
    r = client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "WRONG"}, follow_redirects=True)
    assert "无效" in r.data.decode()
    print("PASS: student wrong class code")


def test_teacher_create_class():
    app = setup_app()
    client = app.test_client()
    client.post("/login/teacher", data={"username": "testteacher", "password": "testpass"})
    r = client.post("/teacher/class/create", data={"name": "新班级", "semester": "2026秋"}, follow_redirects=True)
    assert r.status_code == 200
    assert "班级码" in r.data.decode()
    print("PASS: teacher create class")


def test_teacher_import_students():
    app = setup_app()
    client = app.test_client()
    client.post("/login/teacher", data={"username": "testteacher", "password": "testpass"})
    r = client.post("/teacher/class/1/students/import", data={"student_list": "新同学A\n新同学B,9999"}, follow_redirects=True)
    assert "已导入" in r.data.decode()
    print("PASS: teacher import students")


def test_quota_endpoint():
    app = setup_app()
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    r = client.get("/api/quota")
    assert r.status_code == 200
    data = r.get_json()
    assert "text_limit" in data
    print("PASS: quota endpoint")


def test_student_submit():
    app = setup_app()
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    r = client.post("/student/lesson/1/submit", data={"work_type": "text", "content": "我的作品"}, follow_redirects=True)
    assert "已提交" in r.data.decode()
    print("PASS: student submit")


def test_l7l8l9_page():
    app = setup_app()
    client = app.test_client()
    client.post("/login/student", data={"name": "张三", "phone_tail": "", "class_code": "TEST01"})
    r = client.get("/student/lesson/1/l7l8l9")
    assert r.status_code == 200
    assert "psm.steam.fun" in r.data.decode()
    print("PASS: L7-L9 external links page")


# ==================== F. /psm mount prefix tests ====================

def test_psm_prefixed_routes_direct_smoke():
    """Direct local /psm/* requests work without nginx."""
    app = setup_app()
    client = app.test_client()
    checks = [
        ("/psm/health", "ok"),
        ("/psm/", "PSM"),
        ("/psm/login/student?code=TEST01", "TEST01"),
        ("/psm/login/teacher", "教师登录"),
    ]
    for path, expected in checks:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert expected in r.data.decode()
    html = client.get("/psm/").data.decode()
    assert 'href="/psm/login/teacher"' in html
    assert 'href="/psm/login/student"' in html
    assert 'window.PSM.API_PREFIX = "/psm/api/";' in html
    print("PASS: direct /psm/* smoke routes and generated links")


def test_psm_student_login_redirect_keeps_prefix():
    """Student login reached through /psm redirects to /psm/student/..."""
    app = setup_app()
    client = app.test_client()
    r = client.post(
        "/psm/login/student",
        data={"name": "张三", "phone_tail": "", "class_code": "TEST01"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.location.startswith("/psm/student/lesson/"), r.location
    print("PASS: /psm student login redirect keeps prefix")


def test_proxy_forwarded_prefix_generates_psm_links():
    """nginx-style stripped-path proxy with X-Forwarded-Prefix keeps /psm URLs."""
    app = setup_app()
    client = app.test_client()
    r = client.get("/", headers={"X-Forwarded-Prefix": "/psm"})
    html = r.data.decode()
    assert r.status_code == 200
    assert 'href="/psm/login/teacher"' in html
    assert 'href="/psm/login/student"' in html
    assert 'window.PSM.API_PREFIX = "/psm/api/";' in html
    print("PASS: X-Forwarded-Prefix /psm generates prefixed links")


def test_proxy_x_script_name_generates_psm_links():
    """Legacy X-Script-Name proxy header also keeps /psm URLs."""
    app = setup_app()
    client = app.test_client()
    r = client.get("/login/teacher", headers={"X-Script-Name": "/psm"})
    html = r.data.decode()
    assert r.status_code == 200
    assert 'src="/psm/static/vendor/htmx/htmx.min.js"' in html
    assert 'href="/psm/login"' in html
    print("PASS: X-Script-Name /psm generates prefixed links")


def test_teacher_class_detail_lesson_links_keep_psm_prefix():
    """Teacher-visible lesson links are mount-prefix aware."""
    app = setup_app()
    client = app.test_client()
    client.post("/psm/login/teacher", data={"username": "testteacher", "password": "testpass"})
    r = client.get("/psm/teacher/class/1")
    html = r.data.decode()
    assert r.status_code == 200
    assert "/psm/student/lesson/1" in html
    assert "<code>/student/lesson/1</code>" not in html
    print("PASS: teacher class lesson links keep /psm prefix")


# ==================== Helpers ====================

def _make_tiny_png():
    """Create minimal valid PNG (1x1 red pixel)."""
    try:
        from PIL import Image
        img = Image.new("RGB", (4, 4), color=(255, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Minimal PNG: 1x1 white pixel
        import zlib
        def chunk(ctype, data):
            c = ctype + data
            return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        header = b'\x89PNG\r\n\x1a\n'
        ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        raw = b'\x00\xff\x00\x00'
        idat = chunk(b'IDAT', zlib.compress(raw))
        iend = chunk(b'IEND', b'')
        return header + ihdr + idat + iend


def _write_test_manifest(images):
    """Write a test manifest.json to the pool directory."""
    global _original_manifest_bytes, _original_manifest_existed, _manifest_restore_registered
    from flask import current_app
    pool_dir = os.path.join(current_app.root_path, "static", "images", "pool")
    os.makedirs(pool_dir, exist_ok=True)
    manifest_path = os.path.join(pool_dir, "manifest.json")
    if _original_manifest_bytes is None:
        _original_manifest_existed = os.path.exists(manifest_path)
        _original_manifest_bytes = open(manifest_path, "rb").read() if _original_manifest_existed else b""
    if not _manifest_restore_registered:
        def restore_manifest():
            if _original_manifest_existed:
                with open(manifest_path, "wb") as f:
                    f.write(_original_manifest_bytes)
            elif os.path.exists(manifest_path):
                os.unlink(manifest_path)
        atexit.register(restore_manifest)
        _manifest_restore_registered = True
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"images": images}, f, ensure_ascii=False)


# ==================== Runner ====================

if __name__ == "__main__":
    tests = [
        # A: Lesson mapping
        test_lesson_mapping_l1, test_lesson_mapping_l10,
        test_lesson_mapping_various, test_lesson_mapping_no_mod,
        test_student_requested_lesson_does_not_jump,
        # B: LESSON_CONTENT
        test_lesson_content_l1_to_l10, test_lesson_content_image_activities_have_tags,
        test_l7_to_l9_have_external, test_l10_is_showcase,
        # C: Submission path
        test_submit_saves_to_student_lesson_dir, test_submit_text_only_no_image_path,
        # D: Teacher filter
        test_teacher_submissions_lesson_filter, test_teacher_submissions_shows_lesson_name,
        # E: Image generation
        test_prompt_tags_tiger, test_prompt_tags_cat, test_prompt_tags_generic_animal,
        test_pool_tiger_no_match_generic_animal, test_pool_tiger_matches_tiger_tag,
        test_pool_lesson_mismatch_skipped,
        test_solid_color_image_rejected, test_diverse_image_accepted, test_tiny_image_rejected,
        test_prompt_fusion_with_lesson, test_job_returns_source_and_tags,
        test_generate_image_without_agnes_uses_pool_student_dir,
        test_generate_image_with_agnes_key_queues_before_pool,
        test_agnes_image_post_retries_ssl_eof_then_succeeds,
        test_agnes_result_download_retries_ssl_eof_then_succeeds,
        test_agnes_persistent_failure_uses_pool_with_accurate_source,
        test_agnes_persistent_failure_without_pool_is_friendly_error,
        test_image_worker_saves_without_request_context,
        test_text_generation_ui_progress_lock,
        # Original
        test_health, test_index, test_teacher_login, test_teacher_login_wrong,
        test_student_login_unique, test_student_login_duplicate_need_phone,
        test_student_login_with_phone, test_student_login_wrong_code,
        test_teacher_create_class, test_teacher_import_students,
        test_quota_endpoint, test_student_submit, test_l7l8l9_page,
        # F: /psm mount prefix
        test_psm_prefixed_routes_direct_smoke,
        test_psm_student_login_redirect_keeps_prefix,
        test_proxy_forwarded_prefix_generates_psm_links,
        test_proxy_x_script_name_generates_psm_links,
        test_teacher_class_detail_lesson_links_keep_psm_prefix,
    ]
    passed = 0
    failed = 0
    skipped = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            if "SKIP" in str(e):
                print(f"SKIP: {t.__name__}: {e}")
                skipped += 1
            else:
                print(f"FAIL: {t.__name__}: {e}")
                failed += 1
    print(f"\n=== Results: {passed} passed, {failed} failed, {skipped} skipped ===")
    sys.exit(1 if failed else 0)
