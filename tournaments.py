from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from extensions import db
from models import Tournament, TournamentState, Match, Registration
from pairings import compute_standings
bp = Blueprint("t", __name__, url_prefix="/t")

@bp.route("/")
def index():
    return render_template("tournaments/list.html",
        tournaments=Tournament.query.order_by(Tournament.date.desc()).all())

@bp.route("/<slug>")
def detail(slug):
    t = Tournament.query.filter_by(slug=slug).first_or_404()
    tab = request.args.get("tab", "overview")
    standings = compute_standings(t) if tab == "standings" else None
    is_registered = current_user.is_authenticated and any(r.player_id == current_user.id for r in t.registrations)
    return render_template("tournaments/detail.html", t=t, tab=tab, standings=standings, is_registered=is_registered)

@bp.route("/<slug>/register", methods=["POST"])
@login_required
def register(slug):
    t = Tournament.query.filter_by(slug=slug).first_or_404()
    if t.state != TournamentState.REGISTRATION:
        flash("Anmalan ar inte oppen.", "danger"); return redirect(url_for("t.detail", slug=slug))
    if not any(r.player_id == current_user.id for r in t.registrations):
        db.session.add(Registration(tournament_id=t.id, player_id=current_user.id, army_list=request.form.get("army_list","").strip()))
        db.session.commit(); flash("Du ar anmald!", "success")
    return redirect(url_for("t.detail", slug=slug, tab="players"))

@bp.route("/<slug>/unregister", methods=["POST"])
@login_required
def unregister(slug):
    t = Tournament.query.filter_by(slug=slug).first_or_404()
    if t.state != TournamentState.REGISTRATION:
        flash("Avanmalan stangd - kontakta arrangoren.", "danger"); return redirect(url_for("t.detail", slug=slug))
    Registration.query.filter_by(tournament_id=t.id, player_id=current_user.id).delete()
    db.session.commit(); flash("Avanmald.", "info")
    return redirect(url_for("t.detail", slug=slug))

@bp.route("/match/<int:mid>/report", methods=["GET","POST"])
@login_required
def match_report(mid):
    m = db.get_or_404(Match, mid)
    if current_user.id not in (m.player1_id, m.player2_id) and not current_user.is_admin: abort(403)
    if request.method == "POST":
        try:
            m.p1_tp = float(request.form["p1_tp"]); m.p1_kp = float(request.form["p1_kp"])
            if not m.is_bye:
                m.p2_tp = float(request.form["p2_tp"]); m.p2_kp = float(request.form["p2_kp"])
            m.confirmed = True; db.session.commit(); flash("Resultat sparat.", "success")
            return redirect(url_for("t.detail", slug=m.round.tournament.slug, tab="pairings"))
        except (KeyError, ValueError) as e: flash(f"Felaktig indata: {e}", "danger")
    return render_template("tournaments/match_report.html", m=m)
