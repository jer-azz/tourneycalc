from functools import wraps
from datetime import datetime
import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import Player, Tournament, TournamentState, Round, RoundState, Match, Registration
from pairings import random_pairings, swiss_pairings, all_results_in
bp = Blueprint("admin", __name__, url_prefix="/admin")

def admin_required(view):
    @wraps(view)
    def wrapper(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin: abort(403)
        return view(*a, **kw)
    return wrapper

def slugify(s):
    s = s.lower().replace("å","a").replace("ä","a").replace("ö","o")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "tournament"

@bp.route("/")
@login_required
@admin_required
def dashboard():
    tournaments = Tournament.query.order_by(Tournament.date.desc()).all()
    return render_template("admin/dashboard.html", tournaments=tournaments, players_count=Player.query.count())

@bp.route("/players")
@login_required
@admin_required
def players():
    return render_template("admin/players.html", players=Player.query.order_by(Player.created_at.desc()).all())

@bp.route("/players/new", methods=["GET","POST"])
@login_required
@admin_required
def player_new():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        if Player.query.filter((Player.username == username) | (Player.email == email)).first():
            flash("Anvandarnamn/e-post upptaget.", "danger")
        else:
            p = Player(username=username, email=email,
                display_name=request.form["display_name"].strip() or username,
                faction=request.form.get("faction","").strip(),
                is_admin=bool(request.form.get("is_admin")))
            p.set_password(request.form["password"])
            db.session.add(p); db.session.commit()
            flash("Spelare skapad.", "success")
            return redirect(url_for("admin.players"))
    return render_template("admin/player_form.html", player=None)

@bp.route("/players/<int:pid>/edit", methods=["GET","POST"])
@login_required
@admin_required
def player_edit(pid):
    p = db.get_or_404(Player, pid)
    if request.method == "POST":
        p.display_name = request.form["display_name"].strip() or p.username
        p.email = request.form["email"].strip().lower()
        p.faction = request.form.get("faction","").strip()
        if request.form.get("password"): p.set_password(request.form["password"])
        if p.id != current_user.id: p.is_admin = bool(request.form.get("is_admin"))
        db.session.commit(); flash("Uppdaterad.", "success")
        return redirect(url_for("admin.players"))
    return render_template("admin/player_form.html", player=p)

@bp.route("/players/<int:pid>/delete", methods=["POST"])
@login_required
@admin_required
def player_delete(pid):
    p = db.get_or_404(Player, pid)
    if p.id == current_user.id:
        flash("Du kan inte ta bort dig sjalv.", "danger")
    else:
        db.session.delete(p); db.session.commit(); flash("Borttagen.", "info")
    return redirect(url_for("admin.players"))

@bp.route("/tournaments/new", methods=["GET","POST"])
@login_required
@admin_required
def tournament_new():
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            slug = slugify(name); i = 2
            while Tournament.query.filter_by(slug=slug).first():
                slug = f"{slugify(name)}-{i}"; i += 1
            t = Tournament(name=name, slug=slug,
                date=datetime.strptime(request.form["date"], "%Y-%m-%d").date(),
                location=request.form["location"].strip(),
                description=request.form.get("description","").strip(),
                num_rounds=int(request.form.get("num_rounds", 3)),
                points_limit=int(request.form.get("points_limit", 800)),
                win_tp=int(request.form.get("win_tp", 3)),
                draw_tp=int(request.form.get("draw_tp", 1)),
                loss_tp=int(request.form.get("loss_tp", 0)),
                created_by=current_user.id)
            db.session.add(t); db.session.commit()
            flash("Turnering skapad.", "success")
            return redirect(url_for("admin.tournament_manage", slug=t.slug))
        except (KeyError, ValueError) as e:
            flash(f"Felaktig indata: {e}", "danger")
    return render_template("admin/tournament_form.html", t=None)

@bp.route("/t/<slug>")
@login_required
@admin_required
def tournament_manage(slug):
    t = Tournament.query.filter_by(slug=slug).first_or_404()
    all_players = Player.query.order_by(Player.display_name).all()
    return render_template("admin/tournament_manage.html", t=t, all_players=all_players)

@bp.route("/t/<slug>/state", methods=["POST"])
@login_required
@admin_required
def tournament_state(slug):
    t = Tournament.query.filter_by(slug=slug).first_or_404()
    target = request.form["state"]
    flow = {"draft": TournamentState.REGISTRATION, "registration": TournamentState.IN_PROGRESS, "in_progress": TournamentState.FINISHED}
    new = flow.get(t.state.value)
    if new and target == new.value:
        t.state = new; db.session.commit(); flash(f"Status: {t.state.label}", "success")
    else:
        flash("Ogiltig overgang.", "danger")
    return redirect(url_for("admin.tournament_manage", slug=slug))

@bp.route("/t/<slug>/generate_round", methods=["POST"])
@login_required
@admin_required
def generate_round(slug):
    t = Tournament.query.filter_by(slug=slug).first_or_404()
    if t.state != TournamentState.IN_PROGRESS:
        flash("Turneringen maste vara igang.", "danger")
        return redirect(url_for("admin.tournament_manage", slug=slug))
    n = len(t.rounds) + 1
    if n > t.num_rounds:
        flash("Alla rundor ar genererade.", "warning")
        return redirect(url_for("admin.tournament_manage", slug=slug))
    if n > 1:
        prev = t.rounds[-1]
        if not all_results_in(prev):
            flash("Alla resultat maste rapporteras innan nasta runda.", "danger")
            return redirect(url_for("admin.tournament_manage", slug=slug))
        prev.state = RoundState.COMPLETE
    pairs = random_pairings(t) if n == 1 else swiss_pairings(t)
    rnd = Round(tournament_id=t.id, number=n, state=RoundState.ACTIVE)
    db.session.add(rnd); db.session.flush()
    for i, (p1, p2) in enumerate(pairs, 1):
        m = Match(round_id=rnd.id, table_number=i, player1_id=p1.id, player2_id=p2.id if p2 else None)
        if p2 is None:
            m.p1_tp = t.win_tp; m.p1_kp = 0; m.confirmed = True
        db.session.add(m)
    db.session.commit(); flash(f"Runda {n} genererad.", "success")
    return redirect(url_for("admin.tournament_manage", slug=slug))

@bp.route("/t/<slug>/registration/<int:rid>/toggle_paid", methods=["POST"])
@login_required
@admin_required
def toggle_paid(slug, rid):
    r = db.get_or_404(Registration, rid); r.paid = not r.paid; db.session.commit()
    return redirect(url_for("admin.tournament_manage", slug=slug))

@bp.route("/t/<slug>/registration/<int:rid>/drop", methods=["POST"])
@login_required
@admin_required
def drop_player(slug, rid):
    r = db.get_or_404(Registration, rid); r.dropped = not r.dropped; db.session.commit()
    flash("Spelare " + ("avhoppad" if r.dropped else "aterinsatt"), "info")
    return redirect(url_for("admin.tournament_manage", slug=slug))

@bp.route("/t/<slug>/add_player", methods=["POST"])
@login_required
@admin_required
def add_player_to_tournament(slug):
    t = Tournament.query.filter_by(slug=slug).first_or_404()
    pid = int(request.form["player_id"])
    if not any(r.player_id == pid for r in t.registrations):
        db.session.add(Registration(tournament_id=t.id, player_id=pid)); db.session.commit()
        flash("Spelare tillagd.", "success")
    return redirect(url_for("admin.tournament_manage", slug=slug))
