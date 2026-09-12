from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.databases import get_db
from app.models import Equipement
from app.schemas import EquipementCreate, EquipementResponse

router = APIRouter(prefix="/equipements", tags=["Equipements"])

@router.get("/", response_model=List[EquipementResponse])
def get_equipements(db: Session = Depends(get_db)):
    return db.query(Equipement).all()

@router.post("/", response_model=EquipementResponse)
def create_equipement(equipement: EquipementCreate, db: Session = Depends(get_db)):
    db_equipement = Equipement(**equipement.model_dump())
    db.add(db_equipement)
    db.commit()
    db.refresh(db_equipement)
    return db_equipement

@router.get("/{equipement_id}", response_model=EquipementResponse)
def get_equipement(equipement_id: int, db: Session = Depends(get_db)):
    db_eq = db.query(Equipement).filter(Equipement.id == equipement_id).first()
    if not db_eq:
        raise HTTPException(status_code=404, detail="Équipement non trouvé")
    return db_eq

@router.put("/{equipement_id}", response_model=EquipementResponse)
def update_equipement(equipement_id: int, equipement: EquipementCreate, db: Session = Depends(get_db)):
    db_eq = db.query(Equipement).filter(Equipement.id == equipement_id).first()
    if not db_eq:
        raise HTTPException(status_code=404, detail="Équipement non trouvé")
    for key, value in equipement.model_dump().items():
        setattr(db_eq, key, value)
    db.commit()
    db.refresh(db_eq)
    return db_eq

@router.delete("/{equipement_id}")
def delete_equipement(equipement_id: int, db: Session = Depends(get_db)):
    db_eq = db.query(Equipement).filter(Equipement.id == equipement_id).first()
    if not db_eq:
        raise HTTPException(status_code=404, detail="Équipement non trouvé")
    db.delete(db_eq)
    db.commit()
    return {"message": "Équipement supprimé avec succès"}