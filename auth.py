from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User, Franchise, Admin, UserRole
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def verify_password(plain_password, stored_password):
    # Plain text password comparison
    return plain_password == stored_password

def get_password_hash(password):
    # Return password as-is (no hashing)
    return password

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(db: Session, identifier: str, password: str, role: UserRole):
    # Authenticate based on role
    if role == UserRole.ADMIN:
        user = db.query(Admin).filter(Admin.email == identifier).first()
    elif role == UserRole.FRANCHISE:
        user = db.query(Franchise).filter(Franchise.email == identifier).first()
    else:  # USER
        # Can login with email or MLD ID
        user = db.query(User).filter(
            (User.email == identifier) | (User.mld_id == identifier)
        ).first()
    
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        identifier: str = payload.get("sub")
        role: str = payload.get("role")
        if identifier is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Get user based on role
    if role == "admin":
        user = db.query(Admin).filter(Admin.email == identifier).first()
    elif role == "franchise":
        user = db.query(Franchise).filter(Franchise.email == identifier).first()
    else:
        user = db.query(User).filter(
            (User.email == identifier) | (User.mld_id == identifier)
        ).first()
    
    if user is None:
        raise credentials_exception
    return user

def require_role(required_role: UserRole):
    def role_checker(current_user = Depends(get_current_user)):
        if hasattr(current_user, 'role'):
            user_role = current_user.role
        elif isinstance(current_user, Admin):
            user_role = UserRole.ADMIN
        elif isinstance(current_user, Franchise):
            user_role = UserRole.FRANCHISE
        else:
            user_role = UserRole.USER
        
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker

def require_any_role(allowed_roles: list):
    """Allow access if user has any of the specified roles"""
    def role_checker(current_user = Depends(get_current_user)):
        if hasattr(current_user, 'role'):
            user_role = current_user.role
        elif isinstance(current_user, Admin):
            user_role = UserRole.ADMIN
        elif isinstance(current_user, Franchise):
            user_role = UserRole.FRANCHISE
        else:
            user_role = UserRole.USER
        
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker
