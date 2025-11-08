import logging
import os
import uuid
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, current_app, g, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

from admin_routes import admin_bp
from auth_routes import auth_bp
from book_routes import book_bp
from loan_routes import loan_bp
from reservation_routes import reservation_bp
from response_utils import error_response
from user_routes import user_bp

jwt = JWTManager()


def create_app() -> Flask:
    """
    Application factory: initializes Flask, JWT, CORS, error handlers, and blueprints.
    """
    load_dotenv()

    app = Flask(__name__)

    # Secrets / JWT configuration (override via environment variables)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt-secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        hours=int(os.getenv("JWT_EXPIRES_HOURS", "2"))
    )
    # Configure refresh tokens (optional expiration, default 30 days here)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(
        days=int(os.getenv("JWT_REFRESH_EXPIRES_DAYS", "30"))
    )

    # CORS allowlist (comma-separated origins). Prefer explicit origins over "*".
    cors_default = "http://localhost:4200,http://localhost:3000"
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", cors_default).split(",")]
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins, "supports_credentials": False}},
    )

    # Initialize JWT
    jwt.init_app(app)

    # In-memory JWT blocklist for revoked JTIs (for logout)
    # For multi-process/container deployments use a shared store (e.g., Redis).
    app.config.setdefault("JWT_BLOCKLIST", set())

    @jwt.token_in_blocklist_loader
    def _is_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        blocklist = current_app.config.get("JWT_BLOCKLIST")
        return jti in blocklist if jti and isinstance(blocklist, set) else False

    # Request ID middleware (helps correlate logs with responses)
    @app.before_request
    def _attach_request_id():
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_id = rid

    @app.after_request
    def _inject_response_headers(resp):
        if getattr(g, "request_id", None):
            resp.headers["X-Request-ID"] = g.request_id
        return resp

    # Health check
    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # Optional: serve OpenAPI spec if present in project root
    @app.get("/api/openapi.yaml")
    def openapi_yaml():
        try:
            return send_from_directory(directory=".", path="openapi.yaml", mimetype="text/yaml")
        except Exception:
            return error_response("not_found", "OpenAPI spec not found.", status=404)

    # JWT error handlers (unified JSON errors)
    @jwt.invalid_token_loader
    def _invalid_token(reason: str):
        return error_response("unauthorized", "Missing or invalid token.", status=401)

    @jwt.unauthorized_loader
    def _missing_token(reason: str):
        return error_response("unauthorized", "Missing or invalid token.", status=401)

    @jwt.expired_token_loader
    def _expired_token(jwt_header, jwt_payload):
        return error_response("token_expired", "Token expired.", status=401)

    @jwt.needs_fresh_token_loader
    def _needs_fresh(jwt_header, jwt_payload):
        return error_response("fresh_token_required", "Fresh token required.", status=401)

    @jwt.revoked_token_loader
    def _revoked(jwt_header, jwt_payload):
        return error_response("token_revoked", "Token has been revoked.", status=401)

    # 429 (rate limiting) handler
    @app.errorhandler(429)
    def handle_429(e):
        return error_response("too_many_requests", "Too many requests.", status=429)

    # 404 handler
    @app.errorhandler(404)
    def not_found(e):
        return error_response("not_found", "Endpoint not found.", status=404)

    # Catch-all exception handler, behavior depends on debug mode
    @app.errorhandler(Exception)
    def handle_exception(e):
        debug_mode = current_app.debug

        if isinstance(e, HTTPException):
            message = e.description if debug_mode else "Unexpected HTTP error."
            return error_response("http_error", message, status=e.code or 500)

        current_app.logger.exception("Unhandled exception")
        message = str(e) if debug_mode else "Unexpected server error."
        return error_response("server_error", message, status=500)

    # Register blueprints under /api
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(book_bp, url_prefix="/api")
    app.register_blueprint(loan_bp, url_prefix="/api")
    app.register_blueprint(reservation_bp, url_prefix="/api")
    app.register_blueprint(user_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app = create_app()
    app.run(debug=debug)
