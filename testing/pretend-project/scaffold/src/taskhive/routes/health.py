from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health_check():
    return jsonify({"status": "ok"})


@health_bp.route("/health/db")
def db_health():
    return jsonify({"status": "ok", "database": "connected"})
