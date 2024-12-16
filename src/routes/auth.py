from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from dbconect import get_connection
import subprocess
import os

auth = Blueprint('auth', __name__)

#Student
@auth.route("/", methods=["GET", "POST"])
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

            return redirect(url_for("auth.dashboard"))  # Cập nhật ở đây
        else:
            flash("Invalid credentials or you are not eligible for this attendance session.", "danger")

    return render_template("login.html")


@auth.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.student_login"))  # Cập nhật ở đây

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        user_class=session["user_class"]
    )

#Teacher
@auth.route("/teacher", methods=["GET", "POST"])
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
            return redirect(url_for("students.students_list"))

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
            return redirect(url_for("attendance.attendance_view"))  # Redirect đến trang điểm danh
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("login_teacher.html")

@auth.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.student_login"))