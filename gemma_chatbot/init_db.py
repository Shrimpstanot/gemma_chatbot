import asyncio
from database import engine, Base
from models import User, Conversation, Message

async def init_db():
    """Initialize the database and create tables."""
    async with engine.begin() as conn:
        # Create all tables in the database
        await conn.run_sync(Base.metadata.drop_all) # Drop all tables if they exist
        await conn.run_sync(Base.metadata.create_all) # Create all tables
    await engine.dispose()  # Dispose the engine after operations
    print("Database initialized and tables created.")
    
if __name__ == "__main__":
    # Run the init_db function to initialize the database
    asyncio.run(init_db())
    # This will create the database and tables defined in the models
    # Make sure to run this script before starting the FastAPI application
    print("Database initialization complete. ")