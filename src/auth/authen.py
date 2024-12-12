# auth.py
from flask import session, flash, redirect, url_for, request, render_template
from ..dbconect import get_connection
import os
import subprocess

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
