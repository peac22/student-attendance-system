import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
from datetime import datetime

DB_PATH = "src/attendance.db"
current_user = None  # dict {id, username, role}

# -------------------------
# DB helper
# -------------------------
def db_query(query, params=(), fetch=True):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return rows

if not os.path.exists(DB_PATH):
    messagebox.showerror("Ошибка", f"База данных не найдена!\nОжидается файл:\n{DB_PATH}")
    raise SystemExit(1)

# -------------------------
# Login window
# -------------------------
def login_window(parent, role):
    win = tk.Toplevel(parent)
    win.title(f"Вход ({role})")
    win.geometry("360x260")
    win.grab_set()

    tk.Label(win, text=f"Вход — {role}", font=("Segoe UI", 14, "bold")).pack(pady=16)
    tk.Label(win, text="Username:").pack(anchor="w", padx=40)
    e_user = tk.Entry(win, width=30); e_user.pack(pady=6)
    tk.Label(win, text="Пароль:").pack(anchor="w", padx=40)
    e_pass = tk.Entry(win, width=30, show="*"); e_pass.pack(pady=6)

    def confirm():
        username = e_user.get().strip()
        password = e_pass.get().strip()
        row = db_query("SELECT user_id, username, role FROM USERS WHERE username=? AND password=? AND role=?",
                       (username, password, role))
        if not row:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
            return
        user_id, uname, urole = row[0]
        global current_user
        current_user = {"id": user_id, "username": uname, "role": urole}
        win.destroy()
        if urole == "admin":
            open_admin_panel(parent)
        elif urole == "teacher":
            open_teacher_panel(parent)
        elif urole == "student":
            open_student_panel(parent)
    tk.Button(win, text="Войти", width=18, command=confirm).pack(pady=14)

# -------------------------
# Admin UI
# -------------------------
def open_admin_panel(root):
    win = tk.Toplevel(root)
    win.title("Админ-панель")
    win.geometry("900x600")

    tk.Label(win, text=f"Администратор: {current_user['username']}", font=("Segoe UI", 16, "bold")).pack(pady=10)

    frame = tk.Frame(win); frame.pack(fill="x", padx=12, pady=6)
    tk.Button(frame, text="Пользователи", width=18, command=lambda: admin_manage_users(win)).pack(side="left", padx=6)
    tk.Button(frame, text="Группы", width=18, command=lambda: admin_manage_groups(win)).pack(side="left", padx=6)
    tk.Button(frame, text="Студенты в группах", width=18, command=lambda: admin_manage_group_students(win)).pack(side="left", padx=6)
    tk.Button(frame, text="Предметы", width=18, command=lambda: admin_manage_subjects(win)).pack(side="left", padx=6)
    tk.Button(frame, text="Расписание", width=18, command=lambda: admin_manage_schedule(win)).pack(side="left", padx=6)
    tk.Button(frame, text="Отчёт — все посещения", width=18, command=lambda: teacher_all_attendance(win)).pack(side="left", padx=6)

