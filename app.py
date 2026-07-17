"""
Any2Mp3 — Punto de entrada de la aplicación.
Responsabilidad: Crear e inicializar la app Flask y registrar blueprints.
"""

import os

from flask import Flask, render_template, jsonify

import config
from routes.api import api


def create_app() -> Flask:
    resources = os.environ.get("RESOURCEPATH")
    app = Flask(
        __name__,
        template_folder=os.path.join(resources, "templates") if resources else "templates",
        static_folder=os.path.join(resources, "static") if resources else "static",
    )
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

    # Registrar blueprint de la API
    app.register_blueprint(api)

    # --- Manejo de errores HTTP como JSON ---
    @app.errorhandler(413)
    def too_large(e):
        max_mb = config.MAX_CONTENT_LENGTH // (1024 * 1024)
        return jsonify({"error": f"El archivo es demasiado grande. Máximo permitido: {max_mb} MB."}), 413

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Recurso no encontrado."}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Error interno del servidor."}), 500

    # Ruta principal — sirve el frontend
    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    print("\n🎵  Any2Mp3 corriendo en http://localhost:5050\n")
    app.run(debug=True, host="0.0.0.0", port=5050)
