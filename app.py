"""TourneyCalc - standalone Flask app."""
from __future__ import annotations
import os
from flask import Flask, render_template
from extensions import db, login_manager
from models import Player

def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///tourneycalc.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if config: app.config.update(config)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Logga in for att fortsatta."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(uid):
        return db.session.get(Player, int(uid))

    from auth import bp as auth_bp
    from admin import bp as admin_bp
    from tournaments import bp as t_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(t_bp)
    from cli import register_cli
    register_cli(app)

    @app.route("/")
    def home():
        from models import Tournament, TournamentState
        active = Tournament.query.filter(Tournament.state.in_([TournamentState.REGISTRATION, TournamentState.IN_PROGRESS])).order_by(Tournament.date.asc()).all()
        upcoming = Tournament.query.filter(Tournament.state == TournamentState.DRAFT).order_by(Tournament.date.asc()).all()
        finished = Tournament.query.filter(Tournament.state == TournamentState.FINISHED).order_by(Tournament.date.desc()).limit(5).all()
        return render_template("home.html", active=active, upcoming=upcoming, finished=finished)
    return app

app = create_app()
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
