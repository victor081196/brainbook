import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()  # carga API_KEY desde .env

API_KEY = os.environ["API_KEY"]

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

pregunta = "cuanto es 1+1"
respuesta = model.generate_content(pregunta)
print(respuesta.text)