from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from limits import RateLimitItemPerMinute

from database import SessionLocal
from models import User
from security import verify_password, create_access_token
from main import limiter
from slowapi.util import get_remote_address


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        # Get the client's IP address to use as a key for rate limiting.
        ip = get_remote_address(request)
        # Define the specific rate limit rule we want to check against.
        five_per_minute = RateLimitItemPerMinute(5)

        # Manually hit the rate limiter.
        # The .hit() method returns True if the request is within the limit,
        # and False if it has been exceeded.
        is_allowed = limiter._limiter.hit(five_per_minute, ip, "admin_login")

        if not is_allowed:
            print(f"Admin login rate limit exceeded for IP: {ip}")
            return False

        # If the rate limit check passes, proceed with authentication.
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")

            async with SessionLocal() as db:
                query = select(User).where(User.username == username)
                result = await db.execute(query)
                user = result.scalar_one_or_none()

                if user and user.is_admin and verify_password(password, user.hashed_password):
                    token = create_access_token(data={"sub": user.username})
                    request.session.update({"token": token})
                    return True
        except Exception:
            # Catch any other potential errors during form processing
            return False

        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return "token" in request.session
