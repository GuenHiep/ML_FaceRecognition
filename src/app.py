import subprocess
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
import socket
from functools import wraps
from dbconect import get_connection
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "QDJSUIEWFNQKOWFMDVI"
# Kết nối MySQL
# def get_connection():
#     return mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="tuananh1582",
#         database="face_re"
#     )

# Trang đăng nhập student
@app.route("/", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        idsv = request.form["idsv"]
        password = request.form["password"]

        # Kiểm tra thông tin đăng nhập
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Lấy phiên điểm danh hiện tại
        cursor.execute("""
            SELECT class_name, subject_name FROM attendance_sessions
            WHERE start_time <= NOW() AND (end_time IS NULL OR end_time >= NOW())
            ORDER BY start_time DESC LIMIT 1
        """)
        session_info = cursor.fetchone()

        if not session_info:
            flash("No active attendance session available. Please try again later.", "danger")
            cursor.close()
            conn.close()
            return render_template("login.html")

        # Kiểm tra sinh viên có thuộc lớp và môn học của phiên điểm danh không
        query = """
            SELECT * FROM student 
            WHERE idsv = %s AND user_password = %s AND class = %s
        """
        cursor.execute(query, (idsv, password, session_info["class_name"]))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            # Nếu sinh viên hợp lệ, đăng nhập và chuyển đến dashboard
            session["user_id"] = user["idsv"]
            session["user_name"] = user["users_name"]
            session["user_class"] = user["class"]
            session["user_subject"] = session_info["subject_name"]  # Thêm thông tin môn học vào session

            flash("Login successful! You can now mark your attendance.", "success")

            # Bắt đầu nhận diện khuôn mặt
            try:
                script_path = os.path.join(os.getcwd(), 'src', 'recognize_face.py')
                subprocess.Popen(["python", script_path, idsv])
                flash("Face recognition process started.", "info")
            except Exception as e:
                flash(f"Error starting face recognition: {e}", "danger")

            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials or you are not eligible for this attendance session.", "danger")

    return render_template("login.html")




# Trang đăng nhập teacher
@app.route("/teacher", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Kiểm tra nếu là tài khoản admin
        if email == "admin@gmail.com" and password == "admin":
            session["lecturer_id"] = None
            session["lecturer_name"] = "Admin"
            session["role"] = "admin"
            flash("Admin login successful!", "success")
            return redirect(url_for("students_list"))

        # Kiểm tra thông tin đăng nhập với bảng teacher (giảng viên)
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM teacher WHERE email = %s AND password = %s"
        cursor.execute(query, (email, password))
        lecturer = cursor.fetchone()
        cursor.close()
        conn.close()

        if lecturer:
            session["lecturer_id"] = lecturer["id"]
            session["lecturer_name"] = lecturer["name"]
            session["role"] = "teacher"  # Gán quyền là giảng viên
            flash("Teacher login successful!", "success")
            return redirect(url_for("attendance_view"))  # Redirect đến trang điểm danh
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("login_teacher.html")


# Trang Dashboard (Student)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("student_login"))

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        user_class=session["user_class"]
    )

# Thông tin điểm danh (Teacher)
@app.route("/attendance", methods=["GET", "POST"])
def attendance_view():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

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
            return redirect(url_for("attendance_view"))
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

#Attendance 
@app.route("/attendance/start", methods=["GET", "POST"])
def start_attendance():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))
    
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
        return redirect(url_for("start_attendance"))  # Refresh the page to show active session

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

@app.route("/attendance/end", methods=["POST"])
def end_attendance():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

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
        return redirect(url_for("start_attendance"))

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

    return redirect(url_for("attendance_summary", session_id=session_id))


