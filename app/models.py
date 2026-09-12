from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.databases import Base

class Equipement(Base):
    __tablename__ = "equipements"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(50), nullable=False)
    adresse_ip = Column(String(50), nullable=True)
    port = Column(Integer, nullable=True)  # <-- AJOUTE CETTE LIGNE
    type_equipement = Column(String(50), default="routeur")
    actif = Column(Boolean, default=True)
    date_creation = Column(DateTime, default=datetime.utcnow)
    
    # Clé étrangère vers la topologie (projet)
    topology_id = Column(Integer, ForeignKey("topologies.id", ondelete="CASCADE"), nullable=True)
    topology = relationship("Topology", back_populates="equipements")
    vlans = relationship("Vlan", back_populates="equipement", cascade="all, delete-orphan")
    # Relation vers la table interfaces
    interfaces = relationship("Interface", back_populates="equipement", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="equipement", cascade="all, delete-orphan")


class Interface(Base):
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(50), nullable=False)
    statut = Column(String(20), default="down")
    vlan = Column(Integer, nullable=True)
    adresse_ip = Column(String(50), nullable=True)
    masque = Column(String(50), nullable=True)
    
    equipement_id = Column(Integer, ForeignKey("equipements.id", ondelete="CASCADE"))
    equipement = relationship("Equipement", back_populates="interfaces", foreign_keys=[equipement_id])

    # Nouvelle liaison point-à-point vers une autre interface
    target_interface_id = Column(Integer, ForeignKey("interfaces.id", ondelete="SET NULL"), nullable=True)


class Utilisateur(Base):
    __tablename__ = "users"  # Cibler la table 'users' de la capture phpMyAdmin

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="lecteur")


class Topology(Base):
    __tablename__ = "topologies"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    gns3_project_id = Column(String(100), nullable=True)

    nodes = relationship("Node", back_populates="topology", cascade="all, delete-orphan")
    links = relationship("Link", back_populates="topology", cascade="all, delete-orphan")
    equipements = relationship("Equipement", back_populates="topology", cascade="all, delete-orphan")


class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    node_type = Column(String(50), nullable=False)
    topology_id = Column(Integer, ForeignKey("topologies.id"))

    topology = relationship("Topology", back_populates="nodes")


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    topology_id = Column(Integer, ForeignKey("topologies.id"))
    src_node_name = Column(String(100), nullable=False)
    src_port = Column(Integer, default=0)
    dst_node_name = Column(String(100), nullable=False)
    dst_port = Column(Integer, default=0)

    topology = relationship("Topology", back_populates="links")

class Vlan(Base):
    __tablename__ = "vlans"

    id = Column(Integer, primary_key=True, index=True)
    vlan_id = Column(Integer, nullable=False)
    nom = Column(String(50), nullable=True)

    equipement_id = Column(Integer, ForeignKey("equipements.id", ondelete="CASCADE"))
    equipement = relationship("Equipement", back_populates="vlans")

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    destination = Column(String(50), nullable=False)
    masque = Column(String(50), nullable=False)
    next_hop = Column(String(50), nullable=False)

    equipement_id = Column(Integer, ForeignKey("equipements.id", ondelete="CASCADE"))
    equipement = relationship("Equipement", back_populates="routes")