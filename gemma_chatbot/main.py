import datetime
import os
import shutil
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from jose import jwt, JWTError

# Local application imports
from database import get_db
from models import Message, Conversation, User
from security import get_current_user, SECRET_KEY, ALGORITHM, verify_password, create_access_token, get_user, pwd_context
from rag import process_file_and_update_vector_store, query_vector_store

# Google GenAI client initialization
from google import genai
from google.genai import types
import dotenv

dotenv.load_dotenv(dotenv_path=".env")
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
client = genai.Client(api_key=GEMMA_API_KEY)

# Pydantic Schemas for data validation and serialization
class ConversationBase(BaseModel):
    title: str

class ConversationCreate(ConversationBase):
    pass

class ConversationSchema(BaseModel):
    id: int
    user_id: int
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserSchema(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime.datetime

    class Config:
        orm_mode = True

# FastAPI application initialization
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Helper function for WebSocket authentication
async def get_current_user_from_token(token: str, db: AsyncSession) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    user = await get_user(db, username)
    return user

# HTTP Endpoints
@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/login")
async def login():
    return FileResponse("static/login.html")

@app.get("/register")
async def register():
    return FileResponse("static/register.html")

@app.post("/users/", response_model=UserSchema)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Hash the user's password before storing it
    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Authenticate user credentials
    user = await get_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    # Create and return an access token upon successful authentication
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/conversations", response_model=list[ConversationSchema])
async def get_conversations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Retrieve conversations belonging to the authenticated user
    query = select(Conversation).where(Conversation.user_id == current_user.id).order_by(Conversation.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()

@app.post("/conversations", response_model=ConversationSchema)
async def create_conversation(conversation_data: ConversationCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Create a new conversation associated with the authenticated user
    new_conversation = Conversation(
        title=conversation_data.title,
        user_id=current_user.id,
        created_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)
    return new_conversation

@app.post("/conversations/{conversation_id}/files")
async def upload_files_to_conversation(
    conversation_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify the user owns the conversation before allowing file upload
    query = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
    result = await db.execute(query)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")

    # Create a dedicated directory for uploaded files within the conversation
    upload_dir = f"uploads/{conversation_id}"
    os.makedirs(upload_dir, exist_ok=True)

    for file in files:
        file_path = os.path.join(upload_dir, file.filename)
        
        # Save the uploaded file locally to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the file for RAG in a separate thread to avoid blocking the main event loop
        await run_in_threadpool(process_file_and_update_vector_store, file_path=file_path, conversation_id=conversation_id)
        
        # Record the file upload as a message in the database
        db.add(Message(
            role="user",
            content=f"File uploaded: {file.filename}",
            conversation_id=conversation_id,
            file_path=file_path,
            created_at=datetime.datetime.now(datetime.timezone.utc)
        ))

    await db.commit()
    return {"detail": f"{len(files)} files uploaded successfully and are being processed."}

# WebSocket Endpoint for real-time chat
@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    await websocket.accept()

    # Authenticate the WebSocket connection using a JWT token sent by the client
    try:
        auth_data = await websocket.receive_json()
        if auth_data.get("type") != "auth" or not auth_data.get("token"):
            await websocket.close(code=1008, reason="Authentication failed")
            return

        token = auth_data["token"]
        user = await get_current_user_from_token(token, db)

        if not user:
            await websocket.close(code=1008, reason="Invalid user")
            return
        
        # Verify the authenticated user has access to the requested conversation
        convo_query = select(Conversation).where(
            Conversation.id == conversation_id, 
            Conversation.user_id == user.id
        )
        result = await db.execute(convo_query)
        conversation = result.scalar_one_or_none()
        if not conversation:
            await websocket.close(code=1003, reason="Conversation not found or access denied")
            return

    except Exception as e:
        print(f"Auth Error: {e}")
        await websocket.close(code=1011, reason="An error occurred during authentication.")
        return

    print(f"User {user.username} connected to conversation {conversation_id}")

    # Load existing chat history for the conversation from the database
    history_query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(history_query)
    chat_history_list = [
        {"role": msg.role, "content": msg.content} for msg in result.scalars().all()
    ]
    
    # Send the loaded history to the client
    await websocket.send_json({"type": "history", "messages": chat_history_list})

    try:
        while True:
            # Receive incoming messages from the WebSocket client
            data = await websocket.receive_json()
            message_text = data.get("message", "").strip()

            if not message_text:
                continue
            
            # Save the user's message to the database
            user_message = Message(
                role="user",
                content=message_text,
                conversation_id=conversation_id,
                created_at=datetime.datetime.now(datetime.timezone.utc)
            )
            db.add(user_message)
            await db.commit()
            
            # Update the in-memory chat history list with the new user message
            chat_history_list.append({"role": "user", "content": message_text})

            # RAG Integration: Query the vector store for relevant documents based on the user's message
            relevant_docs = await query_vector_store(message_text, conversation_id)
            
            # Construct the augmented prompt for the LLM, including retrieved context if available
            if relevant_docs:
                context = "\n".join([doc.page_content for doc in relevant_docs])
                augmented_prompt = (
                    f"Based on the following context, please answer the user's question.\n\n"
                    f"Context:\n---\n{context}\n---\n\n"
                    f"User's Question: {message_text}"
                )
                # Combine recent chat history with the augmented prompt for the LLM
                final_model_contents = [turn["content"] for turn in chat_history_list[-4:]] + [augmented_prompt]
            else:
                # If no relevant documents, send only the recent chat history to the LLM
                final_model_contents = [turn["content"] for turn in chat_history_list]

            # Stream the response from the Gemma model
            stream = client.models.generate_content_stream(
                model="gemma-3-27b-it",
                contents=final_model_contents,
                config=types.GenerateContentConfig(temperature=0.7)
            )

            # Accumulate the streamed response and send tokens to the client
            full_response_text = []
            await websocket.send_json({"type": "start_of_stream"})
            for chunk in stream:
                if chunk.text:
                    full_response_text.append(chunk.text)
                    await websocket.send_json({"type": "stream", "token": chunk.text})
            await websocket.send_json({"type": "end_of_stream"})

            final_content = "".join(full_response_text)

            # Save the complete assistant message to the database
            assistant_message = Message(
                role="assistant",
                content=final_content,
                conversation_id=conversation_id,
                created_at=datetime.datetime.now(datetime.timezone.utc)
            )
            db.add(assistant_message)
            await db.commit()

            # Update the in-memory chat history list with the new assistant message
            chat_history_list.append({"role": "assistant", "content": final_content})

    except WebSocketDisconnect:
        print(f"Client disconnected from conversation {conversation_id}.")
    except Exception as e:
        print(f"An error occurred in conversation {conversation_id}: {e}")
        await websocket.send_json({"type": "error", "message": "An internal server error occurred."})
