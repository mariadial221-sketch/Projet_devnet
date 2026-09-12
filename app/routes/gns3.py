import os
import requests
import logging
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.databases import get_db
from app.models import Node, Topology

load_dotenv()
GNS3_SERVER = os.getenv("GNS3_SERVER_URL", "http://localhost:3080")

router = APIRouter(prefix="/gns3", tags=["GNS3"])

class GNS3Manager:
    def __init__(self, server_url=GNS3_SERVER):
        self.server_url = server_url.rstrip("/")
        self.project_id = None

    def create_project(self, name):
        url = f"{self.server_url}/v2/projects"
        res = requests.post(url, json={"name": name})
        if res.status_code in [200, 201]:
            self.project_id = res.json()["project_id"]
            logging.info(f"Projet GNS3 '{name}' créé (ID: {self.project_id}).")
            return self.project_id
        else:
            logging.error(f"Erreur lors de la création du projet GNS3 : {res.text}")
            return None

    def start_all_nodes(self):
        if not self.project_id:
            return False
        url = f"{self.server_url}/v2/projects/{self.project_id}/nodes/start"
        res = requests.post(url)
        if res.status_code == 200:
            logging.info("Tous les nœuds du projet ont été démarrés.")
            return True
        logging.error(f"Erreur lors du démarrage des nœuds : {res.text}")
        return False

class GNS3Service:
    def __init__(self, server_url=GNS3_SERVER):
        self.server_url = server_url.rstrip("/")

    def get_node_console(self, project_id: str, node_name: str):
        url = f"{self.server_url}/v2/projects/{project_id}/nodes"
        res = requests.get(url)
        
        if res.status_code != 200:
            raise Exception(f"Impossible de lister les nœuds GNS3 : {res.text}")
            
        nodes = res.json()
        print("--- DEBUG GNS3 NODES ---")
        for node in nodes:
            print(f"Nom: {node.get('name')} | Type: {node.get('node_type')} | Host: {node.get('console_host')} | Port Console: {node.get('console')}")
            if node.get("name") == node_name:
                console_host = node.get("console_host", "127.0.0.1")
                console_port = node.get("console")
                return console_host, console_port
                
        raise Exception(f"Nœud '{node_name}' introuvable dans le projet GNS3 {project_id}.")

@router.post("/topologies/{topology_id}/sync-nodes")
def sync_gns3_nodes(topology_id: int, db: Session = Depends(get_db)):
    topologie = db.query(Topology).filter(Topology.id == topology_id).first()
    if not topologie or not topologie.gns3_project_id:
        raise HTTPException(status_code=404, detail="Topologie ou projet GNS3 non trouvé")

    gns3_service = GNS3Service()
    url = f"{gns3_service.server_url}/v2/projects/{topologie.gns3_project_id}/nodes"
    res = requests.get(url)
    
    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Impossible de récupérer les nœuds depuis GNS3")

    gns3_nodes = res.json()
    
    # Nettoyer les anciens nœuds de cette topologie pour éviter les doublons
    db.query(Node).filter(Node.topology_id == topology_id).delete()

    # Insérer les vrais nœuds du projet GNS3
    for n in gns3_nodes:
        db_node = Node(
            nom=n.get("name"),
            node_type=n.get("node_type"),
            port=n.get("console"),
            topology_id=topology_id
        )
        db.add(db_node)
    
    db.commit()
    return {"message": f"{len(gns3_nodes)} nœuds synchronisés avec succès."}