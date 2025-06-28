import os
import datetime
from passlib import context
from jose import JWTError, jwt
from models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import dotenv

dotenv.load_dotenv(dotenv_path=".env")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = context.CryptContext(
    schemes=["bcrypt"],
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: datetime.timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db: AsyncSession, username: str) -> User | None:
    """Retrieve a user by ID from the database."""
    query = select(User).where(User.username == username)
    result = db.execute(query)
    return result.scalar_one_or_none()