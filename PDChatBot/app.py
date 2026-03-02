"""
Aplicación web basada en Flask que utiliza el modelo 'gemini-2.5-flash' de Google Gemini para generar respuestas
a partir de entradas del usuario. La aplicación almacena el historial de conversaciones y utiliza Markdown
para formatear las respuestas generadas.
"""

import os
import tempfile

import google.generativeai as genai
import markdown
import requests
from dotenv import load_dotenv

from flask import Flask, request, render_template, session, redirect, url_for, jsonify
from flask_session import Session

# ==============================
# CARGAR VARIABLES DE ENTORNO
# ==============================
load_dotenv()

# ==============================
# CONFIGURACIÓN DE FLASK
# ==============================
app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": ["https://brainbook1.netlify.app"]}})

app.secret_key = "clave_secreta_para_sesiones"
app.config["SESSION_TYPE"] = "filesystem"

# Directorio temporal para la sesión (evita problemas en OneDrive)
app.config["SESSION_FILE_DIR"] = tempfile.gettempdir()

Session(app)

# ==============================
# CONFIGURAR GEMINI
# ==============================
try:
    genai.configure(api_key=os.environ["API_KEY"])
except KeyError:
    print("ADVERTENCIA: Falta API_KEY en el archivo .env")

model = genai.GenerativeModel("gemini-2.5-flash")

MAX_HISTORY = 10  # límite del historial

# ==============================
# RUTA PRINCIPAL (GET)
# ==============================
@app.route("/")
def home():
    # Obtener el último mensaje si existe
    last_prompt = session.pop("last_prompt", None)
    last_response = session.pop("last_response", None)
    error = session.pop("error", None)
    
    # Obtener historial completo
    history = session.get("history", [])
    
    return render_template("apartado_inteligente.html",
                           last_prompt=last_prompt,
                           last_response=last_response,
                           history=history,
                           error=error)

# ==============================
# RUTA DE PREDICCIÓN (POST)
# ==============================
@app.route("/predict", methods=["POST"])
def predict():
    prompt = request.form.get("prompt")

    if not prompt:
        session["error"] = "Por favor, ingresa un texto válido."
        return jsonify({"error": "Texto inválido"}), 400

    try:
        # Generar respuesta de Gemini
        response = model.generate_content(prompt).text
        output_html = markdown.markdown(response)

        # Guardar en historial
        history = session.get("history", [])
        history.append({
            "role": "user",
            "content": prompt
        })
        history.append({
            "role": "assistant",
            "content": output_html
        })

        # Limitar historial
        if len(history) > MAX_HISTORY * 2:
            history = history[-MAX_HISTORY * 2:]
        
        session["history"] = history
        session.modified = True

        return jsonify({"success": True, "response": output_html})

    except requests.exceptions.RequestException as e:
        error_msg = f"Error al conectarse a Gemini: {e}"
        session["error"] = error_msg
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        error_msg = f"Error inesperado: {e}"
        session["error"] = error_msg
        return jsonify({"error": error_msg}), 500

# ==============================
# RUTA PARA OBTENER HISTORIAL (API)
# ==============================
@app.route("/api/history", methods=["GET"])
def get_history():
    history = session.get("history", [])
    return jsonify(history)

# ==============================
# RUTA PARA LIMPIAR CHAT
# ==============================
@app.route("/api/new-chat", methods=["POST"])
def new_chat():
    session["history"] = []
    session.pop("last_prompt", None)
    session.pop("last_response", None)
    return jsonify({"success": True})

# ==============================
# EJECUCIÓN
# ==============================
if __name__ == "__main__":

     app.run()
