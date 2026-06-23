from dotenv import load_dotenv
import os

load_dotenv()

# Groq config
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME   = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")