#main.py
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from google import genai
from google.genai import types
from database import SessionLocal
from models import Message, Conversation, User
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
app.mount("/static", StaticFiles(directory="static"), name="static")

async def get_db():
    try:
        session = SessionLocal()
        yield session
    finally:
        await session.close()
        

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/chat")
async def create_chat_message(user_message: ChatMessage):
    response = client.models.generate_content(
        model="gemma-3-27b-it", contents=[user_message.message]
    )
    return {"response": response.text}

@app.post("/chat-with-image")
async def chat_with_image(
    caption: str = Form(...),
    image: UploadFile = File(...)
):
    user_file = await image.read()
    response = client.models.generate_content(
        model="gemma-3-27b-it",
        contents=[
            types.Part.from_bytes(
                data=user_file,
                mime_type=image.content_type,
            ),
            caption
        ]
    )
    
    return {"response": response.text}
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    try:
        # For simplicity, we'll assume a single conversation for now.
        # In a real app, you'd get this from the user's session or initial message.
        conversation_id = 1 

        while True:
            data = await websocket.receive_json()
            message_text = data.get("message", "").strip()

            if not message_text:
                await websocket.send_json({"type": "error", "message": "Empty message received."})
                continue
            
            # --- Save the user's message ---
            user_message = Message(
                role="user",
                content=message_text,
                conversation_id=conversation_id
            )
            db.add(user_message)
            await db.commit()
            
            # --- Stream response from Gemma ---
            stream = client.models.generate_content_stream(
                model="gemma-3-27b-it",
                contents=[message_text],
                # Using a different name for the config object
                generation_config=types.GenerateContentConfig(temperature=0.7)
            )

            # --- THE FIX: Accumulator Pattern ---
            # 1. Create a list to hold the response chunks
            full_response_text = []
            
            await websocket.send_json({"type": "start_of_stream"})

            for chunk in stream:
                if chunk.text:
                    # 2. Append each chunk to our list
                    full_response_text.append(chunk.text)
                    await websocket.send_json({"type": "stream", "token": chunk.text})
            
            await websocket.send_json({"type": "end_of_stream"})

            # 3. Join the list into a single string
            final_content = "".join(full_response_text)

            # 4. Save the complete assistant message
            assistant_message = Message(
                role="assistant",
                content=final_content,
                conversation_id=conversation_id
            )
            db.add(assistant_message)
            await db.commit()

    except WebSocketDisconnect:
        print("Client disconnected.")
        # No need to call websocket.close() inside WebSocketDisconnect
    except Exception as e:
        print(f"An error occurred: {e}")
        await websocket.send_json({"type": "error", "message": "An internal server error occurred."})
        # FastAPI handles closing the websocket on unhandled exceptions