from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from dbconect import get_connection
from datetime import timedelta

attendance = Blueprint('attendance', __name__)

@attendance.route("/", methods=["GET", "POST"])
def attendance_view():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

    selected_class = None 
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy danh sách các lớp học
    cursor.execute("SELECT DISTINCT class FROM student")
    classes = [row['class'] for row in cursor.fetchall()]

    # Lọc theo lớp
    if request.method == "POST":
        selected_class = request.form.get("class_filter")  # Lấy lớp từ form
        if selected_class:
            query = """
                SELECT attendance.idsv, attendance.users_name, student.class, attendance.timestamp, attendance.ip_address
                FROM attendance
                JOIN student ON attendance.idsv = student.idsv
                WHERE student.class = %s
                ORDER BY attendance.timestamp DESC
            """
            cursor.execute(query, (selected_class,))
            attendance_records = cursor.fetchall()
        else:
            flash("Please select a valid class.", "warning")
            return redirect(url_for("attendance.attendance_view"))
    else:
        # Hiển thị toàn bộ
        query = """
            SELECT attendance.idsv, attendance.users_name, student.class, attendance.timestamp, attendance.ip_address
            FROM attendance
            JOIN student ON attendance.idsv = student.idsv
            ORDER BY attendance.timestamp DESC
        """
        cursor.execute(query)
        attendance_records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "attendance.html",
        records=attendance_records,
        lecturer_name=session["lecturer_name"],
        classes=classes,
        selected_class=selected_class
    )



@attendance.route("/start", methods=["GET", "POST"])
def start_attendance():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        class_name = request.form.get("class_name")
        subject_name = request.form.get("subject_name")

        cursor.execute("""
            SELECT id FROM attendance_sessions
            WHERE class_name = %s AND end_time IS NULL
        """, (class_name,))
        existing_class_session = cursor.fetchone()

        cursor.execute("""
            SELECT id FROM attendance_sessions
            WHERE lecturer_id = %s AND end_time IS NULL
        """, (session["lecturer_id"],))
        existing_lecturer_session = cursor.fetchone()

        if existing_class_session:
            flash(f"An active attendance session already exists for class {class_name}.", "warning")
        elif existing_lecturer_session:
            flash("You already have an active attendance session. Please end it before starting a new one.", "warning")
        else:
            # Tạo phiên điểm danh mới
            cursor.execute(
                "INSERT INTO attendance_sessions (class_name, subject_name, lecturer_id) VALUES (%s, %s, %s)",
                (class_name, subject_name, session["lecturer_id"])
            )
            conn.commit()
            flash("Attendance session started successfully!", "success")

        cursor.close()
        conn.close()
        return redirect(url_for("attendance.start_attendance")) 

    # Lấy danh sách lớp và môn học
    cursor.execute("SELECT DISTINCT class_name FROM classes")
    classes = cursor.fetchall()
    cursor.execute("SELECT DISTINCT name FROM subject")
    subjects = cursor.fetchall()

    # Kiểm tra xem có phiên điểm danh đang hoạt động không
    cursor.execute("""
        SELECT id, class_name, subject_name, start_time FROM attendance_sessions
        WHERE lecturer_id = %s AND end_time IS NULL
        ORDER BY start_time DESC LIMIT 1
    """, (session["lecturer_id"],))
    active_session = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("start_attendance.html", classes=classes, subjects=subjects, active_session=active_session)


@attendance.route("/end", methods=["POST"])
def end_attendance():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy ID của phiên điểm danh đang hoạt động (sẽ được kết thúc)
    cursor.execute("""
        SELECT id 
        FROM attendance_sessions
        WHERE end_time IS NULL
        ORDER BY start_time DESC LIMIT 1
    """)
    active_session = cursor.fetchone()

    if not active_session:
        flash("No active attendance session to end.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("attendance.start_attendance"))

    session_id = active_session["id"]

    # Cập nhật thời gian kết thúc phiên điểm danh
    cursor.execute("""
        UPDATE attendance_sessions
        SET end_time = NOW()
        WHERE id = %s
    """, (session_id,))
    conn.commit()
    flash("Attendance session ended successfully!", "success")

    cursor.close()
    conn.close()

    return redirect(url_for("attendance.attendance_summary", session_id=session_id))



@attendance.route("/summary/<int:session_id>")
def attendance_summary(session_id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Lấy thông tin phiên điểm danh, bao gồm ngày bắt đầu và kết thúc
    cursor.execute("""
        SELECT class_name, subject_name, start_time, end_time 
        FROM attendance_sessions
        WHERE id = %s
    """, (session_id,))
    session_info = cursor.fetchone()

    if not session_info:
        flash("Attendance session not found.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("attendance.start_attendance"))

    # Lấy danh sách sinh viên trong lớp
    class_name = session_info["class_name"]
    cursor.execute("""
        SELECT idsv, users_name 
        FROM student
        WHERE class = %s
    """, (class_name,))
    students = cursor.fetchall()

    # Lấy danh sách điểm danh trong phiên
    cursor.execute("""
        SELECT idsv, timestamp 
        FROM attendance 
        WHERE session_id = %s
    """, (session_id,))
    attendance_records = cursor.fetchall()

    # Tạo dictionary để kiểm tra trạng thái điểm danh
    attendance_by_date = {}
    for record in attendance_records:
        attendance_date = record["timestamp"].strftime("%d-%b-%Y")  # Format ngày
        if attendance_date not in attendance_by_date:
            attendance_by_date[attendance_date] = set()
        attendance_by_date[attendance_date].add(record["idsv"])

    # Lấy các ngày trong phiên điểm danh
    days = []
    current_date = session_info["start_time"].date()
    end_date = session_info["end_time"].date() if session_info["end_time"] else current_date

    # Duyệt qua từng ngày từ start_time đến end_time
    while current_date <= end_date:
        days.append(current_date.strftime("%d-%b-%Y"))
        current_date += timedelta(days=1)

    # Kết hợp danh sách sinh viên với trạng thái điểm danh theo từng ngày
    for student in students:
        student["attendance"] = {day: "" if student["idsv"] in attendance_by_date.get(day, set()) else "v" for day in days}

    cursor.close()
    conn.close()

    return render_template("attendance_summary.html", session_info=session_info, students=students, days=days)



