import hashlib
from flask import Blueprint, request, redirect, url_for, session, render_template, flash, current_app
from flask_login import login_user, logout_user, current_user, UserMixin
from app import get_db, login_manager

bp = Blueprint("auth", __name__, template_folder="../templates/auth")


class TeacherUser(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.display_name = row["display_name"]

    @property
    def is_teacher(self):
        return True


class StudentUser(UserMixin):
    def __init__(self, student_row, class_id, lesson_id):
        self.id = f"s_{student_row['id']}"
        self.student_id = student_row["id"]
        self.name = student_row["name"]
        self.class_id = class_id
        self.lesson_id = lesson_id

    @property
    def is_teacher(self):
        return False


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    if user_id.startswith("s_"):
        sid = int(user_id[2:])
        row = db.execute("SELECT * FROM student WHERE id=?", (sid,)).fetchone()
        if row:
            lesson_id = session.get("current_lesson_id")
            return StudentUser(row, row["class_id"], lesson_id)
        return None
    row = db.execute("SELECT * FROM teacher WHERE id=?", (int(user_id),)).fetchone()
    if row:
        return TeacherUser(row)
    return None


def _hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


@bp.route("/login", methods=["GET"])
def login_chooser():
    return render_template("auth/chooser.html")


@bp.route("/login/teacher", methods=["GET", "POST"])
def login_teacher():
    if request.method == "GET":
        return render_template("auth/teacher_login.html")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    db = get_db()
    row = db.execute("SELECT * FROM teacher WHERE username=?", (username,)).fetchone()
    if row and row["password_hash"] == _hash_pw(password):
        login_user(TeacherUser(row))
        return redirect(url_for("teacher.dashboard"))
    flash("用户名或密码错误", "error")
    return render_template("auth/teacher_login.html")


@bp.route("/login/student", methods=["GET", "POST"])
def login_student():
    if request.method == "GET":
        class_code = request.args.get("code", "")
        return render_template("auth/student_login.html", class_code=class_code)
    name = request.form.get("name", "").strip()
    phone_tail = request.form.get("phone_tail", "").strip()
    class_code = request.form.get("class_code", "").strip()
    if not name or not class_code:
        flash("请填写姓名和班级码", "error")
        return render_template("auth/student_login.html", class_code=class_code)
    db = get_db()
    cls = db.execute("SELECT * FROM class WHERE class_code=?", (class_code,)).fetchone()
    if not cls:
        flash("班级码无效", "error")
        return render_template("auth/student_login.html", class_code=class_code)
    if phone_tail:
        row = db.execute(
            "SELECT * FROM student WHERE name=? AND phone_tail=? AND class_id=?",
            (name, phone_tail, cls["id"]),
        ).fetchone()
    else:
        candidates = db.execute(
            "SELECT * FROM student WHERE name=? AND class_id=?", (name, cls["id"])
        ).fetchall()
        if len(candidates) == 0:
            flash("未找到你的名字，请向老师确认", "error")
            return render_template("auth/student_login.html", class_code=class_code)
        if len(candidates) > 1:
            flash("有同名同学，请输入手机尾号区分", "error")
            return render_template("auth/student_login.html", class_code=class_code, need_phone=True)
        row = candidates[0]
    if not row:
        flash("姓名或尾号不匹配", "error")
        return render_template("auth/student_login.html", class_code=class_code)
    # find current/upcoming lesson
    lesson = db.execute(
        "SELECT * FROM lesson WHERE class_id=? ORDER BY id DESC LIMIT 1", (cls["id"],)
    ).fetchone()
    lesson_id = lesson["id"] if lesson else 0
    # sign attendance
    try:
        db.execute(
            "INSERT OR IGNORE INTO attendance(student_id, lesson_id) VALUES(?,?)",
            (row["id"], lesson_id),
        )
        db.commit()
    except Exception:
        pass
    user = StudentUser(row, cls["id"], lesson_id)
    session["current_lesson_id"] = lesson_id
    session["current_class_id"] = cls["id"]
    login_user(user)
    return redirect(url_for("student.lesson", lesson_id=lesson_id))


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login_chooser"))
