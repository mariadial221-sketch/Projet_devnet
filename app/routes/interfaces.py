from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.databases import get_db
from app.models import Interface, Equipement
from app.schemas import InterfaceCreate, InterfaceResponse, LienCreateSchema

router = APIRouter(prefix="/interfaces", tags=["Interfaces"])

@router.get("/", response_model=list[InterfaceResponse])
def get_interfaces(db: Session = Depends(get_db)):
    """
    Récupère la liste de toutes les interfaces réseau.
    """
    return db.query(Interface).all()

@router.post("/", response_model=InterfaceResponse, status_code=status.HTTP_201_CREATED)
def create_interface(
    interface_data: InterfaceCreate,
    db: Session = Depends(get_db)
):
    """
    Crée une interface rattachée à un équipement via JSON body.
    """
    equipement = db.query(Equipement).filter(Equipement.id == interface_data.equipement_id).first()
    if not equipement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Équipement avec l'ID {interface_data.equipement_id} introuvable."
        )

    db_iface = Interface(**interface_data.model_dump())
    db.add(db_iface)
    db.commit()
    db.refresh(db_iface)
    return db_iface


# === AJOUT DE LA NOUVELLE ROUTE POUR RELIER PAR LES NOMS ===
@router.post("/relier", status_code=status.HTTP_201_CREATED)
def relier_equipements(data: LienCreateSchema, db: Session = Depends(get_db)):
    """
    Relie deux équipements et leurs interfaces en utilisant simplement leurs noms (ex: R1, e0/0 <-> SW_L23_1, f0/1).
    """
    # 1. Trouver l'équipement source et son interface
    eq_src = db.query(Equipement).filter(Equipement.nom == data.equipement_src).first()
    if not eq_src:
        raise HTTPException(status_code=404, detail=f"Équipement source '{data.equipement_src}' introuvable.")
    
    iface_src = db.query(Interface).filter(
        Interface.equipement_id == eq_src.id, 
        Interface.nom == data.interface_src
    ).first()
    
    if not iface_src:
        iface_src = Interface(nom=data.interface_src, equipement_id=eq_src.id)
        db.add(iface_src)
        db.commit()
        db.refresh(iface_src)

    # 2. Trouver l'équipement destination et son interface
    eq_dst = db.query(Equipement).filter(Equipement.nom == data.equipement_dst).first()
    if not eq_dst:
        raise HTTPException(status_code=404, detail=f"Équipement destination '{data.equipement_dst}' introuvable.")
    
    iface_dst = db.query(Interface).filter(
        Interface.equipement_id == eq_dst.id, 
        Interface.nom == data.interface_dst
    ).first()
    
    if not iface_dst:
        iface_dst = Interface(nom=data.interface_dst, equipement_id=eq_dst.id)
        db.add(iface_dst)
        db.commit()
        db.refresh(iface_dst)

    # 3. Établir la liaison bidirectionnelle (Target ID)
    iface_src.target_interface_id = iface_dst.id
    iface_dst.target_interface_id = iface_src.id
    db.commit()

    return {
        "status": "success",
        "message": f"Lien établi avec succès entre {data.equipement_src} ({data.interface_src}) et {data.equipement_dst} ({data.interface_dst})"
    }