@app.route("/attendance/summary/<int:session_id>")
def attendance_summary(session_id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

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
        return redirect(url_for("start_attendance"))

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



#CRUD student
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('You must be an admin to access this page.', 'danger')
            return redirect(url_for('teacher_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/students", methods=["GET","POST"])
#@admin_required
def students_list():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT class FROM student ORDER BY class")
    classes = cursor.fetchall()
    
    students = []
    selected_class = None
    
    if request.method == "POST":
        selected_class = request.form.get("class")
        if selected_class:
            cursor.execute(
                "SELECT * FROM student WHERE class = %s ORDER BY users_name", 
                (selected_class,)
            )
            students = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "students.html", 
        students=students, 
        classes=classes, 
        selected_class=selected_class
    )


@app.route("/students/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    if request.method == "POST":
        idsv = request.form.get("idsv")
        users_name = request.form.get("users_name")
        student_class = request.form.get("class")
        user_password = request.form.get("user_password")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM classes WHERE class_name = %s", (student_class,))
        class_exists = cursor.fetchone()

        if not class_exists:
            cursor.execute("INSERT INTO classes (class_name) VALUES (%s)", (student_class,))
            conn.commit()
        
        cursor.execute(
            "INSERT INTO student (idsv, users_name, class, user_password) VALUES (%s, %s, %s, %s)",
            (idsv, users_name, student_class, user_password),
        )
        conn.commit()
        cursor.close()
        conn.close()

        try:
            capture_script_path = os.path.join(os.getcwd(), 'src', 'capture_images.py')
            subprocess.run(["python", capture_script_path, idsv], check=True)

            train_script_path = os.path.join(os.getcwd(), 'src', 'train_model.py')
            subprocess.run(["python", train_script_path], check=True)

            flash("Face recognition and training process completed successfully.", "success")
        except subprocess.CalledProcessError as e:
            flash(f"Error during face recognition or training: {e}", "danger")

        return redirect(url_for("students_list"))

    return render_template("add_student.html")

@app.route("/students/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_student(id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM student WHERE id = %s", (id,))
    student = cursor.fetchone()
    cursor.close()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("students_list"))

    if request.method == "POST":
        idsv = request.form.get("idsv")
        users_name = request.form.get("users_name")
        student_class = request.form.get("class")
        user_password = request.form.get("user_password")

        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE attendance
                SET idsv = %s
                WHERE idsv = %s
                """,
                (idsv, student['idsv'])
            )

            cursor.execute(
                """
                UPDATE student 
                SET idsv = %s, users_name = %s, class = %s, user_password = %s
                WHERE id = %s
                """,
                (idsv, users_name, student_class, user_password, id),
            )
            conn.commit()
            flash("Student updated successfully!", "success")
            return redirect(url_for("students_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating student: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("edit_student.html", student=student)

@app.route("/students/delete/<int:id>", methods=["POST"])
@admin_required
def delete_student(id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM attendance WHERE idsv = (SELECT idsv FROM student WHERE id = %s)", (id,))

        cursor.execute("DELETE FROM student WHERE id = %s", (id,))
        conn.commit()

        flash("Student deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting student: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("students_list"))


#CRUD Teacher

@app.route("/teachers_list", methods=["GET"])
@admin_required
def teachers_list():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teacher ORDER BY id, name")
    teachers = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("teachers.html", teachers=teachers)


@app.route("/teachers/add", methods=["GET", "POST"])
@admin_required
def add_teacher():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO teacher (name, email, password) VALUES (%s, %s, %s)",
                (name, email, password),
            )
            conn.commit()
            flash("Teacher added successfully.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"An error occurred: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("teachers_list"))

    return render_template("add_teacher.html")


@app.route("/teachers/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_teacher(id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teacher WHERE id = %s", (id,))
    teacher = cursor.fetchone()
    cursor.close()

    if not teacher:
        flash("Teacher not found.", "danger")
        return redirect(url_for("teachers_list"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE teacher 
                SET name = %s, email = %s, password = %s
                WHERE id = %s
                """,
                (name, email, password, id),
            )
            conn.commit()
            return redirect(url_for("teachers_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating teacher: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("edit_teacher.html", teacher=teacher)

@app.route("/teachers/delete/<int:id>", methods=["POST"])
@admin_required
def delete_teacher(id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM teacher WHERE id = %s", (id,))
        conn.commit()

    except Exception as e:
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("teachers_list"))

#CRUD subject
@app.route("/subjects", methods=["GET"])
@admin_required
def subjects_list():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM subject ORDER BY id")
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("subjects.html", subjects=subjects)

@app.route("/subjects/add", methods=["GET", "POST"])
@admin_required
def add_subject():
    if request.method == "POST":
        code = request.form.get("code")
        name = request.form.get("name")
        credits = request.form.get("credits")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO subject (code, name, credits) VALUES (%s, %s, %s)",
                (code, name, credits)
            )
            conn.commit()
            flash("Subject added successfully.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"An error occurred: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("subjects_list"))

    return render_template("add_subject.html")

@app.route("/subjects/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_subject(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM subject WHERE id = %s", (id,))
    subject = cursor.fetchone()
    cursor.close()

    if not subject:
        flash("Subject not found.", "danger")
        return redirect(url_for("subjects_list"))

    if request.method == "POST":
        code = request.form.get("code")
        name = request.form.get("name")
        credits = request.form.get("credits")

        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE subject 
                SET code = %s, name = %s, credits = %s
                WHERE id = %s
                """,
                (code, name, credits, id)
            )
            conn.commit()
            flash("Subject updated successfully!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error updating subject: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("subjects_list"))

    return render_template("edit_subject.html", subject=subject)

@app.route("/subjects/delete/<int:id>", methods=["POST"])
@admin_required
def delete_subject(id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM subject WHERE id = %s", (id,))
        conn.commit()
        flash("Subject deleted successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting subject: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("subjects_list"))

@app.route("/classes", methods=["GET"])
# @admin_required
def classes_list():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Truy vấn kết hợp thông tin lớp học và sĩ số
    cursor.execute("""
        SELECT c.id, c.class_name, 
               COUNT(s.id) AS student_count
        FROM classes c
        LEFT JOIN student s ON c.class_name = s.class
        GROUP BY c.id, c.class_name
        ORDER BY c.id
    """)
    classes = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template("classes.html", classes=classes)


# Đăng xuất
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("student_login"))


def get_current_ip():
    try:
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception as e:
        return "Unknown IP"

if __name__ == "__main__":
    app.run(debug=True)


