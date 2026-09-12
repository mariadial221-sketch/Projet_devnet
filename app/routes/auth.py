from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

# Importations relatives à Projet_devnet
from app.databases import get_db
from app.models import Utilisateur
from app.schemas import UserCreate, Token

SECRET_KEY = "votre_cle_secrete_super_securisee"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Routeurs
router = APIRouter(tags=["Authentification"])
router_users = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- FONCTIONS SÉCURITÉ & AUTHENTIFICATION ---

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(Utilisateur).filter(Utilisateur.username == username).first()
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    return payload

def require_role(required_role: str):
    def role_dependency(payload: dict = Depends(get_current_user), db: Session = Depends(get_db)):
        username = payload.get("sub")
        user = db.query(Utilisateur).filter(Utilisateur.username == username).first()
        if not user or user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : privilèges insuffisants",
            )
        return user
    return role_dependency

# --- ROUTES AUTHENTIFICATION ---

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
        )
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# --- ROUTES UTILISATEURS (RBAC) ---

# Accessible UNIQUEMENT par un administrateur
@router_users.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_role("admin"))
):
    db_user = db.query(Utilisateur).filter(Utilisateur.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur déjà pris")
    
    hashed_pwd = pwd_context.hash(user.password)
    new_user = Utilisateur(
        username=user.username,
        hashed_password=hashed_pwd,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "role": new_user.role,
        "message": "Utilisateur créé avec succès"
    }