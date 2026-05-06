from __future__ import annotations
import enum
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class TournamentState(str, enum.Enum):
    DRAFT = "draft"
    REGISTRATION = "registration"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    @property
    def label(self):
        return {"draft":"Utkast","registration":"Anmalan oppen","in_progress":"Pagar","finished":"Avslutad"}[self.value]
    @property
    def css(self):
        return {"draft":"badge-muted","registration":"badge-info","in_progress":"badge-active","finished":"badge-done"}[self.value]

class RoundState(str, enum.Enum):
    ACTIVE = "active"
    COMPLETE = "complete"

class Player(UserMixin, db.Model):
    __tablename__ = "players"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    faction = db.Column(db.String(120), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class Tournament(db.Model):
    __tablename__ = "tournaments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    num_rounds = db.Column(db.Integer, default=3, nullable=False)
    points_limit = db.Column(db.Integer, default=800)
    win_tp = db.Column(db.Integer, default=3)
    draw_tp = db.Column(db.Integer, default=1)
    loss_tp = db.Column(db.Integer, default=0)
    state = db.Column(db.Enum(TournamentState), default=TournamentState.DRAFT, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("players.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator = db.relationship("Player")
    registrations = db.relationship("Registration", backref="tournament", cascade="all, delete-orphan")
    rounds = db.relationship("Round", backref="tournament", cascade="all, delete-orphan", order_by="Round.number")

class Registration(db.Model):
    __tablename__ = "registrations"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    army_list = db.Column(db.Text, default="")
    paid = db.Column(db.Boolean, default=False)
    dropped = db.Column(db.Boolean, default=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    player = db.relationship("Player")
    __table_args__ = (db.UniqueConstraint("tournament_id", "player_id"),)

class Round(db.Model):
    __tablename__ = "rounds"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("tournaments.id"), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    state = db.Column(db.Enum(RoundState), default=RoundState.ACTIVE, nullable=False)
    matches = db.relationship("Match", backref="round", cascade="all, delete-orphan", order_by="Match.table_number")
    __table_args__ = (db.UniqueConstraint("tournament_id", "number"),)

class Match(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.id"), nullable=False)
    table_number = db.Column(db.Integer, nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=True)
    p1_tp = db.Column(db.Float)
    p1_kp = db.Column(db.Float)
    p2_tp = db.Column(db.Float)
    p2_kp = db.Column(db.Float)
    confirmed = db.Column(db.Boolean, default=False)
    player1 = db.relationship("Player", foreign_keys=[player1_id])
    player2 = db.relationship("Player", foreign_keys=[player2_id])
    @property
    def is_bye(self): return self.player2_id is None
    @property
    def has_result(self):
        if self.p1_tp is None: return False
        if not self.is_bye and self.p2_tp is None: return False
        return True