# -- Users management
def admin_manage_users(parent):
    win = tk.Toplevel(parent)
    win.title("Управление пользователями")
    win.geometry("900x500")

    cols = ("id","username","role","email")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for c,h,w in zip(cols, ["ID","Username","Role","Email"], [60,220,120,300]):
        tree.heading(c, text=h); tree.column(c, width=w)
    tree.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh():
        for i in tree.get_children(): tree.delete(i)
        rows = db_query("SELECT user_id, username, role, COALESCE(email,'') FROM USERS ORDER BY user_id")
        for r in rows: tree.insert("", "end", values=r)
    refresh()

    def create_user():
        dlg = tk.Toplevel(win); dlg.title("Создать пользователя"); dlg.geometry("360x300")
        tk.Label(dlg, text="Username:").pack(anchor="w", padx=12, pady=6)
        e_user = tk.Entry(dlg, width=30); e_user.pack(padx=12)
        tk.Label(dlg, text="Password:").pack(anchor="w", padx=12, pady=6)
        e_pass = tk.Entry(dlg, width=30); e_pass.pack(padx=12)
        tk.Label(dlg, text="Role (admin/teacher/student):").pack(anchor="w", padx=12, pady=6)
        e_role = tk.Entry(dlg, width=30); e_role.pack(padx=12)
        tk.Label(dlg, text="Email (optional):").pack(anchor="w", padx=12, pady=6)
        e_email = tk.Entry(dlg, width=30); e_email.pack(padx=12)

        def save():
            u = e_user.get().strip(); p = e_pass.get().strip(); r = e_role.get().strip(); em = e_email.get().strip()
            if not (u and p and r): messagebox.showerror("Ошибка","Заполните поля"); return
            if r not in ("admin","teacher","student"): messagebox.showerror("Ошибка","Роль должна быть admin/teacher/student"); return
            try:
                db_query("INSERT INTO USERS (username,password,role,email) VALUES (?,?,?,?)",(u,p,r,em), fetch=False)
                messagebox.showinfo("OK","Пользователь создан")
                dlg.destroy(); refresh()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка","Пользователь с таким именем уже существует")
        tk.Button(dlg, text="Создать", command=save).pack(pady=12)

    def edit_user():
        sel = tree.focus()
        if not sel: messagebox.showerror("Ошибка","Выберите пользователя"); return
        uid, uname, role, email = tree.item(sel, "values")
        dlg = tk.Toplevel(win); dlg.title("Редактировать пользователя"); dlg.geometry("360x320")
        tk.Label(dlg, text="Username:").pack(anchor="w", padx=12); e_user = tk.Entry(dlg, width=30); e_user.insert(0,uname); e_user.pack(padx=12)
        tk.Label(dlg, text="Password (оставить пустым чтобы не менять):").pack(anchor="w", padx=12)
        e_pass = tk.Entry(dlg, width=30); e_pass.pack(padx=12)
        tk.Label(dlg, text="Role:").pack(anchor="w", padx=12); e_role = tk.Entry(dlg, width=30); e_role.insert(0,role); e_role.pack(padx=12)
        tk.Label(dlg, text="Email:").pack(anchor="w", padx=12); e_email = tk.Entry(dlg, width=30); e_email.insert(0,email); e_email.pack(padx=12)
        def save():
            new_u = e_user.get().strip(); new_p = e_pass.get().strip(); new_r = e_role.get().strip(); new_em = e_email.get().strip()
            if new_r not in ("admin","teacher","student"): messagebox.showerror("Ошибка","Роль должна быть admin/teacher/student"); return
            try:
                if new_p:
                    db_query("UPDATE USERS SET username=?, password=?, role=?, email=? WHERE user_id=?", (new_u,new_p,new_r,new_em, uid), fetch=False)
                else:
                    db_query("UPDATE USERS SET username=?, role=?, email=? WHERE user_id=?", (new_u,new_r,new_em, uid), fetch=False)
                messagebox.showinfo("OK","Изменено"); dlg.destroy(); refresh()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка","Имя уже занято")
        tk.Button(dlg, text="Сохранить", command=save).pack(pady=10)

    def delete_user():
        sel = tree.focus()
        if not sel: messagebox.showerror("Ошибка","Выберите пользователя"); return
        uid = tree.item(sel,"values")[0]
        if messagebox.askyesno("Подтвердить","Удалить пользователя?"):
            db_query("DELETE FROM USERS WHERE user_id=?", (uid,), fetch=False)
            refresh()

    btns = tk.Frame(win); btns.pack(pady=6)
    tk.Button(btns, text="Создать", command=create_user).pack(side="left", padx=6)
    tk.Button(btns, text="Редактировать", command=edit_user).pack(side="left", padx=6)
    tk.Button(btns, text="Удалить", command=delete_user).pack(side="left", padx=6)

