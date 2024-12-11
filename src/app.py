import subprocess
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
import socket
from functools import wraps

app = Flask(__name__)
app.secret_key = "QDJSUIEWFNQKOWFMDVI"
# Kết nối MySQL
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="tuananh1582",
        database="face_re"
    )

# Trang đăng nhập student
@app.route("/", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        idsv = request.form["idsv"]
        password = request.form["password"]

        # Kiểm tra thông tin đăng nhập
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM student WHERE idsv = %s AND user_password = %s"
        cursor.execute(query, (idsv, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["user_id"] = user["idsv"]
            session["user_name"] = user["users_name"]
            session["user_class"] = user["class"]
            flash("Student login successful!", "success")
            try:
                script_path = os.path.join(os.getcwd(), 'src', 'recognize_face.py')
                subprocess.Popen(["python", script_path, idsv])
                flash("Face recognition process started.", "info")
            except Exception as e:
                flash(f"Error starting face recognition: {e}", "danger")
            
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid IDSV or password. Please try again.", "danger")

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
        return redirect(url_for("login"))

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


#CRUD student
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('You must be an admin to access this page.', 'danger')
            return redirect(url_for('teacher_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/students", methods=["GET"])
@admin_required
def students_list():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM student ORDER BY class, idsv")
    students = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("students.html", students=students)


@app.route("/students/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        idsv = request.form.get("idsv")
        users_name = request.form.get("users_name")
        student_class = request.form.get("class")
        user_password = request.form.get("user_password")

        conn = get_connection()
        cursor = conn.cursor()
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
        return redirect(url_for("login"))

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
        return redirect(url_for("login"))

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
        return redirect(url_for("login"))

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
        return redirect(url_for("login"))

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
        return redirect(url_for("login"))

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
        return redirect(url_for("login"))

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


