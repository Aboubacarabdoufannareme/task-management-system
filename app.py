from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from config import Config
from extensions import db, login_manager
from models import User, Task
from datetime import datetime, timedelta
import csv
from io import StringIO
from flask import Response
from openpyxl import Workbook
from io import BytesIO
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
@login_required
def dashboard():

    total_tasks = Task.query.filter_by(user_id=current_user.id).count()

    pending_tasks = Task.query.filter_by(
        user_id=current_user.id, status="Pending"
    ).count()

    in_progress_tasks = Task.query.filter_by(
        user_id=current_user.id, status="In Progress"
    ).count()

    completed_tasks = Task.query.filter_by(
        user_id=current_user.id, status="Completed"
    ).count()
    completion_rate = 0

    if total_tasks > 0:
        completion_rate = round((completed_tasks / total_tasks) * 100)

    notifications = []

    overdue = Task.query.filter(
        Task.user_id == current_user.id,
        Task.status != "Completed",
        Task.due_date < datetime.today().date(),
    ).all()

    if overdue:
        notifications.append(f"You have {len(overdue)} overdue task(s).")

    today_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.status != "Completed",
        Task.due_date == datetime.today().date(),
    ).all()

    if today_tasks:
        notifications.append(f"{len(today_tasks)} task(s) due today.")

    recent_tasks = (
        Task.query.filter_by(user_id=current_user.id)
        .order_by(Task.created_at.desc())
        .limit(5)
        .all()
    )

    upcoming_tasks = (
        Task.query.filter_by(user_id=current_user.id)
        .order_by(Task.due_date.asc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        completed_tasks=completed_tasks,
        recent_tasks=recent_tasks,
        upcoming_tasks=upcoming_tasks,
        completion_rate=completion_rate,
        notifications=notifications,
    )


@app.route("/tasks")
@login_required
def tasks():

    search = request.args.get("search", "")

    status = request.args.get("status", "")

    priority = request.args.get("priority", "")

    query = Task.query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(Task.title.contains(search))

    if status:
        query = query.filter_by(status=status)

    if priority:
        query = query.filter_by(priority=priority)

    tasks = query.order_by(Task.pinned.desc(), Task.due_date.asc())

    return render_template(
        "tasks.html",
        tasks=tasks,
        search=search,
        status=status,
        priority=priority,
        today=datetime.today().date(),
        today_plus_3=datetime.today().date() + timedelta(days=3),
    )


@app.route("/tasks/add", methods=["GET", "POST"])
@login_required
def add_task():

    if request.method == "POST":
        task = Task(
            title=request.form["title"],
            description=request.form["description"],
            priority=request.form["priority"],
            status=request.form["status"],
            due_date=datetime.strptime(request.form["due_date"], "%Y-%m-%d").date(),
            user_id=current_user.id,
            category=request.form["category"],
        )

        db.session.add(task)

        db.session.commit()

        flash("Task created successfully!", "success")

        return redirect(url_for("tasks"))

    return render_template("add_task.html")


@app.route("/tasks/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_task(id):

    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        task.title = request.form["title"]

        task.description = request.form["description"]

        task.priority = request.form["priority"]

        task.status = request.form["status"]

        task.due_date = datetime.strptime(request.form["due_date"], "%Y-%m-%d").date()
        task.category = request.form["category"]

        db.session.commit()

        flash("Task updated!", "success")

        return redirect(url_for("tasks"))

    return render_template(
        "edit_task.html",
        task=task,
    )


@app.route("/tasks/delete/<int:id>")
@login_required
def delete_task(id):

    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    db.session.delete(task)

    db.session.commit()

    flash("Task deleted.", "success")

    return redirect(url_for("tasks"))


@app.route("/tasks/export/csv")
@login_required
def export_tasks_csv():

    tasks = Task.query.filter_by(user_id=current_user.id).all()

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow(["Title", "Category", "Priority", "Status", "Due Date"])

    for task in tasks:
        writer.writerow(
            [task.title, task.category, task.priority, task.status, task.due_date]
        )

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=tasks.csv"},
    )


@app.route("/tasks/export/pdf")
@login_required
def export_tasks_pdf():

    tasks = Task.query.filter_by(user_id=current_user.id).all()

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)

    pdf.setFont("Helvetica-Bold", 16)

    pdf.drawString(50, 800, "Task Report")

    y = 760

    pdf.setFont("Helvetica", 11)

    for task in tasks:
        pdf.drawString(50, y, f"{task.title} | {task.priority} | {task.status}")

        y -= 20

    pdf.save()

    buffer.seek(0)

    return Response(
        buffer,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tasks.pdf"},
    )


@app.route("/tasks/export/excel")
@login_required
def export_tasks_excel():

    tasks = Task.query.filter_by(user_id=current_user.id).all()

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = "Tasks"

    sheet.append(["Title", "Category", "Priority", "Status", "Due Date"])

    for task in tasks:
        sheet.append(
            [task.title, task.category, task.priority, task.status, str(task.due_date)]
        )

    output = BytesIO()

    workbook.save(output)

    output.seek(0)

    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tasks.xlsx"},
    )


@app.route("/tasks/complete/<int:id>")
@login_required
def complete_task(id):

    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    task.status = "Completed"

    db.session.commit()

    flash("Task completed!", "success")

    return redirect(url_for("tasks"))


@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash("Username or email already exists.", "danger")
            return redirect(url_for("register"))

        user = User(
            username=username,
            email=email,
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/tasks/favorite/<int:id>")
@login_required
def favorite_task(id):

    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    task.favorite = not task.favorite

    db.session.commit()

    return redirect(url_for("tasks"))


@app.route("/tasks/pin/<int:id>")
@login_required
def pin_task(id):

    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    task.pinned = not task.pinned

    db.session.commit()

    return redirect(url_for("tasks"))


@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)

            flash("Welcome back!", "success")

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash("Logged out successfully.", "success")

    return redirect(url_for("login"))


@app.route("/profile")
@login_required
def profile():

    return render_template("profile.html", user=current_user)


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    if request.method == "POST":
        current_password = request.form["current_password"]

        new_password = request.form["new_password"]

        confirm_password = request.form["confirm_password"]

        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")

            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")

            return redirect(url_for("change_password"))

        current_user.set_password(new_password)
        if len(new_password) < 8:

    flash(
        "Password must be at least 8 characters.",
        "danger"
    )

    return redirect(url_for("change_password"))

        db.session.commit()

        flash("Password changed successfully!", "success")

        return redirect(url_for("profile"))

    return render_template("change_password.html")


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
