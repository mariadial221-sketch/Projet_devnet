from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- SCHÉMAS INTERFACE ---
class InterfaceBase(BaseModel):
    nom: str
    statut: Optional[str] = "down"
    vlan: Optional[int] = None
    adresse_ip: Optional[str] = None
    masque: Optional[str] = None
    equipement_id: int
    target_interface_id: Optional[int] = None

class InterfaceCreate(InterfaceBase):
    pass

class InterfaceResponse(InterfaceBase):
    id: int

    class Config:
        from_attributes = True

# --- SCHÉMAS ÉQUIPEMENT ---
class EquipementBase(BaseModel):
    nom: str
    adresse_ip: Optional[str] = None
    port: Optional[int] = None
    type_equipement: Optional[str] = "routeur"
    actif: Optional[bool] = True
    topology_id: Optional[int] = None  # Liaison vers le projet/topologie

class EquipementCreate(EquipementBase):
    pass

class EquipementResponse(EquipementBase):
    id: int
    date_creation: Optional[datetime] = None
    interfaces: List[InterfaceResponse] = []

    class Config:
        from_attributes = True

# --- SCHÉMAS TOPOLOGIE / PROJET ---
class TopologyBase(BaseModel):
    nom: str
    description: Optional[str] = None

class TopologyCreate(TopologyBase):
    pass

class TopologyResponse(TopologyBase):
    id: int
    gns3_project_id: Optional[str] = None
    equipements: List[EquipementResponse] = []

    class Config:
        from_attributes = True

# --- SCHÉMAS AUTHENTIFICATION / UTILISATEURS ---
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "lecteur"  # "admin" ou "lecteur"

class UserResponse(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# --- SCHÉMA AUTOMATISATION NETMIKO ---
class ConfigNodeSchema(BaseModel):
    device_type: str = "cisco_ios"
    host: str
    username: str
    password: str
    secret: Optional[str] = ""
    port: Optional[int] = 22
    commandes: List[str]

class LienCreateSchema(BaseModel):
    equipement_src: str
    interface_src: str
    equipement_dst: str
    interface_dst: str

class NetmikoDeviceConfigRequest(BaseModel):
    device_type: str = "cisco_ios_telnet"
    username: str = ""
    password: str = ""
    secret: Optional[str] = ""
    commands: List[str]
    # Champs ajoutés pour le pont dynamique GNS3
    gns3_project_id: Optional[str] = None  # UUID du projet GNS3
    node_name: Optional[str] = None        # Nom du nœud (ex: "SW_L23_1")