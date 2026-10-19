from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

from app.core.database import get_db
from app.models.user import User

router = APIRouter()

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Pydantic schema for incoming registration data
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    matric_number: str | None = None
    pathway: str | None = "Computer Engineering"
    level: str | None = "HND I"

# Schema for incoming login data
class UserLogin(BaseModel):
    email: str
    password: str

# --- LOGIN ROUTE ---
@router.post("/login")
async def login_user(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    # Force email to lowercase for case-insensitive matching
    user_in.email = user_in.email.lower()

    # 1. Fetch the user by email
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    user = result.scalars().first()

    # --- DIAGNOSTIC LOGS ---
    print(f"DEBUG: Looking for email -> {user_in.email}")
    if not user:
        print("DEBUG: Failed! Email not found in the database.")
    elif not pwd_context.verify(user_in.password, user.hashed_password):
        print("DEBUG: Failed! Email found, but password did not match.")
    else:
        print("DEBUG: Success! Email and password match.")
    # -----------------------

    # 2. Verify user exists and password matches
    if not user or not pwd_context.verify(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Check your credentials."
        )

    # 3. Generate JWT Token
    from app.core.security import create_access_token 
    access_token = create_access_token(subject=str(user.id))
    
    # 4. Return exactly what your React app is destructuring
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# --- REGISTER ROUTE ---
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Force email to lowercase before inserting into the database
    user_in.email = user_in.email.lower()

    # 1. Check if the user already exists
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists in the system."
        )

    # 2. Hash the password
    hashed_password = get_password_hash(user_in.password)

    # 3. Save the new user to the database
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        matric_number=user_in.matric_number,
        pathway=user_in.pathway,
        level=user_in.level,
        role="student",       # Default role
        account_type="free",  # Default account type
        tokens_remaining=50,  # Default starter tokens
        pdf_quota_remaining=5 # Default starter PDF quota
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "message": "Account created successfully",
        "user_id": new_user.id,
        "email": new_user.email
    }