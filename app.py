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
from models import User
from models import User, Task
from datetime import datetime

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
    return render_template("dashboard.html")


@app.route("/tasks")
@login_required
def tasks():

    tasks = (
        Task.query.filter_by(user_id=current_user.id)
        .order_by(Task.created_at.desc())
        .all()
    )

    return render_template(
        "tasks.html",
        tasks=tasks,
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


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
