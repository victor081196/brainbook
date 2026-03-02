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

from flask import Flask, request, render_template, session, jsonify
from flask_session import Session
from flask_cors import CORS  # ✅ FALTABA ESTE IMPORT

# ==============================
# CARGAR VARIABLES DE ENTORNO
# ==============================
load_dotenv()

# ==============================
# CONFIGURACIÓN DE FLASK
# ==============================
app = Flask(__name__)

# ✅ CORS para que el front en Netlify pueda hablar con Render
# Si luego quieres permitir más dominios, agrega aquí.
CORS(app, resources={r"/*": {"origins": ["https://brainbook1.netlify.app"]}})

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave_secreta_para_sesiones")

# Sesiones en filesystem (Render sí lo soporta, pero puede resetearse en redeploy)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = tempfile.gettempdir()
app.config["SESSION_PERMANENT"] = False

Session(app)

# ==============================
# CONFIGURAR GEMINI
# ==============================
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    print("ADVERTENCIA: Falta API_KEY en variables de entorno (Render) o .env")
else:
    genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")
MAX_HISTORY = 10  # límite del historial (pares user+assistant)

# ==============================
# HEALTH CHECK (para probar en Render)
# ==============================
@app.get("/health")
def health():
    return jsonify({"ok": True})

# ==============================
# RUTA PRINCIPAL (GET)
# ==============================
@app.get("/")
def home():
    # Si el template no existe en producción, esto fallará (500).
    # Asegúrate de tener: PDChatBot/templates/apartado_inteligente.html
    history = session.get("history", [])
    return render_template("apartado_inteligente.html", history=history)

# ==============================
# RUTA DE PREDICCIÓN (POST)
# ==============================
@app.post("/predict")
def predict():
    prompt = (request.form.get("prompt") or "").strip()

    if not prompt:
        return jsonify({"error": "Por favor, ingresa un texto válido."}), 400

    try:
        # Generar respuesta de Gemini
        response_text = model.generate_content(prompt).text
        output_html = markdown.markdown(response_text)

        # Guardar en historial
        history = session.get("history", [])
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": output_html})

        # Limitar historial
        if len(history) > MAX_HISTORY * 2:
            history = history[-MAX_HISTORY * 2 :]

        session["history"] = history
        session.modified = True

        # Tu front puede usar esto directamente, sin ir a /api/history si quieres
        return jsonify({"success": True, "response": output_html})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error al conectarse a Gemini: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error inesperado: {e}"}), 500

# ==============================
# RUTA PARA OBTENER HISTORIAL (API)
# ==============================
@app.get("/api/history")
def get_history():
    history = session.get("history", [])
    return jsonify(history)

# ==============================
# RUTA PARA LIMPIAR CHAT
# ==============================
@app.post("/api/new-chat")
def new_chat():
    session["history"] = []
    session.modified = True
    return jsonify({"success": True})

# ==============================
# EJECUCIÓN LOCAL
# ==============================
if __name__ == "__main__":
    # En Render NO se usa esto; Render usa gunicorn.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
