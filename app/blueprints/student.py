import os, re, uuid, time
from functools import wraps
from flask import Blueprint, request, redirect, url_for, render_template, flash, session, current_app
from flask_login import current_user, login_required
from app import get_db

bp = Blueprint("student", __name__, template_folder="../templates/student")


def student_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.is_teacher:
            flash("此页面仅限学生访问", "error")
            return redirect(url_for("teacher.dashboard"))
        return f(*args, **kwargs)
    return decorated


def parse_lesson_level(name):
    """Extract L1-L10 from lesson name. Returns int 1-10 or None."""
    if not name:
        return None
    m = re.search(r'[Ll]\s*(\d{1,2})', name)
    if m:
        val = int(m.group(1))
        if 1 <= val <= 10:
            return val
    return None


LESSON_CONTENT = {
    1: {
        "title": "L1 - AI是什么",
        "desc": "认识AI，了解人工智能的基本概念",
        "activities": [
            {"type": "discussion", "name": "AI大讨论", "desc": "你觉得什么是AI？生活中有哪些AI？"},
            {"type": "agnes_text", "name": "AI小百科", "desc": "让AI帮你解答关于AI的3个问题"},
            {"type": "agnes_image", "name": "我的AI画像", "desc": "画出你心目中AI的样子",
             "expected_tags": ["robot", "portrait"],
             "default_prompt": "一个可爱的机器人助手，友好地站在教室里",
             "prompt_hint": "描述你心目中的AI长什么样"},
        ],
    },
    2: {
        "title": "L2 - AI能做什么",
        "desc": "探索AI的神奇能力",
        "activities": [
            {"type": "agnes_text", "name": "AI能力清单", "desc": "让AI告诉你它能做什么"},
            {"type": "agnes_image", "name": "AI画世界", "desc": "用AI生成一幅画",
             "expected_tags": ["robot", "landscape"],
             "default_prompt": "AI机器人在世界各地旅行，看到美丽的风景",
             "prompt_hint": "让AI画一幅关于世界/风景的画"},
            {"type": "discussion", "name": "AI vs 人类", "desc": "AI哪些方面比人类强？哪些方面不如人类？"},
        ],
    },
    3: {
        "title": "L3 - AI是怎么学习的",
        "desc": "了解机器学习的基本概念",
        "activities": [
            {"type": "agnes_text", "name": "训练一只AI", "desc": "让AI解释它是怎么学会的"},
            {"type": "agnes_image", "name": "数据画廊", "desc": "用AI画出'学习'的过程",
             "expected_tags": ["robot", "story"],
             "default_prompt": "小机器人在图书馆里认真看书学习",
             "prompt_hint": "画出AI学习的过程"},
            {"type": "create", "name": "我的训练集", "desc": "设计一组给AI的训练数据"},
        ],
    },
    4: {
        "title": "L4 - AI与创意",
        "desc": "用AI激发创意灵感",
        "activities": [
            {"type": "agnes_text", "name": "创意助手", "desc": "让AI帮你构思一个创意故事"},
            {"type": "agnes_image", "name": "AI画师", "desc": "描述一个场景，让AI画出来",
             "expected_tags": ["story", "landscape"],
             "default_prompt": "一个充满想象力的童话城堡，彩虹挂在天上",
             "prompt_hint": "描述一个有创意的场景让AI画"},
            {"type": "create", "name": "创意工坊", "desc": "结合AI建议完成你的作品"},
        ],
    },
    5: {
        "title": "L5 - AI与自然语言",
        "desc": "探索AI理解和生成语言的能力",
        "activities": [
            {"type": "agnes_text", "name": "AI翻译官", "desc": "让AI翻译不同语言或解释词语"},
            {"type": "agnes_text", "name": "AI诗人", "desc": "让AI写一首关于学校的诗"},
            {"type": "create", "name": "对话机器人", "desc": "设计一个你想和AI聊的话题"},
        ],
    },
    6: {
        "title": "L6 - AI与图像",
        "desc": "探索AI的视觉能力",
        "activities": [
            {"type": "agnes_image", "name": "AI画廊", "desc": "用文字描述让AI创作一幅画",
             "expected_tags": ["landscape", "space"],
             "default_prompt": "星空下的美丽森林，有萤火虫在飞舞",
             "prompt_hint": "描述你想让AI画的画面"},
            {"type": "agnes_image", "name": "风格变换", "desc": "让AI用不同风格画同一个主题",
             "expected_tags": ["portrait", "story"],
             "default_prompt": "用卡通风格画一个微笑的小朋友",
             "prompt_hint": "选一个主题，描述想要的风格"},
            {"type": "create", "name": "视觉故事", "desc": "用AI生成的图片编一个故事"},
        ],
    },
    7: {
        "title": "L7 - 编程入门（Scratch）",
        "desc": "在 psm.steam.fun 开始你的编程之旅",
        "activities": [
            {"type": "agnes_text", "name": "编程是什么", "desc": "让AI解释编程是什么"},
            {"type": "agnes_image", "name": "我的第一个程序", "desc": "画出你想象中编程的样子",
             "expected_tags": ["robot", "story"],
             "default_prompt": "一个小朋友在电脑前写代码，屏幕上出现了彩色的程序",
             "prompt_hint": "画出编程/写代码的场景"},
            {"type": "external", "name": "Scratch编程", "desc": "去 psm.steam.fun 完成第一个Scratch作品"},
        ],
    },
    8: {
        "title": "L8 - 编程进阶（Scratch动画）",
        "desc": "用Scratch制作动画和小游戏",
        "activities": [
            {"type": "agnes_text", "name": "动画原理", "desc": "让AI解释动画是怎么做出来的"},
            {"type": "agnes_image", "name": "游戏设计图", "desc": "画出你想做的小游戏画面",
             "expected_tags": ["story", "robot"],
             "default_prompt": "一个有趣的像素风格小游戏画面，有角色和障碍物",
             "prompt_hint": "画出你想象中的小游戏画面"},
            {"type": "external", "name": "Scratch动画", "desc": "去 psm.steam.fun 制作一个动画或小游戏"},
        ],
    },
    9: {
        "title": "L9 - 编程挑战（Python初探）",
        "desc": "尝试用Python解决简单问题",
        "activities": [
            {"type": "agnes_text", "name": "Python小助手", "desc": "让AI教你一个Python小技巧"},
            {"type": "agnes_image", "name": "代码可视化", "desc": "让AI画出代码运行的样子",
             "expected_tags": ["robot", "landscape"],
             "default_prompt": "代码变成彩色的积木块，搭建出一座美丽的城堡",
             "prompt_hint": "把代码/程序想象成画面让AI画"},
            {"type": "external", "name": "Python挑战", "desc": "去 psm.steam.fun 完成Python挑战"},
        ],
    },
    10: {
        "title": "L10 - 作品发布与展示",
        "desc": "展示你这学期的AI创作成果",
        "activities": [
            {"type": "agnes_text", "name": "AI总结", "desc": "让AI帮你总结这学期学到了什么"},
            {"type": "agnes_image", "name": "我的作品海报", "desc": "让AI帮你做一张作品展示海报",
             "expected_tags": ["portrait", "story"],
             "default_prompt": "一个小朋友开心地展示自己的AI创作作品集",
             "prompt_hint": "做一张展示你作品的海报"},
            {"type": "create", "name": "作品集发布", "desc": "整理你的所有作品，准备展示给同学和家长"},
        ],
    },
}


