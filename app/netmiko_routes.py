from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.databases import get_db
from app.models import Equipement, Topology, Node
from app.routes.gns3 import GNS3Service
from app.netmiko_service import send_config_to_device

router = APIRouter(prefix="/netmiko", tags=["Netmiko Automation"])

@router.post("/configure/{equipement_id}")
def configure_equipment(equipement_id: int, payload: dict, db: Session = Depends(get_db)):
    # 1. Récupérer l'équipement dans la table 'equipements' (où SW_L23_1 a l'ID 6)
    equipment = db.query(Equipement).filter(Equipement.id == equipement_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Équipement introuvable dans la base")

    # 2. Trouver la topologie associée pour récupérer le gns3_project_id
    topology = db.query(Topology).filter(Topology.id == equipment.topology_id).first()
    if not topology or not topology.gns3_project_id:
        raise HTTPException(status_code=404, detail="Projet GNS3 associé introuvable")

    # 3. Interroger l'API GNS3 en utilisant le VRAI nom de l'équipement (ex: "SW_L23_1")
    gns3_service = GNS3Service()
    try:
        ip, port = gns3_service.get_node_console(topology.gns3_project_id, equipment.nom)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 4. Préparer les paramètres Netmiko avec la bonne IP et le bon port console GNS3
    device_params = payload.copy()
    device_params["ip"] = ip
    device_params["port"] = port
    
    commands = device_params.pop("commands", [])

    # 5. Exécuter la configuration
    result = send_config_to_device(device_params, commands)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "message": f"Configuration appliquée avec succès sur {equipment.nom}",
        "output": result["output"]
    }