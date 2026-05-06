from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from extensions import db
from models import Player
bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("home"))
    if request.method == "POST":
        ident = request.form["username"].strip(); pw = request.form["password"]
        user = Player.query.filter_by(username=ident).first() or Player.query.filter_by(email=ident.lower()).first()
        if user and user.check_password(pw):
            login_user(user, remember=True)
            flash(f"Valkommen {user.display_name}!", "success")
            return redirect(request.args.get("next") or url_for("home"))
        flash("Fel anvandarnamn eller losenord.", "danger")
    return render_template("auth/login.html")

@bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        display_name = request.form["display_name"].strip() or username
        pw = request.form["password"]
        if Player.query.filter_by(username=username).first(): flash("Anvandarnamnet ar upptaget.", "danger")
        elif Player.query.filter_by(email=email).first(): flash("E-postadressen ar registrerad.", "danger")
        else:
            p = Player(username=username, email=email, display_name=display_name)
            p.set_password(pw)
            if Player.query.count() == 0: p.is_admin = True
            db.session.add(p); db.session.commit()
            flash("Konto skapat. Logga in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html")

@bp.route("/logout")
def logout():
    logout_user(); flash("Utloggad.", "info")
    return redirect(url_for("home"))