@bp.route("/lesson/<int:lesson_id>")
@student_required
def lesson(lesson_id):
    db = get_db()
    lesson_row = db.execute(
        "SELECT * FROM lesson WHERE id=? AND class_id=?",
        (lesson_id, current_user.class_id),
    ).fetchone()
    if lesson_row:
        lid = lesson_row["id"]
    else:
        lid = current_user.lesson_id or lesson_id
        lesson_row = db.execute(
            "SELECT * FROM lesson WHERE id=? AND class_id=?",
            (lid, current_user.class_id),
        ).fetchone()
    if not lesson_row:
        lesson_row = db.execute(
            "SELECT * FROM lesson WHERE class_id=? ORDER BY id DESC LIMIT 1",
            (current_user.class_id,),
        ).fetchone()
        lid = lesson_row["id"] if lesson_row else lesson_id
    session["current_lesson_id"] = lid
    # Parse level from lesson name; fallback to lesson_id
    if lesson_row:
        level = parse_lesson_level(lesson_row["name"])
    else:
        level = None
    if level is None:
        level = lid if lid and 1 <= lid <= 10 else 1
    content = LESSON_CONTENT.get(level, LESSON_CONTENT[1])
    # get student quota
    text_used = db.execute(
        "SELECT used FROM quota_ledger WHERE student_id=? AND lesson_id=? AND api_type='text'",
        (current_user.student_id, lid),
    ).fetchone()
    image_used = db.execute(
        "SELECT used FROM quota_ledger WHERE student_id=? AND lesson_id=? AND api_type='image'",
        (current_user.student_id, lid),
    ).fetchone()
    quota = {
        "text_used": text_used["used"] if text_used else 0,
        "text_limit": current_app.config["QUOTA_TEXT_PER_LESSON"],
        "image_used": image_used["used"] if image_used else 0,
        "image_limit": current_app.config["QUOTA_IMAGE_PER_LESSON"],
    }
    return render_template(
        "student/lesson.html",
        lesson=lesson_row,
        content=content,
        quota=quota,
        class_id=current_user.class_id,
        lesson_id=lid,
    )


