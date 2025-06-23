#main.py
from fastapi import FastAPI
from pydantic import BaseModel
from google import genai
import dotenv
import os

# Set the environment variable for the Gemma API key
dotenv.load_dotenv(dotenv_path=".env")
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")

# Initialize the Google GenAI client
client = genai.Client(api_key=GEMMA_API_KEY)

class ChatMessage(BaseModel):
    message: str

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/chat")
async def create_chat_message(user_message: ChatMessage):
    response = client.models.generate_content(
        model="gemma-3-27b-it", contents=[user_message.message]
    )
    return {"response": response.text}