# -- Groups management
def admin_manage_groups(parent):
    win = tk.Toplevel(parent); win.title("Группы"); win.geometry("500x400")
    tree = ttk.Treeview(win, columns=("id","name"), show="headings")
    tree.heading("id", text="ID"); tree.heading("name", text="Название"); tree.column("name", width=320)
    tree.pack(fill="both", expand=True, padx=8, pady=8)
    def refresh():
        for i in tree.get_children(): tree.delete(i)
        for r in db_query('SELECT group_id, group_name FROM "GROUP" ORDER BY group_id'):
            tree.insert("", "end", values=r)
    refresh()
    def create():
        name = simpledialog.askstring("Новая группа","Название группы:", parent=win)
        if not name: return
        db_query('INSERT INTO "GROUP" (group_name) VALUES (?)', (name,), fetch=False); refresh()
    def delete():
        sel = tree.focus()
        if not sel: messagebox.showerror("Ошибка","Выберите группу"); return
        gid = tree.item(sel,"values")[0]
        if messagebox.askyesno("Подтвердить","Удалить группу? (все привязки студентов будут удалены)"):
            db_query('DELETE FROM GROUP_STUDENTS WHERE group_id=?', (gid,), fetch=False)
            db_query('DELETE FROM "GROUP" WHERE group_id=?', (gid,), fetch=False)
            refresh()
    frame = tk.Frame(win); frame.pack(pady=6)
    tk.Button(frame, text="Создать", command=create).pack(side="left", padx=6)
    tk.Button(frame, text="Удалить", command=delete).pack(side="left", padx=6)

# -- Group students management
def admin_manage_group_students(parent):
    win = tk.Toplevel(parent); win.title("Студенты в группах"); win.geometry("800x500")
    cols = ("group_id","group_name","student_id","student_name")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for c,h,w in zip(cols, ["Group ID","Группа","Student ID","Студент"], [80,250,80,250]):
        tree.heading(c, text=h); tree.column(c, width=w)
    tree.pack(fill="both", expand=True, padx=8, pady=8)
    def refresh():
        for i in tree.get_children(): tree.delete(i)
        rows = db_query("""
            SELECT g.group_id, g.group_name, u.user_id, u.username
            FROM GROUP_STUDENTS gs
            JOIN "GROUP" g ON gs.group_id = g.group_id
            JOIN USERS u ON gs.user_id = u.user_id
            ORDER BY g.group_name, u.username
        """)
        for r in rows: tree.insert("", "end", values=r)
    refresh()
    def add():
        dlg = tk.Toplevel(win); dlg.title("Добавить студента в группу"); dlg.geometry("400x200")
        tk.Label(dlg, text="Группа:").pack(anchor="w", padx=12)
        groups = [row[1] for row in db_query('SELECT group_id, group_name FROM "GROUP"')]
        cb_group = ttk.Combobox(dlg, values=groups, width=35); cb_group.pack(padx=12, pady=6)
        tk.Label(dlg, text="Студент:").pack(anchor="w", padx=12)
        students = [row[1] for row in db_query("SELECT user_id, username FROM USERS WHERE role='student'")]
        cb_student = ttk.Combobox(dlg, values=students, width=35); cb_student.pack(padx=12, pady=6)
        def save():
            try:
                gid = db_query('SELECT group_id FROM "GROUP" WHERE group_name=?', (cb_group.get(),))[0][0]
                sid = db_query('SELECT user_id FROM USERS WHERE username=?', (cb_student.get(),))[0][0]
                db_query("INSERT INTO GROUP_STUDENTS (user_id, group_id) VALUES (?, ?)", (sid, gid), fetch=False)
                messagebox.showinfo("OK","Студент добавлен в группу"); dlg.destroy(); refresh()
            except IndexError:
                messagebox.showerror("Ошибка","Выберите группу и студента")
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка","Студент уже в группе")
        tk.Button(dlg, text="Добавить", command=save).pack(pady=12)
    def delete():
        sel = tree.focus()
        if not sel: messagebox.showerror("Ошибка","Выберите запись"); return
        gid, _, sid, _ = tree.item(sel, "values")
        if messagebox.askyesno("Подтвердить","Удалить студента из группы?"):
            db_query("DELETE FROM GROUP_STUDENTS WHERE user_id=? AND group_id=?", (sid, gid), fetch=False)
            refresh()
    frame = tk.Frame(win); frame.pack(pady=6)
    tk.Button(frame, text="Добавить", command=add).pack(side="left", padx=6)
    tk.Button(frame, text="Удалить", command=delete).pack(side="left", padx=6)