@bp.route("/lesson/<int:lesson_id>/l7l8l9")
@student_required
def external_links(lesson_id):
    return render_template("student/l7l8l9.html", lesson_id=lesson_id)


@bp.route("/lesson/<int:lesson_id>/submit", methods=["POST"])
@student_required
def submit_work(lesson_id):
    work_type = request.form.get("work_type", "text")
    text_content = request.form.get("content", "").strip()
    display_name = request.form.get("display_name", "").strip()
    image_file = request.files.get("image")
    image_path = ""
    if image_file and image_file.filename:
        ext = image_file.filename.rsplit(".", 1)[-1].lower() if "." in image_file.filename else ""
        if ext in current_app.config.get("ALLOWED_IMAGE_EXT", set()) | current_app.config.get("ALLOWED_SCREENSHOT_EXT", set()):
            # Save to student_<sid>/lesson_<lid>/ directory
            sid = current_user.student_id
            lid = lesson_id
            student_dir = f"student_{sid}"
            lesson_dir = f"lesson_{lid}" if lid else "lesson_0"
            save_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], student_dir, lesson_dir)
            os.makedirs(save_dir, exist_ok=True)
            fname = f"{uuid.uuid4().hex}.{ext}"
            image_file.save(os.path.join(save_dir, fname))
            image_path = f"uploads/{student_dir}/{lesson_dir}/{fname}"
        else:
            flash("不支持的图片格式", "error")
            return redirect(url_for("student.lesson", lesson_id=lesson_id))
    if not text_content and not image_path:
        flash("请提交作品内容或图片", "error")
        return redirect(url_for("student.lesson", lesson_id=lesson_id))
    db = get_db()
    db.execute(
        "INSERT INTO submission(student_id, lesson_id, work_type, content, image_path, display_name) VALUES(?,?,?,?,?,?)",
        (current_user.student_id, lesson_id, work_type, text_content, image_path, display_name or current_user.name),
    )
    db.commit()
    flash("作品已提交，等待老师审核", "success")
    return redirect(url_for("student.lesson", lesson_id=lesson_id))


@bp.route("/gallery/<int:class_id>")
@student_required
def gallery(class_id):
    db = get_db()
    items = db.execute(
        "SELECT s.content, s.image_path, s.display_name as work_name, st.display_name as student_display "
        "FROM gallery g JOIN submission s ON g.submission_id=s.id JOIN student st ON s.student_id=st.id "
        "WHERE g.class_id=? ORDER BY g.featured_at DESC",
        (class_id,),
    ).fetchall()
    return render_template("student/gallery.html", items=items, class_id=class_id)


@bp.route("/l10/<int:class_id>")
@student_required
def l10_showcase(class_id):
    db = get_db()
    items = db.execute(
        "SELECT s.*, st.display_name as student_display FROM submission s "
        "JOIN student st ON s.student_id=st.id "
        "WHERE s.status='approved' AND st.class_id=? ORDER BY s.created_at DESC",
        (class_id,),
    ).fetchall()
    return render_template("student/l10_showcase.html", items=items, class_id=class_id)
