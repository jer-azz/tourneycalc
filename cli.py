import click
from extensions import db
from models import Player

def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        db.create_all(); click.echo("DB initialised.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, email, password):
        if Player.query.filter_by(username=username).first():
            click.echo("Username taken."); return
        p = Player(username=username, email=email.lower(), display_name=username, is_admin=True)
        p.set_password(password); db.session.add(p); db.session.commit()
        click.echo(f"Admin {username} created.")
