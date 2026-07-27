CREATE TABLE IF NOT EXISTS teacher (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT "",
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS class (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL REFERENCES teacher(id),
    name TEXT NOT NULL,
    semester TEXT DEFAULT "",
    class_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lesson (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL REFERENCES class(id),
    name TEXT NOT NULL,
    lesson_date TEXT DEFAULT "",
    time_slot TEXT DEFAULT "",
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS student (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone_tail TEXT DEFAULT "",
    display_name TEXT DEFAULT "",
    class_id INTEGER NOT NULL REFERENCES class(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, phone_tail, class_id)
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES student(id),
    lesson_id INTEGER NOT NULL REFERENCES lesson(id),
    signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS submission (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES student(id),
    lesson_id INTEGER NOT NULL REFERENCES lesson(id),
    work_type TEXT NOT NULL DEFAULT "text",
    content TEXT DEFAULT "",
    image_path TEXT DEFAULT "",
    display_name TEXT DEFAULT "",
    status TEXT NOT NULL DEFAULT "pending",
    teacher_comment TEXT DEFAULT "",
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quota_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES student(id),
    lesson_id INTEGER NOT NULL REFERENCES lesson(id),
    api_type TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    UNIQUE(student_id, lesson_id, api_type)
);

CREATE TABLE IF NOT EXISTS image_job (
    job_id TEXT PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES student(id),
    lesson_id INTEGER NOT NULL REFERENCES lesson(id),
    prompt TEXT NOT NULL,
    prompt_final TEXT DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'done', 'error')),
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT DEFAULT '',
    source TEXT NOT NULL DEFAULT '' CHECK(source IN ('', 'queue', 'agnes', 'pool', 'pool_fallback', 'error')),
    image_url TEXT DEFAULT '',
    error TEXT DEFAULT '',
    abs_path TEXT DEFAULT '',
    matched_tags TEXT DEFAULT '[]',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_image_job_status_created
ON image_job(status, created_at);

CREATE TABLE IF NOT EXISTS gallery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL REFERENCES class(id),
    submission_id INTEGER NOT NULL REFERENCES submission(id),
    featured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
