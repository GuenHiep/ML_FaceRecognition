from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from dbconect import get_connection
from routes.utils import admin_required

subjects = Blueprint('subjects', __name__)

@subjects.route("/", methods=["GET"])
@admin_required
def subjects_list():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM subject ORDER BY id")
    subjects = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("subjects.html", subjects=subjects)

@subjects.route("/add", methods=["GET", "POST"])
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

        return redirect(url_for("subjects.subjects_list"))

    return render_template("add_subject.html")

@subjects.route("/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_subject(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM subject WHERE id = %s", (id,))
    subject = cursor.fetchone()
    cursor.close()

    if not subject:
        flash("Subject not found.", "danger")
        return redirect(url_for("subjects.subjects_list"))

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

        return redirect(url_for("subjects.subjects_list"))

    return render_template("edit_subject.html", subject=subject)

@subjects.route("/delete/<int:id>", methods=["POST"])
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

    return redirect(url_for("subjects.subjects_list"))
