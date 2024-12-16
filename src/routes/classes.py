from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from dbconect import get_connection
from routes.utils import admin_required

classes = Blueprint('classes', __name__)

@classes.route("/", methods=["GET"])
# @admin_required
def classes_list():
    if "lecturer_id" not in session:
        flash("Please login first.", "warning")
        return redirect(url_for("auth.teacher_login"))

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