# -- Subjects management
def admin_manage_subjects(parent):
    win = tk.Toplevel(parent); win.title("Предметы"); win.geometry("500x400")
    tree = ttk.Treeview(win, columns=("id","name"), show="headings")
    tree.heading("id", text="ID"); tree.heading("name", text="Название"); tree.column("name", width=320)
    tree.pack(fill="both", expand=True, padx=8, pady=8)
    def refresh():
        for i in tree.get_children(): tree.delete(i)
        for r in db_query('SELECT subject_id, subject_name FROM SUBJECT ORDER BY subject_id'):
            tree.insert("", "end", values=r)
    refresh()
    def create():
        name = simpledialog.askstring("Новый предмет","Название предмета:", parent=win)
        if not name: return
        db_query('INSERT INTO SUBJECT (subject_name) VALUES (?)', (name,), fetch=False); refresh()
    def delete():
        sel = tree.focus()
        if not sel: messagebox.showerror("Ошибка","Выберите предмет"); return
        sid = tree.item(sel,"values")[0]
        if messagebox.askyesno("Подтвердить","Удалить предмет?"):
            db_query('DELETE FROM SUBJECT WHERE subject_id=?', (sid,), fetch=False)
            refresh()
    frame = tk.Frame(win); frame.pack(pady=6)
    tk.Button(frame, text="Создать", command=create).pack(side="left", padx=6)
    tk.Button(frame, text="Удалить", command=delete).pack(side="left", padx=6)

