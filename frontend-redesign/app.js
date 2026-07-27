/* ============================================================
 * PSM AI 训练营 · 奶油乐园
 * app.js — 数据层 / 路由 / 视图渲染 / 交互逻辑 / 交互特效
 *
 * 设计原则：严格还原原项目（app/templates/* + app/static/*）
 *  - LESSON_CONTENT L1-L10 的活动类型：discussion / agnes_text / agnes_image / create / external
 *  - askText 进度 12%→92%，900ms 间隔，3 段提示，按钮 lock+restore
 *  - askImage 进度 8%→95%，1200ms 间隔，4 段提示，队列轮询 "前面还有 N 个任务"
 *  - 额度：文字 10 + 图片 5 / 每学生每课时
 *  - 教师审核 → 通过的作品进入展示墙
 *  - 登录为演示模式（用户要求）：不校验、不查库，点击直接交互
 *  - 唯一主题：奶油乐园（其余主题 CSS 保留在仓库，可随时切回）
 *  - 交互特效（基于奶油贴纸语言）：入场错位 / 3D 倾斜 / 主按钮磁吸 / 点击爆星 / 提交彩屑 / 进度条 mascot / 额度抖动 / 审核印章
 * ============================================================ */

(function () {
  'use strict';

  /* ============================================================
   * 1. 主题：当前唯一主题 = 奶油乐园。其它主题 CSS 在仓库中保留以便回切。
   * ============================================================ */
  document.body.setAttribute('data-theme', 'creamy');

  /* ============================================================
   * 2. 数据层：localStorage 'psm_db_v1' —— classes/lessons/students/gallery/submissions
   * ============================================================ */
  const DB_KEY = 'psm_db_v1';
  const SESSION_KEY = 'psm_session';

  function loadDB() {
    try {
      const raw = localStorage.getItem(DB_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) { /* fallthrough */ }
    return seedDB();
  }

  function saveDB(db) { localStorage.setItem(DB_KEY, JSON.stringify(db)); }

  function getSession() {
    try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); }
    catch (e) { return null; }
  }

  function setSession(s) {
    if (s) localStorage.setItem(SESSION_KEY, JSON.stringify(s));
    else localStorage.removeItem(SESSION_KEY);
  }

  let DB = loadDB();

  /* ============================================================
   * 3. LESSON_CONTENT —— 严格还原原 blueprints/student.py
   *    L1-L10，每课时含 activities / quota / 默认 prompt
   * ============================================================ */
  const LESSON_CONTENT = {
    L1: {
      title: 'L1 · AI 是什么？',
      desc: '认识人工智能：和你聊天的、会画画的、写故事的，到底都是什么？',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'discussion', prompt: '说一个你今天用过的"AI"——它帮你做了什么？' },
        { type: 'agnes_text',  prompt: '问问 AI：「你觉得什么是智能？」' },
        { type: 'agnes_image', prompt: '让 AI 画一张「机器人在教室里上课」' },
        { type: 'create',      prompt: '把你和 AI 的对话写下来，做成一张小卡片' }
      ],
      text_pool: [
        '智能是一种能根据环境调整自己行为的能力。比如我认出"红灯停、绿灯行"就是一种简单的智能。',
        '智能包含感知、理解、推理和决策。AI 在某些任务上已经超过人类，但通用智能还远着呢。',
        '我觉得智能不只是答题对不对，还包括"知道自己不知道"——AI 离这一步还有距离。'
      ]
    },
    L2: {
      title: 'L2 · 和 AI 聊聊天',
      desc: '学会向 AI 提问：怎么问，决定了它怎么答。',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'agnes_text',  prompt: '试试用「角色 + 任务 + 限制」三段式提问' },
        { type: 'discussion',  prompt: '把你得到的回答贴出来，对比同学的提问' }
      ],
      text_pool: [
        '好的提问要明确角色、说清任务、给出限制。比如"假设你是 5 年级老师，用 3 句话解释光合作用"。',
        '我让 AI 写一首关于秋天的诗，比"写首诗"具体多了，它给出的句子更对景。'
      ]
    },
    L3: {
      title: 'L3 · AI 怎么"看"世界',
      desc: '计算机视觉入门：图片是怎么被机器理解的？',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'agnes_image', prompt: '让 AI 画一张「机器人在图书馆读书」' },
        { type: 'discussion',  prompt: '观察图片细节，AI 是不是画错了什么？' }
      ],
      text_pool: [
        '我把机器人画到图书馆里，它把书摆得很整齐——但手指的关节还是有点怪。',
        'AI 是按"概念组合"画画的：图书馆有书架、机器人有金属感。'
      ]
    },
    L4: {
      title: 'L4 · 让 AI 当小画家',
      desc: '图像生成的提示词：把"脑海里的画面"翻译成 AI 听得懂的话。',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'agnes_image', prompt: '让 AI 画「机器人去旅行」' },
        { type: 'agnes_text',  prompt: '把你画面的关键词列出来：主体 / 场景 / 风格 / 氛围' }
      ],
      text_pool: [
        '关键词拆成主体、场景、风格、氛围四块，AI 就不容易跑偏。',
        '我加上了"日落""胶片质感"，画面立刻比"机器人旅行"高级了一档。'
      ]
    },
    L5: {
      title: 'L5 · AI 的"超"与"不超"',
      desc: '了解 AI 的能力边界：它强在哪里，弱在哪里。',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'agnes_text',  prompt: '问 AI："你最不擅长做什么？为什么？"' },
        { type: 'discussion',  prompt: '挑一个任务，测试 AI 会不会"一本正经地胡说"' }
      ],
      text_pool: [
        'AI 擅长在大量数据里找模式，但"真假"它判断不了，只能算"像不像"。',
        '我让它编一个不存在的历史人物，它编得特别像，但事实全是假的——这就是幻觉。'
      ]
    },
    L6: {
      title: 'L6 · 和 AI 一起写故事',
      desc: '共创写作：让 AI 当你的第一读者和提词器。',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'agnes_text',  prompt: '给 AI 一个开头，让它接一段' },
        { type: 'agnes_image', prompt: '为你的故事画一张封面' },
        { type: 'create',      prompt: '把故事写完整，标题、角色、转折都要有' }
      ],
      text_pool: [
        '好的共创不是让 AI 全写，而是它提三个方向、你选一个、再改写。',
        '我把"机器人在图书馆读书"和"机器人去旅行"缝在一起，做了个短篇。'
      ]
    },
    L7: {
      title: 'L7 · 编程世界登场',
      desc: '和 Scratch / Python 打个招呼：代码是另一种"语言"。',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'external',  prompt: '到 psm.steam.fun 打开「第一关」' },
        { type: 'discussion', prompt: '把第一关的运行截图上传到这里，写一句收获' }
      ],
      text_pool: [
        'Scratch 里的"积木"其实就是代码块——拖一拖、拼一拼，程序就跑起来了。',
        '我让小猫转一圈并发出"喵"，用了"重复 10 次"和"播放声音"两个积木。'
      ]
    },
    L8: {
      title: 'L8 · 顺序 / 循环 / 判断',
      desc: '三大基本结构：所有程序都是它们搭出来的。',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'external',  prompt: '到 psm.steam.fun 试一下"如果…那么…"' },
        { type: 'discussion', prompt: '用一个生活例子解释什么是"条件判断"' }
      ],
      text_pool: [
        '条件判断就是"如果明天下雨，我就带伞"——程序也是这样。',
        '我做了个小游戏：碰到边缘就反弹，碰到红色就 Game Over。'
      ]
    },
    L9: {
      title: 'L9 · 我也能写小游戏',
      desc: '把你学到的所有东西，做成一个能玩的小作品。',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'external',   prompt: '到 psm.steam.fun 开始你的小项目' },
        { type: 'discussion',  prompt: '上传运行截图，讲讲你做了什么' }
      ],
      text_pool: [
        '我把"小猫接苹果"做完了，加了分数和失败音效，超有成就感。',
        '我做了一个迷宫生成器：每次刷新都不一样，AI 都不能每次相同。'
      ]
    },
    L10: {
      title: 'L10 · 我的作品集',
      desc: '把这一路做过的故事、图画、游戏截图，集结成你的一本作品集。',
      quota: { text: 10, image: 5 },
      activities: [
        { type: 'create', prompt: '挑 3 件你最满意的作品，给它们写一段介绍' }
      ],
      text_pool: [
        '我挑了 L1 的 AI 答题、L4 的画、L9 的小游戏——刚好覆盖三种能力。',
        '作品集不只是结果集，更是"我怎么走到这里"的笔记。'
      ]
    }
  };

  /* ============================================================
   * 4. 种子数据（首次打开自动建一个示例班级 / 名册 / 作品）
   * ============================================================ */
  function seedDB() {
    const now = Date.now();
    const db = {
      classes: [
        {
          id: 'c1', code: 'A1B2C3', name: '示例班 · 周六上午',
          semester: '2026 春季',
          created_at: now,
          lessons: [
            { id: 'l1', level: 'L1', name: 'L1 · AI 是什么？',    lesson_date: '2026-07-26', time_slot: '09:00-10:30' },
            { id: 'l2', level: 'L2', name: 'L2 · 和 AI 聊聊天',   lesson_date: '2026-08-02', time_slot: '09:00-10:30' },
            { id: 'l3', level: 'L3', name: 'L3 · AI 怎么"看"世界', lesson_date: '2026-08-09', time_slot: '09:00-10:30' },
            { id: 'l4', level: 'L4', name: 'L4 · 让 AI 当小画家',   lesson_date: '2026-08-16', time_slot: '09:00-10:30' },
            { id: 'l5', level: 'L5', name: 'L5 · AI 的"超"与"不超"', lesson_date: '2026-08-23', time_slot: '09:00-10:30' },
            { id: 'l6', level: 'L6', name: 'L6 · 和 AI 一起写故事', lesson_date: '2026-08-30', time_slot: '09:00-10:30' },
            { id: 'l7', level: 'L7', name: 'L7 · 编程世界登场',     lesson_date: '2026-09-06', time_slot: '09:00-10:30' },
            { id: 'l8', level: 'L8', name: 'L8 · 顺序 / 循环 / 判断', lesson_date: '2026-09-13', time_slot: '09:00-10:30' },
            { id: 'l9', level: 'L9', name: 'L9 · 我也能写小游戏',   lesson_date: '2026-09-20', time_slot: '09:00-10:30' },
            { id: 'l10', level: 'L10', name: 'L10 · 我的作品集',   lesson_date: '2026-09-27', time_slot: '09:00-10:30' }
          ],
          students: [
            { id: 's1', name: '小明', phone_tail: '1234', display: '小明' },
            { id: 's2', name: '小红', phone_tail: '5678', display: '小红' },
            { id: 's3', name: '小芳', phone_tail: '',    display: '小芳' },
            { id: 's4', name: '小伟', phone_tail: '4321', display: '小伟' },
            { id: 's5', name: '小丽', phone_tail: '8765', display: '小丽' },
            { id: 's6', name: '小刚', phone_tail: '',    display: '小刚' }
          ]
        }
      ],
      gallery: [
        { id: 'g1', class_id: 'c1', lesson_id: 'l3', student_id: 's1', student_name: '小明',
          work_type: 'image', image: 'assets/images/img3_robot_library.jpeg', source: 'ai',
          content: '我让 AI 画"机器人在图书馆"，它把书摆得很整齐，但手指的关节还是有点怪。',
          created_at: now - 86400000 * 5 },
        { id: 'g2', class_id: 'c1', lesson_id: 'l4', student_id: 's2', student_name: '小红',
          work_type: 'image', image: 'assets/images/img2_robot_travel.jpeg', source: 'ai',
          content: '「机器人去旅行」+ 胶片质感 + 日落，整张图一下子高级了起来。',
          created_at: now - 86400000 * 4 },
        { id: 'g3', class_id: 'c1', lesson_id: 'l4', student_id: 's3', student_name: '小芳',
          work_type: 'image', image: 'assets/images/img1_robot_classroom.jpeg', source: 'ai',
          content: '「机器人在教室里上课」——AI 还给它画了粉笔和黑板，超可爱。',
          created_at: now - 86400000 * 3 },
        { id: 'g4', class_id: 'c1', lesson_id: 'l5', student_id: 's4', student_name: '小伟',
          work_type: 'text', image: '', source: 'ai',
          content: '我问 AI"你最不擅长什么"，它说"判断真假"。我觉得它说的是实话。',
          created_at: now - 86400000 * 2 },
        { id: 'g5', class_id: 'c1', lesson_id: 'l6', student_id: 's5', student_name: '小丽',
          work_type: 'mixed', image: 'assets/images/img4_fairy_castle.jpeg', source: 'ai',
          content: '我让 AI 写了一段精灵城堡的故事，又画了一张封面，超有感觉。',
          created_at: now - 86400000 }
      ],
      submissions: [
        { id: 'sub1', class_id: 'c1', lesson_id: 'l1', student_id: 's1', student_name: '小明',
          work_type: 'text', content: '今天我用 AI 查了"为什么天空是蓝的"，它说了一堆散射。',
          image: '', source: 'manual', status: 'pending', comment: '',
          created_at: now - 86400000 * 0.3 },
        { id: 'sub2', class_id: 'c1', lesson_id: 'l1', student_id: 's2', student_name: '小红',
          work_type: 'mixed', content: '让 AI 帮我写的自我介绍，它说我"热情、爱画画"。',
          image: 'assets/images/img6_kid_showcase.jpeg', source: 'ai', status: 'pending', comment: '',
          created_at: now - 86400000 * 0.2 },
        { id: 'sub3', class_id: 'c1', lesson_id: 'l3', student_id: 's3', student_name: '小芳',
          work_type: 'image', content: 'AI 画的星空森林。',
          image: 'assets/images/img5_starry_forest.jpeg', source: 'ai', status: 'pending', comment: '',
          created_at: now - 86400000 * 0.1 }
      ]
    };
    saveDB(db);
    return db;
  }

  /* ============================================================
   * 5. 通用工具
   * ============================================================ */
  function uid(prefix) { return prefix + '_' + Math.random().toString(36).slice(2, 9) + Date.now().toString(36).slice(-3); }

  function escapeHTML(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function showFlash(category, msg) {
    const host = document.getElementById('flash');
    if (!host) return;
    host.innerHTML = `<div class="flash ${category}">${escapeHTML(msg)}</div>`;
    setTimeout(() => { if (host) host.innerHTML = ''; }, 3200);
  }

  function pickFromPool(pool, seed) {
    if (!pool || !pool.length) return '';
    return pool[seed % pool.length];
  }

  function pickImageForPrompt(prompt) {
    // 关键词 → 6 张图 简单路由
    if (!prompt) return 'assets/images/img1_robot_classroom.jpeg';
    const p = prompt.toLowerCase();
    if (p.includes('教室') || p.includes('classroom')) return 'assets/images/img1_robot_classroom.jpeg';
    if (p.includes('旅行') || p.includes('travel'))     return 'assets/images/img2_robot_travel.jpeg';
    if (p.includes('图书馆') || p.includes('library'))  return 'assets/images/img3_robot_library.jpeg';
    if (p.includes('城堡') || p.includes('精灵') || p.includes('castle')) return 'assets/images/img4_fairy_castle.jpeg';
    if (p.includes('星空') || p.includes('森林') || p.includes('star'))  return 'assets/images/img5_starry_forest.jpeg';
    if (p.includes('作品') || p.includes('showcase'))  return 'assets/images/img6_kid_showcase.jpeg';
    // 兜底
    const all = ['img1_robot_classroom','img2_robot_travel','img3_robot_library',
                 'img4_fairy_castle','img5_starry_forest','img6_kid_showcase'];
    const idx = (prompt.length * 7) % all.length;
    return 'assets/images/' + all[idx] + '.jpeg';
  }

  /* ============================================================
   * 6. 路由：showView + history.pushState + nav 渲染
   * ============================================================ */
  const VIEWS = ['chooser', 'student-login', 'teacher-login', 'lesson',
                 'l7l8l9', 'gallery', 'l10',
                 'dashboard', 'class', 'submissions'];

  function showView(name, opts) {
    opts = opts || {};
    if (!VIEWS.includes(name)) name = 'chooser';
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const target = document.getElementById('v-' + name);
    if (target) target.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });

    // 视图进入时调用对应渲染器
    if (name === 'lesson')      renderLesson();
    if (name === 'gallery')     renderGallery();
    if (name === 'l10')         renderL10();
    if (name === 'l7l8l9')      renderL7L8L9();
    if (name === 'dashboard')   renderDashboard();
    if (name === 'class')       renderClassDetail();
    if (name === 'submissions') renderSubmissions();

    // 视图进入时为新渲染的节点挂上交互特效（磁吸 / 3D 倾斜 / glare）
    if (target) {
      // 推迟一帧，让 stagger 动画先计算一次
      requestAnimationFrame(() => {
        FX.bindMagnetic(target);
        FX.bindTilt(target);
      });
    }

    if (!opts.skipHistory) {
      const url = new URL(location.href);
      url.hash = '#' + name;
      history.pushState({ view: name }, '', url.toString());
    }
    renderNav();
  }

  function renderNav() {
    const host = document.getElementById('nav-links');
    if (!host) return;
    const s = getSession();
    if (!s) {
      host.innerHTML = '<a href="#" data-link="chooser">登录</a>';
      return;
    }
    if (s.role === 'student') {
      host.innerHTML =
        '<a href="#" data-link="lesson">当前课程</a>' +
        '<a href="#" data-link="gallery">展示墙</a>' +
        '<a href="#" data-link="l10">L10 作品集</a>' +
        '<a href="#" data-link="l7l8l9">编程世界</a>' +
        '<a href="#" id="nav-logout">退出</a>';
    } else if (s.role === 'teacher') {
      host.innerHTML =
        '<a href="#" data-link="dashboard">教师后台</a>' +
        (s.class_id ? '<a href="#" data-link="class">班级管理</a>' : '') +
        '<a href="#" data-link="submissions">作品审核</a>' +
        '<a href="#" id="nav-logout">退出</a>';
    }
  }

  // 全局链接点击（data-link）+ 演示直达（data-demo-enter）
  document.addEventListener('click', e => {
    const demo = e.target.closest('[data-demo-enter]');
    if (demo) {
      e.preventDefault();
      demoEnter(demo.dataset.demoEnter);
      return;
    }
    const link = e.target.closest('[data-link]');
    if (link) {
      e.preventDefault();
      showView(link.dataset.link);
      return;
    }
    if (e.target.closest('#nav-logout')) {
      e.preventDefault();
      setSession(null);
      showFlash('info', '已退出登录');
      showView('chooser');
      return;
    }
  });

  // 浏览器前进 / 后退
  window.addEventListener('popstate', e => {
    const v = (e.state && e.state.view) || (location.hash || '').replace('#','') || 'chooser';
    showView(v, { skipHistory: true });
  });

  // 交互特效：主按钮点击 → 星星爆开（在路由 click handler 之后注册，单独走 capture=false 即可）
  document.addEventListener('click', e => {
    const btn = e.target.closest('.btn.primary');
    if (!btn || btn.disabled) return;
    // 提交流程的彩屑由 bindSubmitWork 自行处理，这里只管普通点击的星星
    if (btn.closest('form')) return;
    const r = btn.getBoundingClientRect();
    const x = e.clientX || (r.left + r.width / 2);
    const y = e.clientY || (r.top + r.height / 2);
    const isImage = btn.dataset.askImage != null;
    FX.clickBurst(x, y, isImage ? 'image' : 'text');
  });

  /* ============================================================
   * 7. 鉴权 —— 演示模式：登录页直接越过
   *    不连数据库、不做任何校验；点击按钮即进入对应身份。
   *    留空字段自动补演示值（小明 / A1B2C3 / 演示老师）。
   * ============================================================ */
  function ensureDemoClass() {
    if (!DB.classes || !DB.classes.length) DB = seedDB();
    return DB.classes[0];
  }

  // 选择页「免登录直达」
  function demoEnter(role) {
    const cls = ensureDemoClass();
    if (role === 'teacher') {
      setSession({ role: 'teacher', username: '演示老师', class_id: cls.id });
      showFlash('success', '演示模式：已直接进入教师后台');
      showView('dashboard');
      return;
    }
    let stu = cls.students[0];
    if (!stu) {
      stu = { id: uid('s'), name: '小明', phone_tail: '', display: '小明' };
      cls.students.push(stu);
      saveDB(DB);
    }
    setSession({ role: 'student', name: stu.name, display: stu.display, class_id: cls.id, student_id: stu.id });
    showFlash('success', '演示模式：已直接进入课堂（' + stu.display + '）');
    showView('lesson');
  }

  function bindAuthForms() {
    // 学生：无校验直通；姓名不在名册就现场加入，保证演示不卡壳
    const fS = document.getElementById('form-student-login');
    if (fS) {
      fS.addEventListener('submit', e => {
        e.preventDefault();
        const fd = new FormData(fS);
        const name = String(fd.get('name') || '').trim() || '小明';
        const phone_tail = String(fd.get('phone_tail') || '').trim();
        const class_code = String(fd.get('class_code') || '').trim().toUpperCase() || 'A1B2C3';
        ensureDemoClass();
        const cls = DB.classes.find(c => c.code === class_code) || DB.classes[0];
        let student = cls.students.find(s => s.name === name && (!phone_tail || s.phone_tail === phone_tail));
        if (!student) {
          student = { id: uid('s'), name: name, phone_tail: phone_tail, display: name };
          cls.students.push(student);
          saveDB(DB);
        }
        setSession({ role: 'student', name: student.name, display: student.display, class_id: cls.id, student_id: student.id });
        showFlash('success', '演示模式：欢迎，' + student.display);
        showView('lesson');
      });
    }
    // 老师：无校验直通
    const fT = document.getElementById('form-teacher-login');
    if (fT) {
      fT.addEventListener('submit', e => {
        e.preventDefault();
        const fd = new FormData(fT);
        const u = String(fd.get('username') || '').trim() || '演示老师';
        const cls = ensureDemoClass();
        setSession({ role: 'teacher', username: u, class_id: cls.id });
        showFlash('success', '演示模式：已进入教师后台');
        showView('dashboard');
      });
    }
  }



  /* ============================================================
   * 8. 课时页：quota-bar / 活动卡 / askText / askImage
   *    严格还原原 lesson.html 的进度条假动画 + 按钮 lock+restore
   * ============================================================ */
  const textLocks  = new Set();
  const imageLocks = new Set();
  const imageQueues = {}; // idx -> 剩余排队数

  function getStudentLessonState() {
    const s = getSession();
    if (!s || s.role !== 'student') return null;
    if (!s.class_id) return null;
    const cls = DB.classes.find(c => c.id === s.class_id);
    if (!cls) return null;
    const today = '2026-07-27'; // 沙箱时间
    let lesson = cls.lessons.find(l => l.lesson_date >= today) || cls.lessons[cls.lessons.length - 1];
    if (!lesson) lesson = cls.lessons[0];
    return { cls: cls, lesson: lesson };
  }

  function getQuotaUsed(lessonId, studentId) {
    const counts = { text: 0, image: 0 };
    DB.submissions.forEach(sub => {
      if (sub.lesson_id === lessonId && sub.student_id === studentId && (sub.source === 'ai' || sub.source === 'manual')) {
        if (sub.work_type === 'image') counts.image++;
        else if (sub.work_type === 'text') counts.text++;
        else if (sub.work_type === 'mixed') { counts.text++; counts.image++; }
      }
    });
    return counts;
  }

  function renderLesson() {
    const ctx = getStudentLessonState();
    if (!ctx) { showView('chooser'); return; }
    const content = LESSON_CONTENT[ctx.lesson.level] || LESSON_CONTENT.L1;
    document.getElementById('lesson-title').textContent = content.title;
    document.getElementById('lesson-desc').textContent = content.desc;

    // quota
    const used = getQuotaUsed(ctx.lesson.id, getSession().student_id);
    const q = content.quota;
    const qb = document.getElementById('quota-bar');
    qb.innerHTML = `
      <div class="quota-slot" data-type="text">
        <span class="lbl">文字额度</span>
        <span class="dots">${Array.from({length: q.text}, (_,i) =>
          `<i class="${i < used.text ? 'on' : ''}"></i>`).join('')}</span>
        <span class="num">${used.text}/${q.text}</span>
      </div>
      <div class="quota-slot" data-type="image">
        <span class="lbl">图片额度</span>
        <span class="dots">${Array.from({length: q.image}, (_,i) =>
          `<i class="${i < used.image ? 'on' : ''}"></i>`).join('')}</span>
        <span class="num">${used.image}/${q.image}</span>
      </div>`;

    // activities
    const acts = document.getElementById('activities');
    acts.classList.add('fx-stagger');
    acts.innerHTML = content.activities.map((a, idx) => renderActivityCard(a, idx, content, ctx, used)).join('');

    // 活动卡上的 textarea 已经渲染时填充了 prompt 作为 placeholder，默认值为 prompt
    // 这里不需要额外处理。

    // 绑定活动卡交互
    bindActivities(content, ctx, used);

    // 提交作品
    bindSubmitWork(ctx);
  }

  function renderActivityCard(a, idx, content, ctx, used) {
    const type = a.type;
    const pHint = a.prompt || '';
    if (type === 'discussion') {
      return `
        <div class="activity-card" data-type="discussion" data-idx="${idx}">
          <div class="type-tag">讨论</div>
          <div class="activity-prompt">${escapeHTML(pHint)}</div>
          <div class="activity-result" data-result></div>
        </div>`;
    }
    if (type === 'agnes_text') {
      const left = content.quota.text - used.text;
      const disabled = left <= 0;
      return `
        <div class="activity-card" data-type="agnes_text" data-idx="${idx}">
          <div class="type-tag">问 AI</div>
          <div class="activity-prompt">${escapeHTML(pHint)}</div>
          <textarea data-input rows="3" placeholder="把问题说得更具体，比如加上角色、限制...">${escapeHTML(pHint)}</textarea>
          <div class="activity-actions">
            <button class="btn primary" data-ask-text data-idx="${idx}" ${disabled ? 'disabled' : ''}>
              问 AI · 剩余 ${left} 次
            </button>
          </div>
          <div class="ai-progress" data-progress style="display:none">
            <div class="ai-progress-bar"><div class="ai-progress-fill"></div></div>
            <div class="fx-progress-mascot" data-mascot>🦄</div>
            <div class="ai-progress-text"></div>
          </div>
          <div class="activity-result" data-result></div>
        </div>`;
    }
    if (type === 'agnes_image') {
      const left = content.quota.image - used.image;
      const disabled = left <= 0;
      return `
        <div class="activity-card" data-type="agnes_image" data-idx="${idx}">
          <div class="type-tag">让 AI 画</div>
          <div class="activity-prompt">${escapeHTML(pHint)}</div>
          <textarea data-input rows="2" placeholder="把画面拆成：主体 + 场景 + 风格 + 氛围...">${escapeHTML(pHint)}</textarea>
          <div class="activity-actions">
            <button class="btn primary" data-ask-image data-idx="${idx}" ${disabled ? 'disabled' : ''}>
              让 AI 画 · 剩余 ${left} 次
            </button>
          </div>
          <div class="ai-progress" data-progress style="display:none">
            <div class="ai-progress-bar"><div class="ai-progress-fill"></div></div>
            <div class="fx-progress-mascot" data-mascot>🎨</div>
            <div class="ai-progress-text"></div>
          </div>
          <div class="activity-result" data-result></div>
        </div>`;
    }
    if (type === 'create') {
      return `
        <div class="activity-card" data-type="create" data-idx="${idx}">
          <div class="type-tag">创作</div>
          <div class="activity-prompt">${escapeHTML(pHint)}</div>
          <div class="activity-result" data-result></div>
        </div>`;
    }
    if (type === 'external') {
      return `
        <div class="activity-card" data-type="external" data-idx="${idx}">
          <div class="type-tag">外链</div>
          <div class="activity-prompt">${escapeHTML(pHint)}</div>
          <a href="https://psm.steam.fun" target="_blank" rel="noopener" class="btn">前往 psm.steam.fun →</a>
        </div>`;
    }
    return '';
  }

  function bindActivities(content, ctx, used) {
    const root = document.getElementById('activities');

    root.querySelectorAll('[data-ask-text]').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = btn.dataset.idx;
        if (textLocks.has(idx)) return;
        const card = btn.closest('.activity-card');
        const input = card.querySelector('[data-input]').value.trim();
        const cur = getQuotaUsed(ctx.lesson.id, getSession().student_id);
        if (cur.text >= content.quota.text) {
          showFlash('error', '本课时文字额度已用完');
          FX.shakeCard(card);
          return;
        }
        askText(idx, input || content.activities[idx].prompt, content, ctx);
      });
    });

    root.querySelectorAll('[data-ask-image]').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = btn.dataset.idx;
        if (imageLocks.has(idx)) return;
        const card = btn.closest('.activity-card');
        const input = card.querySelector('[data-input]').value.trim();
        const cur = getQuotaUsed(ctx.lesson.id, getSession().student_id);
        if (cur.image >= content.quota.image) {
          showFlash('error', '本课时图片额度已用完');
          FX.shakeCard(card);
          return;
        }
        askImage(idx, input || content.activities[idx].prompt, content, ctx);
      });
    });
  }

  /* ----- askText：12%→92%，900ms 间隔，3 段提示，按钮 lock+restore ----- */
  function askText(idx, promptText, content, ctx) {
    const card = document.querySelector(`.activity-card[data-type="agnes_text"][data-idx="${idx}"]`);
    if (!card) return;
    const btn = card.querySelector('[data-ask-text]');
    const progress = card.querySelector('[data-progress]');
    const fill = progress.querySelector('.ai-progress-fill');
    const text = progress.querySelector('.ai-progress-text');
    const result = card.querySelector('[data-result]');

    textLocks.add(idx);
    btn.disabled = true;
    progress.style.display = '';
    fill.style.width = '12%';
    text.textContent = '正在让 AI 思考...';
    FX.startProgressMascot(progress);

    const stages = ['正在让 AI 思考...', '正在整理语言...', '马上就好...'];
    let pct = 12;
    let step = 0;
    const timer = setInterval(() => {
      pct = Math.min(92, pct + (92 - 12) / 8);
      fill.style.width = pct.toFixed(0) + '%';
      if (step < stages.length && pct > 12 + (92 - 12) * (step + 1) / stages.length) {
        text.textContent = stages[step];
        step++;
      }
      if (pct >= 92) clearInterval(timer);
    }, 900);

    setTimeout(() => {
      clearInterval(timer);
      fill.style.width = '100%';
      text.textContent = '生成完成';
      const answer = pickFromPool(content.text_pool || LESSON_CONTENT.L1.text_pool, Date.now() + idx.charCodeAt(0));
      result.innerHTML = `
        <div class="ai-answer">
          <div class="ai-answer-head">AI 回答 · 来源 agnes_text</div>
          <div class="ai-answer-body">${escapeHTML(answer)}</div>
        </div>`;
      textLocks.delete(idx);

      // 落库：作为 AI 文字 submission
      const sess = getSession();
      DB.submissions.push({
        id: uid('sub'), class_id: ctx.cls.id, lesson_id: ctx.lesson.id,
        student_id: sess.student_id, student_name: sess.display,
        work_type: 'text', content: promptText + '\n\n【AI 答】' + answer,
        image: '', source: 'ai', status: 'pending', comment: '',
        created_at: Date.now()
      });
      saveDB(DB);
      // 刷新 quota
      renderLesson();
      showFlash('success', 'AI 回答已生成');
    }, 900 * 9); // ~8.1s
  }

  /* ----- askImage：8%→95%，1200ms 间隔，4 段提示，队列轮询 ----- */
  function askImage(idx, promptText, content, ctx) {
    const card = document.querySelector(`.activity-card[data-type="agnes_image"][data-idx="${idx}"]`);
    if (!card) return;
    const btn = card.querySelector('[data-ask-image]');
    const progress = card.querySelector('[data-progress]');
    const fill = progress.querySelector('.ai-progress-fill');
    const text = progress.querySelector('.ai-progress-text');
    const result = card.querySelector('[data-result]');

    imageLocks.add(idx);
    btn.disabled = true;
    progress.style.display = '';
    fill.style.width = '8%';
    FX.startProgressMascot(progress);

    // 队列模拟：当前前面可能还有 0~2 个任务
    imageQueues[idx] = Math.floor(Math.random() * 3);
    const stages = ['提交画图任务...', '排队中...', 'AI 正在作画...', '即将完成...'];
    let pct = 8;
    let stageIdx = 0;
    text.textContent = stages[0] + (imageQueues[idx] > 0 ? ` 前面还有 ${imageQueues[idx]} 个任务` : '');

    const timer = setInterval(() => {
      pct = Math.min(95, pct + (95 - 8) / 10);
      fill.style.width = pct.toFixed(0) + '%';
      // 队列慢慢消化
      if (pct > 30 && imageQueues[idx] > 0) imageQueues[idx]--;
      const queueNote = imageQueues[idx] > 0 ? ` 前面还有 ${imageQueues[idx]} 个任务` : '';
      if (stageIdx < stages.length) {
        text.textContent = stages[stageIdx] + queueNote;
        if (pct > 8 + (95 - 8) * (stageIdx + 1) / stages.length) stageIdx++;
      } else {
        text.textContent = stages[stages.length - 1] + queueNote;
      }
      if (pct >= 95) clearInterval(timer);
    }, 1200);

    setTimeout(() => {
      clearInterval(timer);
      fill.style.width = '100%';
      text.textContent = '生成完成';
      const imagePath = pickImageForPrompt(promptText);
      result.innerHTML = `
        <div class="ai-answer">
          <div class="ai-answer-head">AI 画作 · 来源 agnes_image</div>
          <img src="${escapeHTML(imagePath)}" alt="AI 生成图" class="ai-image" loading="lazy">
          <div class="ai-answer-body">${escapeHTML(promptText)}</div>
        </div>`;
      imageLocks.delete(idx);

      const sess = getSession();
      DB.submissions.push({
        id: uid('sub'), class_id: ctx.cls.id, lesson_id: ctx.lesson.id,
        student_id: sess.student_id, student_name: sess.display,
        work_type: 'image', content: promptText,
        image: imagePath, source: 'ai', status: 'pending', comment: '',
        created_at: Date.now()
      });
      saveDB(DB);
      renderLesson();
      showFlash('success', 'AI 画作已生成');
    }, 1200 * 11); // ~13.2s
  }

  /* ----- 提交作品（L1 / 通用） ----- */
  function bindSubmitWork(ctx) {
    const f = document.getElementById('form-submit-work');
    if (!f) return;
    f.onsubmit = e => {
      e.preventDefault();
      const fd = new FormData(f);
      const name = String(fd.get('display_name') || '').trim();
      const content = String(fd.get('content') || '').trim();
      const file = fd.get('image');
      if (!name && !content && !(file && file.size)) {
        showFlash('error', '至少填一个字段再提交');
        return;
      }
      const sess = getSession();
      let work_type = 'text';
      if (file && file.size) work_type = content ? 'mixed' : 'image';

      // 文件 → DataURL（存到 localStorage 受限，所以只记文件信息；图片预选用 assets）
      const imagePath = (file && file.size) ? '' : ''; // 没有就用空，审核列表显示"已上传"
      DB.submissions.push({
        id: uid('sub'), class_id: ctx.cls.id, lesson_id: ctx.lesson.id,
        student_id: sess.student_id, student_name: sess.display,
        work_type: work_type,
        display_name: name || sess.display + ' 的作品',
        content: content || '(无文字)',
        image: imagePath, source: 'manual', status: 'pending', comment: '',
        created_at: Date.now()
      });
      saveDB(DB);
      f.reset();
      showFlash('success', '作品已提交，等待老师审核');
      // 彩屑：从提交按钮位置喷出
      const submitBtn = f.querySelector('button[type="submit"]');
      if (submitBtn) {
        const r = submitBtn.getBoundingClientRect();
        FX.submitConfetti(r.left + r.width / 2, r.top + r.height / 2);
      }
    };
  }



  /* ============================================================
   * 9. 展示墙 / L10 作品集 / L7-L9 编程世界
   * ============================================================ */
  function getCurrentStudentClass() {
    const s = getSession();
    if (!s || !s.class_id) return null;
    return DB.classes.find(c => c.id === s.class_id) || null;
  }

  function renderGallery() {
    const cls = getCurrentStudentClass();
    if (!cls) { showView('chooser'); return; }
    const items = DB.gallery.filter(g => g.class_id === cls.id);
    const body = document.getElementById('gallery-body');
    if (!items.length) {
      body.innerHTML = '<div class="empty">展示墙还空着——做点什么，提交给老师审核吧。</div>';
      return;
    }
    body.innerHTML = `
      <div class="gallery-grid fx-stagger">
        ${items.map(it => renderGalleryCard(it, false)).join('')}
      </div>`;
  }

  function renderL10() {
    const cls = getCurrentStudentClass();
    if (!cls) { showView('chooser'); return; }
    const items = DB.gallery.filter(g => g.class_id === cls.id);
    const featured = items.slice(0, 4);
    const body = document.getElementById('l10-body');
    if (!items.length) {
      body.innerHTML = '<div class="empty">还没有作品集哦，先去做几个作品吧。</div>';
      return;
    }
    body.innerHTML = `
      <div class="l10-feature">
        <div class="l10-feature-main">
          ${renderGalleryCard(featured[0], true)}
        </div>
        <div class="l10-feature-side">
          ${featured.slice(1, 4).map(it => renderGalleryCard(it, true)).join('')}
        </div>
      </div>
      <h2 class="section-title">全部作品</h2>
      <div class="gallery-grid">
        ${items.map(it => renderGalleryCard(it, false)).join('')}
      </div>`;
  }

  function renderGalleryCard(it, compact) {
    const img = it.image
      ? `<img src="${escapeHTML(it.image)}" alt="" loading="lazy">`
      : `<div class="placeholder"></div>`;
    const content = (it.content || '').slice(0, compact ? 80 : 200);
    const badge = it.source === 'ai' ? '<span class="badge ai">AI 出品</span>'
                                : '<span class="badge manual">原创</span>';
    return `
      <div class="gallery-card ${compact ? 'compact' : ''}">
        <div class="fx-glare" aria-hidden="true"></div>
        <div class="gallery-thumb">${img}</div>
        <div class="gallery-meta">
          <span class="author">${escapeHTML(it.student_name)}</span>
          ${badge}
        </div>
        <div class="gallery-content">${escapeHTML(content)}</div>
      </div>`;
  }

  function renderL7L8L9() {
    const f = document.getElementById('form-screenshot');
    if (!f) return;
    f.onsubmit = e => {
      e.preventDefault();
      const fd = new FormData(f);
      const content = String(fd.get('content') || '').trim();
      const file = fd.get('image');
      if (!content && !(file && file.size)) {
        showFlash('error', '至少写一句说明或选一张图');
        return;
      }
      const sess = getSession();
      const cls = getCurrentStudentClass();
      const lesson = cls.lessons.find(l => l.level === 'L9') || cls.lessons[cls.lessons.length - 1];
      DB.submissions.push({
        id: uid('sub'), class_id: cls.id, lesson_id: lesson.id,
        student_id: sess.student_id, student_name: sess.display,
        work_type: file && file.size ? 'screenshot' : 'text',
        content: content || '(编程截图作业)',
        image: '', source: 'manual', status: 'pending', comment: '',
        created_at: Date.now()
      });
      saveDB(DB);
      f.reset();
      showFlash('success', '编程作业已提交，等待老师审核');
      const submitBtn = f.querySelector('button[type="submit"]');
      if (submitBtn) {
        const r = submitBtn.getBoundingClientRect();
        FX.submitConfetti(r.left + r.width / 2, r.top + r.height / 2);
      }
    };
  }

  /* ============================================================
   * 10. 教师后台：dashboard / class / submissions
   * ============================================================ */
  function getCurrentTeacherClass() {
    const s = getSession();
    if (!s || s.role !== 'teacher' || !s.class_id) return null;
    return DB.classes.find(c => c.id === s.class_id) || null;
  }

  function renderDashboard() {
    const s = getSession();
    const list = document.getElementById('class-list');
    if (!s || s.role !== 'teacher') { showView('chooser'); return; }

    // 新建班级
    const fC = document.getElementById('form-create-class');
    if (fC) {
      fC.onsubmit = e => {
        e.preventDefault();
        const fd = new FormData(fC);
        const name = String(fd.get('name') || '').trim();
        const semester = String(fd.get('semester') || '').trim() || '未命名学期';
        if (!name) return;
        const code = Math.random().toString(36).slice(2, 8).toUpperCase().replace(/[^A-Z0-9]/g, '0').padEnd(6, '0').slice(0, 6);
        const cls = { id: uid('c'), code, name, semester, created_at: Date.now(), lessons: [], students: [] };
        DB.classes.push(cls);
        saveDB(DB);
        fC.reset();
        showFlash('success', '已创建班级 ' + name + '（码 ' + code + '）');
        renderDashboard();
      };
    }

    if (!DB.classes.length) { list.innerHTML = '<div class="empty">还没有班级，先创建一个吧。</div>'; return; }
    list.innerHTML = `
      <table class="data-table">
        <thead><tr><th>名称</th><th>学期</th><th>班级码</th><th>学生数</th><th>操作</th></tr></thead>
        <tbody>
        ${DB.classes.map(c => `
          <tr>
            <td>${escapeHTML(c.name)}</td>
            <td>${escapeHTML(c.semester)}</td>
            <td><code>${escapeHTML(c.code)}</code></td>
            <td>${c.students.length}</td>
            <td class="actions">
              <button class="btn sm" data-go-class="${c.id}">管理</button>
              <button class="btn sm" data-go-subs="${c.id}">审核作品</button>
              <button class="btn sm" data-go-gallery="${c.id}">展示墙</button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>`;

    list.querySelectorAll('[data-go-class]').forEach(b => b.onclick = () => {
      const s = getSession(); s.class_id = b.dataset.goClass; setSession(s);
      showView('class');
    });
    list.querySelectorAll('[data-go-subs]').forEach(b => b.onclick = () => {
      const s = getSession(); s.class_id = b.dataset.goSubs; setSession(s);
      showView('submissions');
    });
    list.querySelectorAll('[data-go-gallery]').forEach(b => b.onclick = () => {
      const s = getSession(); s.class_id = b.dataset.goGallery; setSession(s);
      showView('gallery');
    });
  }

  function renderClassDetail() {
    const cls = getCurrentTeacherClass();
    if (!cls) { showView('dashboard'); return; }
    document.getElementById('class-title').textContent = cls.name;
    document.getElementById('class-info').innerHTML = `学期：${escapeHTML(cls.semester)} · 班级码：<code>${escapeHTML(cls.code)}</code>`;

    // 添加课次
    const fL = document.getElementById('form-add-lesson');
    if (fL) {
      fL.onsubmit = e => {
        e.preventDefault();
        const fd = new FormData(fL);
        const name = String(fd.get('name') || '').trim();
        const date = String(fd.get('lesson_date') || '').trim();
        const slot = String(fd.get('time_slot') || '').trim();
        if (!name) return;
        // 从 name 里识别 L1..L10，否则给个 Lx 默认
        const m = name.match(/L\s*(\d{1,2})/i);
        const level = m ? ('L' + m[1]) : ('L' + Math.min(10, cls.lessons.length + 1));
        cls.lessons.push({ id: uid('l'), level, name, lesson_date: date, time_slot: slot });
        saveDB(DB);
        fL.reset();
        showFlash('success', '已添加课次 ' + name);
        renderClassDetail();
      };
    }
    // 课次列表
    const ll = document.getElementById('lesson-list');
    if (!cls.lessons.length) { ll.innerHTML = '<div class="empty">还没有课次</div>'; }
    else {
      ll.innerHTML = `
        <table class="data-table">
          <thead><tr><th>课次</th><th>名称</th><th>日期</th><th>时段</th></tr></thead>
          <tbody>${cls.lessons.map(l => `
            <tr>
              <td><code>${escapeHTML(l.level)}</code></td>
              <td>${escapeHTML(l.name)}</td>
              <td>${escapeHTML(l.lesson_date || '—')}</td>
              <td>${escapeHTML(l.time_slot || '—')}</td>
            </tr>`).join('')}
          </tbody>
        </table>`;
    }

    // 批量导入学生
    const fI = document.getElementById('form-import-students');
    if (fI) {
      fI.onsubmit = e => {
        e.preventDefault();
        const fd = new FormData(fI);
        const text = String(fd.get('student_list') || '');
        const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
        let added = 0;
        lines.forEach(line => {
          const parts = line.split(/[,\t]/).map(p => p.trim());
          const name = parts[0];
          if (!name) return;
          const phone = (parts[1] || '').replace(/\D/g, '').slice(-4);
          const display = parts[2] || name;
          cls.students.push({ id: uid('s'), name, phone_tail: phone, display });
          added++;
        });
        saveDB(DB);
        fI.reset();
        showFlash('success', `已导入 ${added} 名学生`);
        renderClassDetail();
      };
    }
    // 学生名册
    const sl = document.getElementById('student-list');
    if (!cls.students.length) { sl.innerHTML = '<div class="empty">还没有学生</div>'; }
    else {
      sl.innerHTML = `
        <table class="data-table">
          <thead><tr><th>姓名</th><th>手机尾号</th><th>显示名</th><th>操作</th></tr></thead>
          <tbody>${cls.students.map(st => `
            <tr>
              <td>${escapeHTML(st.name)}</td>
              <td>${st.phone_tail ? escapeHTML(st.phone_tail) : '—'}</td>
              <td>${escapeHTML(st.display)}</td>
              <td class="actions">
                <button class="btn sm danger" data-del-student="${st.id}">删除</button>
              </td>
            </tr>`).join('')}
          </tbody>
        </table>`;
      sl.querySelectorAll('[data-del-student]').forEach(b => b.onclick = () => {
        if (!confirm('确定删除？')) return;
        cls.students = cls.students.filter(x => x.id !== b.dataset.delStudent);
        saveDB(DB);
        showFlash('info', '已删除');
        renderClassDetail();
      });
    }
  }

  /* ----- 作品审核 ----- */
  let currentSubFilter = 'all';
  let currentSubLesson = 'all';

  function renderSubmissions() {
    const s = getSession();
    if (!s || s.role !== 'teacher') { showView('chooser'); return; }
    const cls = getCurrentTeacherClass();
    if (!cls) { showView('dashboard'); return; }
    document.getElementById('subs-title').textContent = '作品审核 · ' + cls.name;

    // 课次过滤选项
    const sel = document.getElementById('sub-lesson-filter');
    if (sel) {
      sel.innerHTML = '<option value="all">全部课次</option>' +
        cls.lessons.map(l => `<option value="${escapeHTML(l.id)}" ${l.id === currentSubLesson ? 'selected' : ''}>${escapeHTML(l.name)}</option>`).join('');
      sel.onchange = () => { currentSubLesson = sel.value; renderSubmissions(); };
    }

    // 状态过滤按钮
    document.querySelectorAll('[data-sub-filter]').forEach(b => {
      b.classList.toggle('on', b.dataset.subFilter === currentSubFilter);
      b.onclick = e => { e.preventDefault(); currentSubFilter = b.dataset.subFilter; renderSubmissions(); };
    });

    // 数据
    const items = DB.submissions.filter(sub => {
      if (sub.class_id !== cls.id) return false;
      if (currentSubLesson !== 'all' && sub.lesson_id !== currentSubLesson) return false;
      if (currentSubFilter !== 'all' && sub.status !== currentSubFilter) return false;
      return true;
    });

    const host = document.getElementById('subs-list');
    if (!items.length) {
      host.innerHTML = '<div class="empty">没有符合条件的作品。</div>';
      return;
    }
    host.classList.add('fx-stagger');
    host.innerHTML = items.map(renderSubmissionCard).join('');
    host.querySelectorAll('[data-sub-act]').forEach(btn => btn.onclick = () => handleSubAction(btn));
  }

  function renderSubmissionCard(sub) {
    const cls = DB.classes.find(c => c.id === sub.class_id);
    const lesson = cls && cls.lessons.find(l => l.id === sub.lesson_id);
    const lessonLabel = lesson ? lesson.name : sub.lesson_id;
    const statusBadge = `<span class="status-badge status-${escapeHTML(sub.status)}">${
      { pending: '待审核', approved: '已通过', rejected: '已驳回' }[sub.status] || sub.status
    }</span>`;
    const typeLabel = { text: '文字', image: '图片', mixed: '图文', screenshot: '截图' }[sub.work_type] || sub.work_type;
    const sourceLabel = sub.source === 'ai' ? 'AI 生成' : '学生原创';
    return `
      <div class="submission-card" data-sub-id="${escapeHTML(sub.id)}">
        <div class="submission-head">
          <div>
            <span class="student">${escapeHTML(sub.student_name)}</span>
            <span class="lesson">· ${escapeHTML(lessonLabel)}</span>
            <span class="type">· ${typeLabel}</span>
            <span class="source">· ${sourceLabel}</span>
          </div>
          <div>${statusBadge}</div>
        </div>
        <div class="submission-body">
          ${sub.image ? `<img src="${escapeHTML(sub.image)}" alt="" class="submission-image" loading="lazy">` : ''}
          <div class="submission-text">${escapeHTML(sub.content || '(无文字)')}</div>
        </div>
        <div class="submission-foot">
          <textarea class="comment" rows="2" placeholder="给学生的评语（通过 / 驳回时保存）">${escapeHTML(sub.comment || '')}</textarea>
          <div class="submission-actions">
            ${sub.status === 'pending' ? `
              <button class="btn primary sm" data-sub-act="approve">通过</button>
              <button class="btn danger sm" data-sub-act="reject">驳回</button>
            ` : `<span class="muted">已处理</span>`}
          </div>
        </div>
      </div>`;
  }

  function handleSubAction(btn) {
    const card = btn.closest('.submission-card');
    const id = card.dataset.subId;
    const sub = DB.submissions.find(s => s.id === id);
    if (!sub) return;
    const comment = card.querySelector('.comment').value.trim();
    sub.comment = comment;
    // 先禁用本卡操作按钮，防止印章动画期间重复点击
    card.querySelectorAll('[data-sub-act]').forEach(b => { b.disabled = true; });
    if (btn.dataset.subAct === 'approve') {
      sub.status = 'approved';
      // 进入 gallery
      DB.gallery.push({
        id: uid('g'), class_id: sub.class_id, lesson_id: sub.lesson_id,
        student_id: sub.student_id, student_name: sub.student_name,
        work_type: sub.work_type, image: sub.image, source: sub.source,
        content: sub.content, created_at: Date.now()
      });
      showFlash('success', '已通过，作品进入展示墙');
      FX.dropStamp(card, 'approve');
    } else if (btn.dataset.subAct === 'reject') {
      sub.status = 'rejected';
      showFlash('info', '已驳回');
      FX.dropStamp(card, 'reject');
    }
    saveDB(DB);
    // 延迟重渲染：同步 innerHTML 重绘会把刚砸下的印章在同一帧抹掉，
    // 等印章下落动画（0.55s）播完并稍作停留后再刷新列表。
    setTimeout(() => renderSubmissions(), 1500);
  }

  /* ============================================================
   * 12. 交互特效（基于奶油乐园设计语言的 8 处动效）
   *   - FX.clickBurst：主按钮点击时从指针位置喷出星星
   *   - FX.submitConfetti：作品提交成功时彩屑
   *   - FX.magnetic：主按钮磁吸
   *   - FX.tilt：选择卡 / 作品卡 3D 倾斜 + glare
   *   - FX.progressMascot：AI 进度条骑乘 emoji
   *   - FX.quotaShake：额度用尽抖动
   *   - FX.stamp：审核通过 / 驳回印章
   *   - FX.bindOnViewEnter：每次 view 切换时重新绑定磁吸 / 倾斜
   * 全部在 prefers-reduced-motion 时降级为 noop。
   * ============================================================ */
  const FX = (() => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    let burstHost = null;

    function ensureBurstHost() {
      if (burstHost) return burstHost;
      burstHost = document.createElement('div');
      burstHost.className = 'fx-burst-host';
      document.body.appendChild(burstHost);
      return burstHost;
    }

    function clickBurst(x, y, kind) {
      if (reduced) return;
      const host = ensureBurstHost();
      const N = 10;
      const glyphs = kind === 'image' ? ['🎨','✦','✿','★'] : ['✦','★','✿','✧','❀'];
      for (let i = 0; i < N; i++) {
        const s = document.createElement('span');
        const angle = (Math.PI * 2 * i) / N + (Math.random() - 0.5) * 0.4;
        const dist = 60 + Math.random() * 50;
        const bx = Math.cos(angle) * dist;
        const by = Math.sin(angle) * dist - 30; // 偏上
        const br = (Math.random() * 360) | 0;
        const cls = ['', 'alt', 'alt2'][i % 3];
        s.className = 'fx-burst-star' + (cls ? ' ' + cls : '');
        s.textContent = glyphs[i % glyphs.length];
        s.style.left = x + 'px';
        s.style.top = y + 'px';
        s.style.setProperty('--bx', bx.toFixed(0) + 'px');
        s.style.setProperty('--by', by.toFixed(0) + 'px');
        s.style.setProperty('--br', br + 'deg');
        host.appendChild(s);
        setTimeout(() => s.remove(), 1100);
      }
    }

    function submitConfetti(x, y) {
      if (reduced) return;
      const host = ensureBurstHost();
      const colors = ['#ff6b6b', '#4ecdc4', '#ffd166', '#ff8a65', '#b388ff', '#7cb342'];
      const N = 36;
      for (let i = 0; i < N; i++) {
        const c = document.createElement('div');
        c.className = 'fx-confetti';
        const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 0.9;
        const dist = 140 + Math.random() * 180;
        const cx = Math.cos(angle) * dist;
        const cy = Math.sin(angle) * dist + 220; // 落下
        const cz = (Math.random() * 720 - 360) | 0;
        const cxr = (Math.random() * 540) | 0;
        c.style.left = x + 'px';
        c.style.top = y + 'px';
        c.style.background = colors[i % colors.length];
        c.style.setProperty('--cx', cx.toFixed(0) + 'px');
        c.style.setProperty('--cy', cy.toFixed(0) + 'px');
        c.style.setProperty('--cz', cz + 'deg');
        c.style.setProperty('--cxr', cxr + 'deg');
        host.appendChild(c);
        setTimeout(() => c.remove(), 1500);
      }
    }

    function bindMagnetic(root) {
      if (reduced) return;
      const btns = (root || document).querySelectorAll('.btn.primary');
      btns.forEach(btn => {
        if (btn.__fx_mag) return;
        btn.__fx_mag = true;
        let raf = 0;
        btn.addEventListener('mousemove', e => {
          const r = btn.getBoundingClientRect();
          const cx = r.left + r.width / 2;
          const cy = r.top + r.height / 2;
          // 限幅 4px
          const dx = Math.max(-4, Math.min(4, (e.clientX - cx) * 0.18));
          const dy = Math.max(-4, Math.min(4, (e.clientY - cy) * 0.18));
          cancelAnimationFrame(raf);
          raf = requestAnimationFrame(() => {
            btn.style.setProperty('--mx', dx.toFixed(1) + 'px');
            btn.style.setProperty('--my', dy.toFixed(1) + 'px');
            btn.classList.add('fx-magnet');
          });
        });
        btn.addEventListener('mouseleave', () => {
          cancelAnimationFrame(raf);
          btn.style.setProperty('--mx', '0px');
          btn.style.setProperty('--my', '0px');
          // 不移除 fx-magnet class，让 CSS 用 transition 平滑回到 0
        });
      });
    }

    function bindTilt(root) {
      if (reduced) return;
      const cards = (root || document).querySelectorAll('.choice-card, .gallery-card');
      cards.forEach(card => {
        if (card.__fx_tilt) return;
        // 确保有 glare 子元素
        if (!card.querySelector(':scope > .fx-glare')) {
          const g = document.createElement('div');
          g.className = 'fx-glare';
          g.setAttribute('aria-hidden', 'true');
          card.insertBefore(g, card.firstChild);
        }
        card.__fx_tilt = true;
        let raf = 0;
        card.addEventListener('mousemove', e => {
          const r = card.getBoundingClientRect();
          const px = (e.clientX - r.left) / r.width;
          const py = (e.clientY - r.top) / r.height;
          const rx = (0.5 - py) * 8;   // rotateX ±4deg
          const ry = (px - 0.5) * 10;  // rotateY ±5deg
          cancelAnimationFrame(raf);
          raf = requestAnimationFrame(() => {
            card.style.transform = `perspective(900px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) translateY(-3px)`;
            const glare = card.querySelector(':scope > .fx-glare');
            if (glare) {
              glare.style.setProperty('--gx', (px * 100).toFixed(1) + '%');
              glare.style.setProperty('--gy', (py * 100).toFixed(1) + '%');
            }
          });
        });
        card.addEventListener('mouseleave', () => {
          cancelAnimationFrame(raf);
          // 平滑回到原状——注意：choice-card 默认有 rotate(-1.5deg/1.5deg)，gallery-card 无
          const isChoice = card.classList.contains('choice-card');
          const idx = Array.from(card.parentNode.children).indexOf(card);
          const restRot = isChoice ? (idx === 0 ? '-1.5deg' : '1.5deg') : '0deg';
          card.style.transform = `perspective(900px) rotateX(0) rotateY(0) translateZ(0) rotate(${restRot})`;
        });
      });
    }

    function updateProgressMascot(progressEl) {
      const fill = progressEl.querySelector('.ai-progress-fill');
      const mascot = progressEl.querySelector('[data-mascot]');
      if (!fill || !mascot) return;
      const w = fill.getBoundingClientRect().width;
      const pw = progressEl.getBoundingClientRect().width;
      if (!pw) return;
      const pct = Math.max(2, Math.min(98, (w / pw) * 100));
      mascot.style.left = pct + '%';
      // 到顶或到底时给个 bump
      const isEnd = pct >= 96;
      const isStart = pct <= 4;
      if (isEnd || isStart) {
        mascot.classList.remove('bump');
        // force reflow
        void mascot.offsetWidth;
        mascot.classList.add('bump');
      }
    }

    function startProgressMascot(progressEl) {
      if (reduced) return;
      const fill = progressEl.querySelector('.ai-progress-fill');
      if (!fill) return;
      // 用 ResizeObserver 监听 fill 宽度变化
      if (progressEl.__fx_mascot_ro) progressEl.__fx_mascot_ro.disconnect();
      const ro = new ResizeObserver(() => updateProgressMascot(progressEl));
      ro.observe(fill);
      progressEl.__fx_mascot_ro = ro;
      updateProgressMascot(progressEl);
    }

    function shakeCard(card) {
      if (reduced) return;
      card.classList.remove('fx-shake');
      void card.offsetWidth;
      card.classList.add('fx-shake');
      setTimeout(() => card.classList.remove('fx-shake'), 500);
    }

    function dropStamp(card, kind) {
      if (reduced) return;
      const old = card.querySelector('.fx-stamp');
      if (old) old.remove();
      const s = document.createElement('div');
      s.className = 'fx-stamp' + (kind === 'reject' ? ' reject' : '');
      s.textContent = kind === 'reject' ? '已驳回' : '已通过';
      card.appendChild(s);
      // 状态徽章弹入
      const badge = card.querySelector('.status-badge');
      if (badge) {
        badge.classList.remove('just-in');
        void badge.offsetWidth;
        badge.classList.add('just-in');
      }
      // 印章 4s 后淡出（避免挡住内容）
      setTimeout(() => { if (s.parentNode) s.remove(); }, 4000);
    }

    return {
      clickBurst, submitConfetti, bindMagnetic, bindTilt,
      startProgressMascot, shakeCard, dropStamp,
      reduced
    };
  })();

  /* ============================================================
   * 13. 启动
   * ============================================================ */
  function boot() {
    bindAuthForms();
    renderNav();
    // 启动时按 hash 决定初始视图
    const hash = (location.hash || '').replace('#', '');
    const startView = VIEWS.includes(hash) ? hash : 'chooser';
    showView(startView, { skipHistory: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
