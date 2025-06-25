#main.py
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types
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

@app.get("/")
async def root():
    return HTMLResponse(content=open("static/index.html").read(), status_code=200)

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
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()

            if not message:
                await websocket.send_json({"type": "error", "message": "Empty message received."})
                continue

            # Assuming the correct method is generate_content with stream=True
            stream = client.models.generate_content_stream(
                model="gemma-3-27b-it",
                contents=[message],
                config = types.GenerateContentConfig(temperature=1.5)
            )

            # Send a marker to the frontend that a new response is starting
            await websocket.send_json({"type": "start_of_stream"})

            for chunk in stream:
                # Make sure the chunk has text to avoid sending empty messages
                if chunk.text:
                    await websocket.send_json({"type": "stream", "token": chunk.text})
            
            # Send a marker that the stream is finished
            await websocket.send_json({"type": "end_of_stream"})

    except WebSocketDisconnect:
        print("Client disconnected.") # Good for debugging
        await websocket.close()
    except Exception as e:
        print(f"An error occurred: {e}")
        # Inform the client of the error
        await websocket.send_json({"type": "error", "message": "An internal server error occurred."})
        await websocket.close()