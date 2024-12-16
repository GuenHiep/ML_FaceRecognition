from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('You must be an admin to access this page.', 'danger')
            return redirect(url_for('auth.teacher_login'))
        return f(*args, **kwargs)
    return decorated_function