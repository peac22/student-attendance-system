import os
import sqlite3
import json
import csv
import yaml
import xml.etree.ElementTree as ET
from datetime import datetime

def main():
    os.makedirs("src", exist_ok=True)
    os.makedirs("out", exist_ok=True)

    DB_PATH = "src/attendance.db"

    if os.path.exists(DB_PATH):
        print("База уже существует, пропуск инициализации.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ============================
    # СОЗДАНИЕ ТАБЛИЦ
    # ============================
    cursor.executescript("""
    DROP TABLE IF EXISTS ATTENDANCE;
    DROP TABLE IF EXISTS SCHEDULE;
    DROP TABLE IF EXISTS GROUP_STUDENTS;
    DROP TABLE IF EXISTS SUBJECT;
    DROP TABLE IF EXISTS "GROUP";
    DROP TABLE IF EXISTS USERS;

    CREATE TABLE USERS (
        user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT NOT NULL UNIQUE,
        password    TEXT NOT NULL,
        role        TEXT CHECK(role IN ('admin', 'teacher', 'student')) NOT NULL,
        email       TEXT
    );

    CREATE TABLE "GROUP" (
        group_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name  TEXT NOT NULL
    );

    CREATE TABLE GROUP_STUDENTS (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        group_id    INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES USERS(user_id),
        FOREIGN KEY (group_id) REFERENCES "GROUP"(group_id)
    );

    CREATE TABLE SUBJECT (
        subject_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name  TEXT NOT NULL
    );

    CREATE TABLE SCHEDULE (
        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id  INTEGER NOT NULL,
        teacher_id  INTEGER NOT NULL,
        group_id    INTEGER NOT NULL,
        date        TEXT NOT NULL,
        time        TEXT NOT NULL,
        room        TEXT,
        FOREIGN KEY (subject_id) REFERENCES SUBJECT(subject_id),
        FOREIGN KEY (teacher_id) REFERENCES USERS(user_id),
        FOREIGN KEY (group_id) REFERENCES "GROUP"(group_id)
    );

    CREATE TABLE ATTENDANCE (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id   INTEGER NOT NULL,
        user_id       INTEGER NOT NULL,
        status        TEXT NOT NULL,
        FOREIGN KEY (schedule_id) REFERENCES SCHEDULE(schedule_id),
        FOREIGN KEY (user_id) REFERENCES USERS(user_id)
    );
    """)

    # ============================
    # НАЧАЛЬНЫЕ ДАННЫЕ
    # ============================

    users = [
        ("admin", "admin123", "admin", "admin@mail.com"),
        ("teacher1", "teachpass", "teacher", "teach1@mail.com"),
        ("student1", "studpass", "student", "stud1@mail.com"),
        ("student2", "studpass", "student", "stud2@mail.com")
    ]

    cursor.executemany("""
        INSERT INTO USERS (username, password, role, email)
        VALUES (?, ?, ?, ?)
    """, users)

    groups = [("25-ИВТ-2-1",), ("25-ИВТ-2-2",)]
    cursor.executemany("""INSERT INTO "GROUP" (group_name) VALUES (?)""", groups)

    group_students = [
        (3, 1),  # student1 → group 1
        (4, 1)   # student2 → group 1
    ]
    cursor.executemany("""
        INSERT INTO GROUP_STUDENTS (user_id, group_id)
        VALUES (?, ?)
    """, group_students)

    subjects = [("Математика",), ("Информатика",)]
    cursor.executemany("""INSERT INTO SUBJECT (subject_name) VALUES (?)""", subjects)

    # Расписание
    schedule_rows = [
        (1, 2, 1, "2025-11-20", "10:00", "Ауд. 101"),
        (2, 2, 1, "2025-11-21", "12:00", "Ауд. 202")
    ]
    cursor.executemany("""
        INSERT INTO SCHEDULE (subject_id, teacher_id, group_id, date, time, room)
        VALUES (?, ?, ?, ?, ?, ?)
    """, schedule_rows)

    attendance_rows = [
        (1, 3, "present"),
        (1, 4, "absent"),
        (2, 3, "present"),
        (2, 4, "present")
    ]
    cursor.executemany("""
        INSERT INTO ATTENDANCE (schedule_id, user_id, status)
        VALUES (?, ?, ?)
    """, attendance_rows)

    conn.commit()

    print("База успешно создана и заполнена!")


    cursor.execute("""
    SELECT 
        a.attendance_id,
        u.username,
        g.group_name,
        s.date,
        s.time,
        sub.subject_name,
        a.status
    FROM ATTENDANCE a
    JOIN USERS u ON a.user_id = u.user_id
    JOIN SCHEDULE s ON a.schedule_id = s.schedule_id
    JOIN SUBJECT sub ON s.subject_id = sub.subject_id
    JOIN "GROUP" g ON s.group_id = g.group_id
    """)

    data = []
    for row in cursor.fetchall():
        attendance_id, username, group_name, date, time, subj, status = row

        data.append({
            "attendance_id": attendance_id,
            "student": username,
            "group": group_name,
            "date": date,
            "time": time,
            "subject": subj,
            "status": status
        })

    # ============================
    # EXPORT JSON
    # ============================
    with open("out/attendance.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # ============================
    # EXPORT YAML
    # ============================
    with open("out/attendance.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    # ============================
    # EXPORT CSV
    # ============================
    with open("out/attendance.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["attendance_id","student","group","date","time","subject","status"])
        for d in data:
            writer.writerow(d.values())

    # ============================
    # EXPORT XML
    # ============================
    root = ET.Element("attendance_records")
    for d in data:
        r = ET.SubElement(root, "record")
        for k, v in d.items():
            ET.SubElement(r, k).text = str(v)

    ET.ElementTree(root).write("out/attendance.xml", encoding="utf-8", xml_declaration=True)

    conn.close()


if __name__ == "__main__":
    main()
