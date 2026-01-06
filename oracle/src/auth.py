"""
Authentication and Authorization
JWT-based authentication system with role-based access control
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from database import get_db
from models import TokenData, User

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=scopes)
        return token_data
        
    except JWTError:
        raise credentials_exception

async def get_user(username: str) -> Optional[User]:
    """Get user from database"""
    try:
        from sqlalchemy import text
        async with get_db() as db:
            result = await db.execute(
                text("SELECT * FROM users WHERE username = :username AND is_active = true"),
                {"username": username}
            )
            user_data = result.fetchone()
            
            if user_data:
                return User(
                    username=user_data.username,
                    email=user_data.email,
                    full_name=user_data.full_name,
                    is_active=user_data.is_active,
                    roles=user_data.roles or []
                )
            return None
            
    except Exception as e:
        logger.error(f"Failed to get user {username}: {e}")
        return None

async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user credentials"""
    try:
        from sqlalchemy import text
        async with get_db() as db:
            result = await db.execute(
                text("SELECT * FROM users WHERE username = :username AND is_active = true"),
                {"username": username}
            )
            user_data = result.fetchone()
            
            if user_data and verify_password(password, user_data.hashed_password):
                # Update last login
                await db.execute(
                    text("UPDATE users SET last_login = :last_login WHERE username = :username"),
                    {"last_login": datetime.now(timezone.utc), "username": username}
                )
                await db.commit()
                
                return User(
                    username=user_data.username,
                    email=user_data.email,
                    full_name=user_data.full_name,
                    is_active=user_data.is_active,
                    roles=user_data.roles or []
                )
            return None
            
    except Exception as e:
        logger.error(f"Authentication failed for {username}: {e}")
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token"""
    try:
        token_data = verify_token(credentials.credentials)
        user = await get_user(username=token_data.username)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
        
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def check_permissions(required_roles: list[str]):
    """Dependency to check if user has required roles"""
    def permission_checker(current_user: User = Depends(get_current_active_user)):
        if not any(role in current_user.roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return permission_checker

async def create_user(
    username: str,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    roles: Optional[list[str]] = None
) -> User:
    """Create a new user"""
    try:
        hashed_password = get_password_hash(password)
        user_roles = roles or ["user"]
        
        async with get_db() as db:
            # Check if user already exists
            existing = await db.execute(
                "SELECT username FROM users WHERE username = %s OR email = %s",
                (username, email)
            )
            if existing.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already exists"
                )
            
            # Insert new user
            await db.execute(
                """
                INSERT INTO users (username, email, hashed_password, full_name, roles, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (username, email, hashed_password, full_name, user_roles, True)
            )
            await db.commit()
            
            return User(
                username=username,
                email=email,
                full_name=full_name,
                is_active=True,
                roles=user_roles
            )
            
    except Exception as e:
        logger.error(f"Failed to create user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

async def create_default_admin():
    """Create default admin user if none exists"""
    try:
        async with get_db() as db:
            # Check if any admin user exists
            result = await db.execute(
                "SELECT COUNT(*) FROM users WHERE roles @> %s",
                ('["admin"]',)
            )
            admin_count = result.scalar()
            
            if admin_count == 0:
                # Create default admin
                admin_password = os.getenv("ADMIN_PASSWORD", secrets.token_urlsafe(16))
                
                await create_user(
                    username="admin",
                    email="admin@cardea.local",
                    password=admin_password,
                    full_name="System Administrator",
                    roles=["admin", "user"]
                )
                
                # Log creation without exposing the password
                if os.getenv("ADMIN_PASSWORD"):
                    logger.info("Created default admin user with password from ADMIN_PASSWORD env var")
                else:
                    logger.warning("Created default admin user with auto-generated password. Set ADMIN_PASSWORD env var to specify.")
                logger.warning("Please change the admin password immediately!")
                
    except Exception as e:
        logger.error(f"Failed to create default admin: {e}")

# Webhook authentication for Sentry services
async def verify_sentry_webhook(token: str) -> bool:
    """Verify webhook token from Sentry services"""
    return token == settings.SENTRY_WEBHOOK_TOKEN

def webhook_auth_required():
    """Dependency for webhook authentication"""
    def webhook_checker(credentials: HTTPAuthorizationCredentials = Depends(security)):
        if not verify_sentry_webhook(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return True
    return webhook_checker