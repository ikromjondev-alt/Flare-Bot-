import os
import functools

from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv

import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("WEBPANEL_SECRET_KEY", "change-me-please-в-.env")

PANEL_PASSWORD = os.getenv("WEBPANEL_PASSWORD", "")


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if PANEL_PASSWORD and password == PANEL_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Неверный пароль / Wrong password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    guild_ids = db.list_guild_ids()
    return render_template("dashboard.html", guild_ids=guild_ids)


@app.route("/guild/<int:guild_id>")
@login_required
def guild_detail(guild_id):
    settings = db.get_guild_settings(guild_id)
    autorole = db.get_autorole_config(guild_id)
    log_channel_id = db.get_log_channel(guild_id)
    warns = db.list_warns(guild_id)
    domains = db.list_allowed_domains(guild_id)
    return render_template(
        "guild.html",
        guild_id=guild_id,
        settings=settings,
        autorole=autorole,
        log_channel_id=log_channel_id,
        warns=warns,
        domains=domains,
    )


@app.route("/guild/<int:guild_id>/settings", methods=["POST"])
@login_required
def update_settings(guild_id):
    report_channel_id = request.form.get("report_channel_id") or None
    antispam_enabled = 1 if request.form.get("antispam_enabled") == "on" else 0
    language = request.form.get("language", "ru")
    warn_limit = request.form.get("warn_limit") or 0

    db.update_guild_settings(
        guild_id,
        report_channel_id=int(report_channel_id) if report_channel_id else None,
        antispam_enabled=antispam_enabled,
        language=language,
        warn_limit=int(warn_limit),
    )

    log_channel_id = request.form.get("log_channel_id") or None
    if log_channel_id:
        db.set_log_channel(guild_id, int(log_channel_id))

    flash("✅ Настройки сохранены / Settings saved")
    return redirect(url_for("guild_detail", guild_id=guild_id))


@app.route("/guild/<int:guild_id>/autorole", methods=["POST"])
@login_required
def update_autorole(guild_id):
    channel_id = request.form.get("channel_id") or None
    role_id = request.form.get("role_id") or None
    custom_message = request.form.get("custom_message") or None
    enabled = 1 if request.form.get("enabled") == "on" else 0

    db.update_autorole_config(
        guild_id,
        channel_id=int(channel_id) if channel_id else None,
        role_id=int(role_id) if role_id else None,
        custom_message=custom_message,
        enabled=enabled,
    )
    flash("✅ Настройки авто-роли сохранены / Autorole settings saved")
    return redirect(url_for("guild_detail", guild_id=guild_id))


@app.route("/guild/<int:guild_id>/warn/<int:warn_id>/delete", methods=["POST"])
@login_required
def delete_warn(guild_id, warn_id):
    db.delete_warn(warn_id)
    flash("✅ Предупреждение удалено / Warning deleted")
    return redirect(url_for("guild_detail", guild_id=guild_id))


@app.route("/guild/<int:guild_id>/domain/add", methods=["POST"])
@login_required
def add_domain(guild_id):
    domain = request.form.get("domain", "").strip()
    if domain:
        db.add_allowed_domain(guild_id, domain)
    return redirect(url_for("guild_detail", guild_id=guild_id))


@app.route("/guild/<int:guild_id>/domain/<path:domain>/delete", methods=["POST"])
@login_required
def remove_domain(guild_id, domain):
    db.remove_allowed_domain(guild_id, domain)
    return redirect(url_for("guild_detail", guild_id=guild_id))


if __name__ == "__main__":
    if not PANEL_PASSWORD:
        print("⚠️  ВНИМАНИЕ: WEBPANEL_PASSWORD не задан в .env — панель не защищена паролем!")
    app.run(host="0.0.0.0", port=int(os.getenv("WEBPANEL_PORT", "5000")), debug=False)
