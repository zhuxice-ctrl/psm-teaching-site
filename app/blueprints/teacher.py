import os, uuid, json
from functools import wraps
from flask import Blueprint, request, redirect, url_for, render_template, flash, current_app
from flask_login import current_user, login_required
from app import get_db

bp = Blueprint("teacher", __name__, template_folder="../templates/teacher")


def teacher_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_teacher:
            flash("需要教师权限", "error")
            return redirect(url_for("auth.login_chooser"))
        return f(*args, **kwargs)
    return decorated


@bp.route("/dashboard")
@teacher_required
def dashboard():
    db = get_db()
    classes = db.execute(
        "SELECT * FROM class WHERE teacher_id=? ORDER BY created_at DESC",
        (current_user.id,),
    ).fetchall()
    return render_template("teacher/dashboard.html", classes=classes)


@bp.route("/class/create", methods=["POST"])
@teacher_required
def create_class():
    name = request.form.get("name", "").strip()
    semester = request.form.get("semester", "").strip()
    if not name:
        flash("班级名称不能为空", "error")
        return redirect(url_for("teacher.dashboard"))
    code = uuid.uuid4().hex[:6].upper()
    db = get_db()
    db.execute(
        "INSERT INTO class(teacher_id, name, semester, class_code) VALUES(?,?,?,?)",
        (current_user.id, name, semester, code),
    )
    db.commit()
    flash(f"班级已创建，班级码: {code}", "success")
    return redirect(url_for("teacher.dashboard"))


@bp.route("/class/<int:class_id>")
@teacher_required
def class_detail(class_id):
    db = get_db()
    cls = db.execute("SELECT * FROM class WHERE id=? AND teacher_id=?", (class_id, current_user.id)).fetchone()
    if not cls:
        flash("班级不存在", "error")
        return redirect(url_for("teacher.dashboard"))
    lessons = db.execute("SELECT * FROM lesson WHERE class_id=? ORDER BY id DESC", (class_id,)).fetchall()
    students = db.execute("SELECT * FROM student WHERE class_id=? ORDER BY id", (class_id,)).fetchall()
    return render_template("teacher/class_detail.html", cls=cls, lessons=lessons, students=students)


@bp.route("/class/<int:class_id>/lesson/create", methods=["POST"])
@teacher_required
def create_lesson(class_id):
    name = request.form.get("name", "").strip()
    lesson_date = request.form.get("lesson_date", "").strip()
    time_slot = request.form.get("time_slot", "").strip()
    if not name:
        flash("课次名称不能为空", "error")
        return redirect(url_for("teacher.class_detail", class_id=class_id))
    db = get_db()
    db.execute(
        "INSERT INTO lesson(class_id, name, lesson_date, time_slot) VALUES(?,?,?,?)",
        (class_id, name, lesson_date, time_slot),
    )
    db.commit()
    flash("课次已创建", "success")
    return redirect(url_for("teacher.class_detail", class_id=class_id))


@bp.route("/class/<int:class_id>/students/import", methods=["POST"])
@teacher_required
def import_students(class_id):
    raw = request.form.get("student_list", "").strip()
    if not raw:
        flash("学生名单为空", "error")
        return redirect(url_for("teacher.class_detail", class_id=class_id))
    db = get_db()
    added = 0
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if not parts:
            continue
        name = parts[0]
        phone_tail = parts[1] if len(parts) > 1 else ""
        display_name = parts[2] if len(parts) > 2 else name
        try:
            db.execute(
                "INSERT OR IGNORE INTO student(name, phone_tail, display_name, class_id) VALUES(?,?,?,?)",
                (name, phone_tail, display_name, class_id),
            )
            added += 1
        except Exception:
            pass
    db.commit()
    flash(f"已导入 {added} 名学生", "success")
    return redirect(url_for("teacher.class_detail", class_id=class_id))


@bp.route("/class/<int:class_id>/student/delete/<int:student_id>", methods=["POST"])
@teacher_required
def delete_student(class_id, student_id):
    db = get_db()
    db.execute("DELETE FROM student WHERE id=? AND class_id=?", (student_id, class_id))
    db.commit()
    flash("学生已删除", "success")
    return redirect(url_for("teacher.class_detail", class_id=class_id))


@bp.route("/class/<int:class_id>/submissions")
@teacher_required
def submissions(class_id):
    db = get_db()
    cls = db.execute("SELECT * FROM class WHERE id=? AND teacher_id=?", (class_id, current_user.id)).fetchone()
    if not cls:
        flash("班级不存在", "error")
        return redirect(url_for("teacher.dashboard"))
    status_filter = request.args.get("status", "all")
    lesson_filter = request.args.get("lesson_id", "all")
    # Fetch lessons for filter dropdown
    lessons = db.execute("SELECT * FROM lesson WHERE class_id=? ORDER BY id", (class_id,)).fetchall()
    sql = ("SELECT s.*, st.name as student_name, l.name as lesson_name "
           "FROM submission s JOIN student st ON s.student_id=st.id "
           "LEFT JOIN lesson l ON s.lesson_id=l.id "
           "WHERE s.lesson_id IN (SELECT id FROM lesson WHERE class_id=?)")
    params = [class_id]
    if status_filter != "all":
        sql += " AND s.status=?"
        params.append(status_filter)
    if lesson_filter != "all":
        try:
            lid = int(lesson_filter)
            sql += " AND s.lesson_id=?"
            params.append(lid)
        except (ValueError, TypeError):
            pass
    sql += " ORDER BY s.created_at DESC"
    subs = db.execute(sql, params).fetchall()
    return render_template("teacher/submissions.html", cls=cls, submissions=subs,
                           status_filter=status_filter, lesson_filter=lesson_filter,
                           lessons=lessons)


@bp.route("/submission/<int:sub_id>/review", methods=["POST"])
@teacher_required
def review_submission(sub_id):
    action = request.form.get("action", "approve")
    comment = request.form.get("comment", "").strip()
    db = get_db()
    sub = db.execute("SELECT * FROM submission WHERE id=?", (sub_id,)).fetchone()
    if not sub:
        flash("作品不存在", "error")
        return redirect(url_for("teacher.dashboard"))
    new_status = "approved" if action == "approve" else "rejected"
    db.execute("UPDATE submission SET status=?, teacher_comment=? WHERE id=?", (new_status, comment, sub_id))
    if new_status == "approved":
        db.execute(
            "INSERT OR IGNORE INTO gallery(class_id, submission_id) SELECT st.class_id, ? FROM student st WHERE st.id=?",
            (sub_id, sub["student_id"]),
        )
    db.commit()
    flash(f"已{'通过' if action == 'approve' else '驳回'}", "success")
    return redirect(url_for("teacher.submissions", class_id=request.form.get("class_id", 0)))


@bp.route("/class/<int:class_id>/gallery")
@teacher_required
def gallery(class_id):
    db = get_db()
    cls = db.execute("SELECT * FROM class WHERE id=? AND teacher_id=?", (class_id, current_user.id)).fetchone()
    if not cls:
        flash("班级不存在", "error")
        return redirect(url_for("teacher.dashboard"))
    items = db.execute(
        "SELECT g.*, s.content, s.image_path, s.display_name as work_name, st.name as student_name, st.display_name as student_display "
        "FROM gallery g JOIN submission s ON g.submission_id=s.id JOIN student st ON s.student_id=st.id "
        "WHERE g.class_id=? ORDER BY g.featured_at DESC",
        (class_id,),
    ).fetchall()
    return render_template("teacher/gallery.html", cls=cls, items=items)