# -- Schedule management
def admin_manage_schedule(parent):
    win = tk.Toplevel(parent); win.title("Расписание"); win.geometry("1000x600")

    cols = ("id","date","time","subject","teacher","group","room")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    headers = ["ID","Дата","Время","Предмет","Преподаватель","Группа","Аудитория"]
    widths = [60,110,110,220,180,140,120]
    for c,h,w in zip(cols, headers, widths):
        tree.heading(c, text=h); tree.column(c, width=w)
    tree.pack(fill="both", expand=True, padx=8, pady=8)

    def refresh():
        for i in tree.get_children(): tree.delete(i)
        rows = db_query("""
            SELECT s.schedule_id, s.date, s.time, sub.subject_name, u.username, g.group_name, s.room
            FROM SCHEDULE s
            JOIN SUBJECT sub ON s.subject_id = sub.subject_id
            JOIN USERS u ON s.teacher_id = u.user_id
            JOIN "GROUP" g ON s.group_id = g.group_id
            ORDER BY s.date, s.time
        """)
        for r in rows: tree.insert("", "end", values=r)
    refresh()

    def create():
        dlg = tk.Toplevel(win); dlg.title("Добавить занятие"); dlg.geometry("420x420")
        tk.Label(dlg, text="Группа:").pack(anchor="w", padx=12)
        groups = [row[1] for row in db_query('SELECT group_id, group_name FROM "GROUP"')]
        cb_group = ttk.Combobox(dlg, values=groups, width=35); cb_group.pack(padx=12, pady=6)
        tk.Label(dlg, text="Преподаватель:").pack(anchor="w", padx=12)
        teachers = [row[1] for row in db_query("SELECT user_id, username FROM USERS WHERE role='teacher'")]
        cb_teacher = ttk.Combobox(dlg, values=teachers, width=35); cb_teacher.pack(padx=12, pady=6)
        tk.Label(dlg, text="Предмет:").pack(anchor="w", padx=12)
        subjects = [row[1] for row in db_query("SELECT subject_id, subject_name FROM SUBJECT")]
        cb_subject = ttk.Combobox(dlg, values=subjects, width=35); cb_subject.pack(padx=12, pady=6)
        tk.Label(dlg, text="Дата (YYYY-MM-DD):").pack(anchor="w", padx=12); e_date = tk.Entry(dlg, width=36); e_date.pack(padx=12, pady=6)
        tk.Label(dlg, text="Время (HH:MM):").pack(anchor="w", padx=12); e_time = tk.Entry(dlg, width=36); e_time.pack(padx=12, pady=6)
        tk.Label(dlg, text="Аудитория:").pack(anchor="w", padx=12); e_room = tk.Entry(dlg, width=36); e_room.pack(padx=12, pady=6)
        def save():
            try:
                gid = db_query('SELECT group_id FROM "GROUP" WHERE group_name=?', (cb_group.get(),))[0][0]
                tid = db_query('SELECT user_id FROM USERS WHERE username=?', (cb_teacher.get(),))[0][0]
                sid = db_query('SELECT subject_id FROM SUBJECT WHERE subject_name=?', (cb_subject.get(),))[0][0]
            except Exception:
                messagebox.showerror("Ошибка","Выберите корректные группу/преподавателя/предмет"); return
            db_query("""INSERT INTO SCHEDULE (subject_id, teacher_id, group_id, date, time, room)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (sid, tid, gid, e_date.get().strip(), e_time.get().strip(), e_room.get().strip()), fetch=False)
            messagebox.showinfo("ОК","Занятие добавлено"); dlg.destroy(); refresh()
        tk.Button(dlg, text="Сохранить", command=save).pack(pady=12)
    def delete():
        sel = tree.focus()
        if not sel: messagebox.showerror("Ошибка","Выберите занятие"); return
        sid = tree.item(sel,"values")[0]
        if messagebox.askyesno("Подтвердить","Удалить занятие?"):
            db_query("DELETE FROM SCHEDULE WHERE schedule_id=?", (sid,), fetch=False); refresh()
    def on_double(e):
        sel = tree.focus()
        if not sel: return
        schedule_id = tree.item(sel, "values")[0]
        open_attendance_mark_window(win, schedule_id)
    tree.bind("<Double-1>", on_double)
    frame = tk.Frame(win); frame.pack(pady=6)
    tk.Button(frame, text="Создать", command=create).pack(side="left", padx=6)
    tk.Button(frame, text="Удалить", command=delete).pack(side="left", padx=6)

# -------------------------
# Teacher UI
# -------------------------
def open_teacher_panel(root):
    win = tk.Toplevel(root)
    win.title("Преподаватель")
    win.geometry("900x600")
    tk.Label(win, text=f"Преподаватель: {current_user['username']}", font=("Segoe UI", 16, "bold")).pack(pady=10)
    frame = tk.Frame(win); frame.pack(pady=6)
    tk.Button(frame, text="Моё расписание", width=20, command=lambda: teacher_schedule(win)).pack(side="left", padx=8)
    tk.Button(frame, text="Отчёт — все посещения", width=20, command=lambda: teacher_all_attendance(win)).pack(side="left", padx=8)

def teacher_schedule(parent):
    win = tk.Toplevel(parent); win.title("Моё расписание"); win.geometry("1000x600")
    cols = ("id","date","time","subject","group","room")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for c,h,w in zip(cols, ["ID","Дата","Время","Предмет","Группа","Аудитория"], [60,120,120,300,180,120]):
        tree.heading(c, text=h); tree.column(c, width=w)
    tree.pack(fill="both", expand=True, padx=8, pady=8)
    rows = db_query("""
        SELECT s.schedule_id, s.date, s.time, sub.subject_name, g.group_name, s.room
        FROM SCHEDULE s
        JOIN SUBJECT sub ON s.subject_id = sub.subject_id
        JOIN "GROUP" g ON s.group_id = g.group_id
        WHERE s.teacher_id = ?
        ORDER BY s.date, s.time
    """, (current_user["id"],))
    for r in rows: tree.insert("", "end", values=r)
    def on_double(e):
        sel = tree.focus()
        if not sel: return
        schedule_id = tree.item(sel, "values")[0]
        open_attendance_mark_window(parent, schedule_id)
    tree.bind("<Double-1>", on_double)

def teacher_all_attendance(parent):
    win = tk.Toplevel(parent); win.title("Все посещения"); win.geometry("1000x600")
    cols = ("id","student","group","date","time","subject","status")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    headers = ["ID","Студент","Группа","Дата","Время","Предмет","Статус"]
    widths = [60,220,160,110,90,220,100]
    for c,h,w in zip(cols, headers, widths):
        tree.heading(c, text=h); tree.column(c, width=w)
    tree.pack(fill="both", expand=True, padx=8, pady=8)
    rows = db_query("""
        SELECT a.attendance_id, u.username, g.group_name, s.date, s.time, sub.subject_name, a.status
        FROM ATTENDANCE a
        JOIN USERS u ON a.user_id = u.user_id
        JOIN SCHEDULE s ON a.schedule_id = s.schedule_id
        JOIN SUBJECT sub ON s.subject_id = sub.subject_id
        JOIN "GROUP" g ON s.group_id = g.group_id
        ORDER BY s.date DESC
    """)
    for r in rows: tree.insert("", "end", values=r)

# -------------------------
# Attendance marking (teacher/admin)
# -------------------------
def open_attendance_mark_window(parent, schedule_id):
    win = tk.Toplevel(parent); win.title(f"Отметка посещаемости — занятие #{schedule_id}"); win.geometry("700x520")
    tk.Label(win, text=f"Занятие #{schedule_id}", font=("Segoe UI", 14, "bold")).pack(pady=10)
    cols = ("student","status")
    tree = ttk.Treeview(win, columns=cols, show="headings"); tree.heading("student", text="Студент"); tree.heading("status", text="Статус")
    tree.pack(fill="both", expand=True, padx=10, pady=10)
    rows = db_query("""
        SELECT u.user_id, u.username
        FROM GROUP_STUDENTS gs
        JOIN USERS u ON gs.user_id = u.user_id
        JOIN SCHEDULE s ON s.group_id = gs.group_id
        WHERE s.schedule_id = ?
    """, (schedule_id,))
    for student_id, username in rows:
        existing = db_query("SELECT status FROM ATTENDANCE WHERE schedule_id=? AND user_id=?", (schedule_id, student_id))
        status = existing[0][0] if existing else "—"
        tree.insert("", "end", values=(username, status), tags=(student_id,))
    def mark_present():
        sel = tree.focus()
        if not sel: return
        sid = tree.item(sel, "tags")[0]
        upsert_attendance(schedule_id, sid, "present")
        tree.set(sel, "status", "present")
    def mark_absent():
        sel = tree.focus()
        if not sel: return
        sid = tree.item(sel, "tags")[0]
        upsert_attendance(schedule_id, sid, "absent")
        tree.set(sel, "status", "absent")
    def mark_late():
        sel = tree.focus()
        if not sel: return
        sid = tree.item(sel, "tags")[0]
        upsert_attendance(schedule_id, sid, "late")
        tree.set(sel, "status", "late")
    frm = tk.Frame(win); frm.pack(pady=8)
    tk.Button(frm, text="Присутствует", width=14, command=mark_present).grid(row=0,column=0,padx=6)
    tk.Button(frm, text="Отсутствует", width=14, command=mark_absent).grid(row=0,column=1,padx=6)
    tk.Button(frm, text="Опоздал", width=14, command=mark_late).grid(row=0,column=2,padx=6)

def upsert_attendance(schedule_id, user_id, status):
    exists = db_query("SELECT 1 FROM ATTENDANCE WHERE schedule_id=? AND user_id=?", (schedule_id, user_id))
    if exists:
        db_query("UPDATE ATTENDANCE SET status=? WHERE schedule_id=? AND user_id=?", (status, schedule_id, user_id), fetch=False)
    else:
        db_query("INSERT INTO ATTENDANCE (schedule_id, user_id, status) VALUES (?, ?, ?)", (schedule_id, user_id, status), fetch=False)

# -------------------------
# Student UI
# -------------------------
def open_student_panel(root):
    win = tk.Toplevel(root)
    win.title("Студент")
    win.geometry("900x600")
    tk.Label(win, text=f"Студент: {current_user['username']}", font=("Segoe UI", 16, "bold")).pack(pady=8)
    frame = tk.Frame(win); frame.pack(pady=6)
    tk.Button(frame, text="Моё расписание", width=18, command=lambda: student_schedule(win)).pack(side="left", padx=6)
    tk.Button(frame, text="Моя посещаемость", width=18, command=lambda: student_attendance(win)).pack(side="left", padx=6)

def student_schedule(parent):
    # find group
    row = db_query("""
        SELECT g.group_id, g.group_name
        FROM GROUP_STUDENTS gs
        JOIN "GROUP" g ON gs.group_id=g.group_id
        WHERE gs.user_id=?
    """, (current_user["id"],))
    if not row:
        messagebox.showerror("Ошибка","Вы не прикреплены к группе")
        return
    gid, gname = row[0]
    win = tk.Toplevel(parent); win.title("Моё расписание"); win.geometry("900x500")
    tk.Label(win, text=f"Группа: {gname}", font=("Segoe UI", 14, "bold")).pack(pady=6)
    cols = ("date","time","subject","teacher","room")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for c,h,w in zip(cols, ["Дата","Время","Предмет","Преподаватель","Аудитория"], [130,110,260,220,120]):
        tree.heading(c, text=h); tree.column(c, width=w)
    tree.pack(fill="both", expand=True, padx=8, pady=8)
    rows = db_query("""
        SELECT s.date, s.time, sub.subject_name, u.username, s.room
        FROM SCHEDULE s
        JOIN SUBJECT sub ON s.subject_id=sub.subject_id
        JOIN USERS u ON s.teacher_id=u.user_id
        WHERE s.group_id=?
        ORDER BY s.date, s.time
    """, (gid,))
    for r in rows: tree.insert("", "end", values=r)

def student_attendance(parent):
    win = tk.Toplevel(parent); win.title("Моя посещаемость"); win.geometry("900x500")
    cols = ("date","time","subject","status")
    tree = ttk.Treeview(win, columns=cols, show="headings")
    for c,h,w in zip(cols, ["Дата","Время","Предмет","Статус"], [150,110,380,120]):
        tree.heading(c, text=h); tree.column(c, width=w)
    tree.pack(fill="both", expand=True, padx=8, pady=8)
    rows = db_query("""
        SELECT s.date, s.time, sub.subject_name, a.status
        FROM ATTENDANCE a
        JOIN SCHEDULE s ON a.schedule_id=s.schedule_id
        JOIN SUBJECT sub ON s.subject_id=sub.subject_id
        WHERE a.user_id=?
        ORDER BY s.date
    """, (current_user["id"],))
    for r in rows: tree.insert("", "end", values=r)

# -------------------------
# Main window
# -------------------------
def main_window():
    root = tk.Tk()
    root.title("Система учёта посещаемости")
    root.geometry("520x420")
    tk.Label(root, text="СИСТЕМА УЧЁТА ПОСЕЩАЕМОСТИ", font=("Segoe UI", 18, "bold")).pack(pady=24)
    tk.Button(root, text="СТУДЕНТ", width=30, height=2, command=lambda: login_window(root,"student")).pack(pady=8)
    tk.Button(root, text="ПРЕПОДАВАТЕЛЬ", width=30, height=2, command=lambda: login_window(root,"teacher")).pack(pady=8)
    tk.Button(root, text="АДМИНИСТРАТОР", width=30, height=2, command=lambda: login_window(root,"admin")).pack(pady=8)
    root.mainloop()

if __name__ == "__main__":
    main_window()