# main.py
import datetime
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# Local imports (make sure these files exist and are correct)
from database import SessionLocal, get_db  # Assuming get_db is in database.py
from models import Message, Conversation

# Initialize the Google GenAI client (assuming this part is correct)
from google import genai
from google.genai import types
import dotenv
import os

dotenv.load_dotenv(dotenv_path=".env")
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
client = genai.Client(api_key=GEMMA_API_KEY)


# --- Pydantic Schemas ---

class ConversationBase(BaseModel):
    title: str

class ConversationCreate(ConversationBase):
    pass

class ConversationSchema(ConversationBase):
    id: int
    user_id: int
    # THE FIX IS HERE: Use datetime.datetime for the type hint
    created_at: datetime.datetime

    class Config:
        orm_mode = True


# --- FastAPI App Initialization ---

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- HTTP Endpoints ---

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/conversations", response_model=list[ConversationSchema])
async def get_conversations(db: AsyncSession = Depends(get_db)):
    query = select(Conversation).where(Conversation.user_id == 1).order_by(Conversation.created_at.desc())
    result = await db.execute(query)
    conversations = result.scalars().all()
    return conversations

@app.post("/conversations", response_model=ConversationSchema)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    new_conversation = Conversation(
        title=conversation_data.title,
        user_id=1,
        created_at=datetime.datetime.now(datetime.timezone.utc) # Set TZ-aware timestamp
    )
    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)
    return new_conversation


# --- WebSocket Endpoint ---

# In main.py

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    await websocket.accept()

    # --- THE FIX: PART 1 ---
    # Load history from DB and immediately convert it to a plain list of dicts.
    # This is now our "source of truth" for the rest of the connection.
    history_query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(history_query)
    # This list contains simple dicts, NOT live SQLAlchemy objects.
    chat_history_list = [
        {"role": msg.role, "content": msg.content} for msg in result.scalars().all()
    ]
    
    # Send the clean history to the client.
    await websocket.send_json({"type": "history", "messages": chat_history_list})

    try:
        while True:
            data = await websocket.receive_json()
            message_text = data.get("message", "").strip()

            if not message_text:
                continue

            # Save user message to the database (this part is fine).
            user_message = Message(
                role="user",
                content=message_text,
                conversation_id=conversation_id,
                created_at=datetime.datetime.now(datetime.timezone.utc)
            )
            db.add(user_message)
            await db.commit()
            
            # --- THE FIX: PART 2 ---
            # Update our IN-MEMORY plain list with the new user message.
            chat_history_list.append({"role": "user", "content": message_text})

            # Prepare the history for the model from our clean list.
            model_contents = [turn["content"] for turn in chat_history_list]

            # Stream response from Gemma.
            stream = client.models.generate_content_stream(
                model="gemma-3-27b-it",
                contents=model_contents,
                config=types.GenerateContentConfig(temperature=0.7)
            )

            # Accumulate the response (this part is fine).
            full_response_text = []
            await websocket.send_json({"type": "start_of_stream"})
            for chunk in stream:
                if chunk.text:
                    full_response_text.append(chunk.text)
                    await websocket.send_json({"type": "stream", "token": chunk.text})
            await websocket.send_json({"type": "end_of_stream"})

            final_content = "".join(full_response_text)

            # Save the complete assistant message to the database (this part is fine).
            assistant_message = Message(
                role="assistant",
                content=final_content,
                conversation_id=conversation_id,
                created_at=datetime.datetime.now(datetime.timezone.utc)
            )
            db.add(assistant_message)
            await db.commit()

            # --- THE FIX: PART 3 ---
            # Update our IN-MEMORY plain list with the new assistant message.
            chat_history_list.append({"role": "assistant", "content": final_content})

    except WebSocketDisconnect:
        print(f"Client disconnected from conversation {conversation_id}.")
    except Exception as e:
        print(f"An error occurred in conversation {conversation_id}: {e}")
        await websocket.send_json({"type": "error", "message": "An internal server error occurred."})