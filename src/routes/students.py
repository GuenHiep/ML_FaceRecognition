from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from dbconect import get_connection
from routes.utils import admin_required
import subprocess
import os

students = Blueprint('students', __name__)

@students.route("/", methods=["GET", "POST"])
def students_list():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

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

@students.route("/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

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

        return redirect(url_for("students.students_list"))

    return render_template("add_student.html")


@students.route("/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_student(id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM student WHERE id = %s", (id,))
    student = cursor.fetchone()
    cursor.close()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("students.students_list"))

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
            return redirect(url_for("students.students_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating student: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("edit_student.html", student=student)



@students.route("/delete/<int:id>", methods=["POST"])
@admin_required
def delete_student(id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

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

    return redirect(url_for("students.students_list"))


