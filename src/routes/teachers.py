from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from dbconect import get_connection
from routes.utils import admin_required

teachers = Blueprint('teachers', __name__)

@teachers.route("/", methods=["GET", "POST"])
@admin_required
def teachers_list():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teacher ORDER BY id, name")
    teachers = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("teachers.html", teachers=teachers)

@teachers.route("/add", methods=["GET", "POST"])
@admin_required
def add_teacher():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

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

        return redirect(url_for("teachers.teachers_list"))

    return render_template("add_teacher.html")

@teachers.route("/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_teacher(id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teacher WHERE id = %s", (id,))
    teacher = cursor.fetchone()
    cursor.close()

    if not teacher:
        flash("Teacher not found.", "danger")
        return redirect(url_for("teachers.teachers_list"))

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
            return redirect(url_for("teachers.teachers_list"))
        except Exception as e:
            conn.rollback()
            flash(f"Error updating teacher: {e}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("edit_teacher.html", teacher=teacher)

@teachers.route("/delete/<int:id>", methods=["POST"])
@admin_required
def delete_teacher(id):
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

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

    return redirect(url_for("teachers.teachers_list"))
