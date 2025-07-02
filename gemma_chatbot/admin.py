from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from database import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User 
from security import verify_password, create_access_token
from starlette.responses import Response

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        request_data = await request.form()
        username = request_data.get("username")
        password = request_data.get("password")
        # --- Get db session manually ---
        async with SessionLocal() as db:
            query = select(User).where(User.username == username)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            if user and user.is_admin:
                verified = verify_password(password, user.hashed_password)
                if verified:
                    token = create_access_token(data={"sub": user.username}) # subject is the username
                    # Store the token in the session
                    request.session.update({
                        "token": token,
                    })
                    return True
        return False
    
    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Response | bool:
        return "token" in request.session
    