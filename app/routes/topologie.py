import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import requests
import yaml
import time
from src.validation import verify_ping, verify_interfaces
import ipaddress
from pathlib import Path
from app.netmiko_service import send_config_to_device
from app.databases import get_db
from app.models import Equipement, Interface, Topology, Vlan, Route
from app.utils import logger
from .gns3 import GNS3Service  # à ajouter en haut du fichier si pas déjà présent
gns3 = GNS3Service()  # à ajouter en haut du fichier si pas déjà présent (ou réutiliser l'instance existante)

router = APIRouter(prefix="/topologie", tags=["Topologie GNS3"])

GNS3_SERVER_URL = "http://localhost:3080/v2"

# Dictionnaire de correspondance entre le type_equipement de MySQL et le template_id de GNS3
TEMPLATE_MAP = {
    "ROUTEUR": "1ea37661-3aaa-48d2-94ec-27e8f61c0826",
    "UN ROUTEUR": "1ea37661-3aaa-48d2-94ec-27e8f61c0826",
    "SWITCH L23": "c9321ede-d98d-4f41-8545-475ebf870698",
    "SWITCH L3": "c9321ede-d98d-4f41-8545-475ebf870698",
    "SWITCH 2": "a5ecb339-9af9-4fbc-b52c-c8317c1c5145",
    "VPCS": "19021f99-e36f-394d-b4a1-8aaa902ab9cc"
}

def parse_port_number(nom_interface: str) -> tuple[int, int]:
    """Extrait le numéro de port depuis le nom (ex: Fa0/1 -> 1, eth0 -> 0)."""
    numbers = re.findall(r'\d+', nom_interface)
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    elif len(numbers) == 1:
        return 0, int(numbers[0])
    return 0, 0

# --- NOUVEAUX ENDPOINTS POUR GÉRER LES TOPOLOGIES (À appeler avant le déploiement) ---

@router.post("/creer_projet/{nom}", status_code=status.HTTP_201_CREATED)
def creer_topologie_db(nom: str, description: str = None, db: Session = Depends(get_db)):
    """Enregistre le nom de la topologie/projet en base de données pour pouvoir ensuite la déployer."""
    existing = db.query(Topology).filter(Topology.nom == nom).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Une topologie nommée '{nom}' existe déjà en base."
        )
    
    new_topo = Topology(nom=nom, description=description)
    db.add(new_topo)
    db.commit()
    db.refresh(new_topo)
    
    logger.info(f"Topologie '{nom}' enregistrée avec succès en BDD.")
    return {"status": "success", "message": f"Topologie '{nom}' créée.", "id": new_topo.id}

@router.get("/lister_projets", status_code=status.HTTP_200_OK)
def lister_topologies_db(db: Session = Depends(get_db)):
    """Liste toutes les topologies enregistrées en base de données."""
    topos = db.query(Topology).all()
    return [{"id": t.id, "nom": t.nom, "gns3_project_id": getattr(t, "gns3_project_id", None)} for t in topos]


# --- ENDPOINT DE DÉPLOIEMENT AUTOMATIQUE ---

@router.post("/deploy_from_db/{nom_projet}", status_code=status.HTTP_201_CREATED)
def deploy_from_db(nom_projet: str, db: Session = Depends(get_db)):
    logger.info(f"Déploiement automatique du projet '{nom_projet}'...")

    # 0. Récupérer la topologie / projet correspondante en base de données
    topologie = db.query(Topology).filter(Topology.nom == nom_projet).first()
    if not topologie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projet/Topologie '{nom_projet}' introuvable en base de données. Créez-la d'abord via l'endpoint de création."
        )
    equipements = topologie.equipements
    print("--- DEBUG EQUIPEMENTS ---")
    for eq in equipements:
        print(f"Nom: {eq.nom} | Type: {eq.type_equipement} | Topology ID: {eq.topology_id}")
    print("-------------------------")
    # 1. Création ou réutilisation du projet GNS3
    try:
        res_list = requests.get(f"{GNS3_SERVER_URL}/projects").json()
        existing_proj = next((p for p in res_list if p["name"] == nom_projet), None)

        if existing_proj:
            project_id = existing_proj["project_id"]
            requests.delete(f"{GNS3_SERVER_URL}/projects/{project_id}")

        res_proj = requests.post(f"{GNS3_SERVER_URL}/projects", json={"name": nom_projet})
        res_proj.raise_for_status()
        project_id = res_proj.json()["project_id"]

        topologie.gns3_project_id = project_id
        db.commit()
    except Exception as e:
        logger.error(f"Erreur projet GNS3 : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur GNS3: {str(e)}")

    # 2. Instanciation avec répartition hiérarchique symétrique par branches
    equipements = topologie.equipements
    if not equipements:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Aucun équipement n'est rattaché au projet '{nom_projet}'."
        )

    gns3_node_map = {}

    coeur_sw = [eq for eq in equipements if any(keyword in eq.type_equipement.strip().upper() for keyword in ["ROUTEUR", "L23", "L3"])]
    acces_sw = [eq for eq in equipements if eq not in coeur_sw and ("VPCS" not in eq.type_equipement.strip().upper() and "PC" not in eq.nom.upper())]
    pcs = [eq for eq in equipements if "VPCS" in eq.type_equipement.strip().upper() or "PC" in eq.nom.upper()]

    # Positionnement des équipements de Cœur (Niveau haut)
    for i, eq in enumerate(coeur_sw):
        pos_x = 200 + (i * 300)
        pos_y = 50

        eq_type_clean = eq.type_equipement.strip().upper()
        template_id = TEMPLATE_MAP.get(eq_type_clean)
        if not template_id:
            logger.warning(f"Aucun template trouvé pour {eq.nom} (type: {eq.type_equipement}), ignoré.")
            continue
        try:
            res_node = requests.post(
                f"{GNS3_SERVER_URL}/projects/{project_id}/templates/{template_id}",
                json={"x": pos_x, "y": pos_y}
            )
            res_node.raise_for_status()
            node_data = res_node.json()
            node_id = node_data["node_id"]

            requests.put(
                f"{GNS3_SERVER_URL}/projects/{project_id}/nodes/{node_id}",
                json={"name": eq.nom, "x": pos_x, "y": pos_y}
            )
            gns3_node_map[eq.id] = node_id
            logger.info(f"Nœud Cœur instancié : {eq.nom} en ({pos_x}, {pos_y})")
        except Exception as e:
            logger.error(f"Échec création nœud Cœur {eq.nom} : {str(e)}")

    # Positionnement des Switches d'accès (Niveau milieu)
    for i, eq in enumerate(acces_sw):
        pos_x = 200 + (i * 300)
        pos_y = 250

        eq_type_clean = eq.type_equipement.strip().upper()
        template_id = TEMPLATE_MAP.get(eq_type_clean)
        if not template_id:
            logger.warning(f"Aucun template trouvé pour {eq.nom} (type: {eq.type_equipement}), ignoré.")
            continue
        try:
            res_node = requests.post(
                f"{GNS3_SERVER_URL}/projects/{project_id}/templates/{template_id}",
                json={"x": pos_x, "y": pos_y}
            )
            res_node.raise_for_status()
            node_data = res_node.json()
            node_id = node_data["node_id"]

            requests.put(
                f"{GNS3_SERVER_URL}/projects/{project_id}/nodes/{node_id}",
                json={"name": eq.nom, "x": pos_x, "y": pos_y}
            )
            gns3_node_map[eq.id] = node_id
            logger.info(f"Nœud Accès instancié : {eq.nom} en ({pos_x}, {pos_y})")
        except Exception as e:
            logger.error(f"Échec création nœud Accès {eq.nom} : {str(e)}")

    # Positionnement des PC / VPCS (Niveau bas)
    for i, eq in enumerate(pcs):
        branch_index = i // 2
        sub_index = i % 2

        pos_x = (branch_index * 300) + (sub_index * 120) + 100
        pos_y = 450

        payload = {
            "name": eq.nom,
            "node_type": "vpcs",
            "compute_id": "local",
            "x": pos_x,
            "y": pos_y
        }
        try:
            res_node = requests.post(f"{GNS3_SERVER_URL}/projects/{project_id}/nodes", json=payload)
            res_node.raise_for_status()
            gns3_node_map[eq.id] = res_node.json()["node_id"]
            logger.info(f"Nœud GNS3 VPCS instancié : {eq.nom} en ({pos_x}, {pos_y})")
        except Exception as e:
            logger.error(f"Échec création VPCS {eq.nom} : {str(e)}")

    # 3. Câblage automatique des interfaces basé sur les noms normalisés
    equipement_ids = [eq.id for eq in equipements]
    interfaces = db.query(Interface).filter(
        Interface.equipement_id.in_(equipement_ids),
        Interface.target_interface_id.isnot(None)
    ).all()

    liens_traites = set()
    liens_crees = 0

    for iface in interfaces:
        target_iface = db.query(Interface).filter(Interface.id == iface.target_interface_id).first()
        if not target_iface:
            continue

        eq1 = db.query(Equipement).filter(Equipement.id == iface.equipement_id).first()
        eq2 = db.query(Equipement).filter(Equipement.id == target_iface.equipement_id).first()

        if not eq1 or not eq2:
            continue

        endpoint_a = (eq1.nom, iface.nom)
        endpoint_b = (eq2.nom, target_iface.nom)
        pair = tuple(sorted([endpoint_a, endpoint_b], key=lambda x: (x[0], x[1])))

        if pair in liens_traites:
            continue
        liens_traites.add(pair)

        if iface.equipement_id in gns3_node_map and target_iface.equipement_id in gns3_node_map:
            src_port_adapter, src_port_number = parse_port_number(iface.nom)
            dst_port_adapter, dst_port_number = parse_port_number(target_iface.nom)

            link_payload = {
                "nodes": [
                    {"node_id": gns3_node_map[iface.equipement_id], "adapter_number": src_port_adapter, "port_number": src_port_number},
                    {"node_id": gns3_node_map[target_iface.equipement_id], "adapter_number": dst_port_adapter, "port_number": dst_port_number}
                ]
            }
            try:
                res_link = requests.post(f"{GNS3_SERVER_URL}/projects/{project_id}/links", json=link_payload)
                res_link.raise_for_status()
                liens_crees += 1
                logger.info(f"Lien créé : {eq1.nom}:{iface.nom} <-> {eq2.nom}:{target_iface.nom}")
            except requests.exceptions.HTTPError as he:
                if he.response.status_code == 409:
                    logger.warning(f"Le lien {eq1.nom}:{iface.nom} <-> {eq2.nom}:{target_iface.nom} existe déjà dans GNS3 (ignoré).")
                else:
                    logger.error(f"Erreur HTTP création du lien : {str(he)}")
            except Exception as e:
                logger.error(f"Erreur inattendue création du lien : {str(e)}")

    # 4. Démarrage automatique de tous les équipements du projet
    try:
        res_start = requests.post(f"{GNS3_SERVER_URL}/projects/{project_id}/nodes/start")
        res_start.raise_for_status()
        logger.info(f"Tous les nœuds du projet '{nom_projet}' ont été démarrés automatiquement.")
        time.sleep(20)
    except Exception as e:
        logger.error(f"Erreur lors du démarrage automatique des nœuds : {str(e)}")

    return {
        "status": "success",
        "projet": nom_projet,
        "noeuds_deployes": len(gns3_node_map),
        "liens_cables": liens_crees
    }

@router.post("/importer_yaml/{nom_projet}", status_code=status.HTTP_201_CREATED)
def importer_yaml_vers_db(nom_projet: str, db: Session = Depends(get_db)):
    yaml_path = Path("topology.yml")
    if not yaml_path.exists():
        raise HTTPException(status_code=404, detail="Fichier topology.yml introuvable à la racine du projet.")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # 1. Récupérer ou créer la topologie en BDD
    topologie = db.query(Topology).filter(Topology.nom == nom_projet).first()
    if not topologie:
        topologie = Topology(nom=nom_projet, description="Importé automatiquement depuis YAML")
        db.add(topologie)
        db.commit()
        db.refresh(topologie)
    else:
        # Nettoyage des anciens équipements/interfaces pour repartir sur une base propre liée au YAML
        anciens_eqs = db.query(Equipement).filter(Equipement.topology_id == topologie.id).all()
        for eq in anciens_eqs:
            db.query(Interface).filter(Interface.equipement_id == eq.id).delete()
            db.delete(eq)
        db.commit()

    eq_map = {}

    # 2. Insertion des équipements du YAML, avec leurs VLANs, interfaces et routes
    for device in data.get("devices", []):
        nom_eq = device.get("name")
        type_eq = device.get("template")
        ip_mgmt = device.get("management_ip")

        eq = Equipement(
            nom=nom_eq,
            type_equipement=type_eq,
            adresse_ip=ip_mgmt,
            topology_id=topologie.id
        )
        db.add(eq)
        db.commit()
        db.refresh(eq)
        eq_map[nom_eq] = eq

        # Insertion des VLANs déclarés pour CET équipement (dans la boucle !)
        for vlan_data in device.get("vlans", []):
            vlan = Vlan(
                vlan_id=vlan_data.get("id"),
                nom=vlan_data.get("name"),
                equipement_id=eq.id
            )
            db.add(vlan)

        # Insertion/mise à jour des interfaces avec IP ou VLAN déclarées pour CET équipement
        for iface_data in device.get("interfaces", []):
            nom_iface = iface_data.get("name")
            ip_cidr = iface_data.get("ip")
            vlan_id = iface_data.get("vlan")

            iface = db.query(Interface).filter(
                Interface.nom == nom_iface,
                Interface.equipement_id == eq.id
            ).first()

            if not iface:
                iface = Interface(nom=nom_iface, statut="down", equipement_id=eq.id)
                db.add(iface)

            if ip_cidr:
                ip, prefixe = ip_cidr.split("/")
                masque = str(ipaddress.IPv4Network(f"0.0.0.0/{prefixe}").netmask)
                iface.adresse_ip = ip
                iface.masque = masque

            if vlan_id:
                iface.vlan = vlan_id

        # Insertion des routes statiques déclarées pour CET équipement
        for route_data in device.get("routes", []):
            route = Route(
                destination=route_data.get("destination"),
                masque=route_data.get("mask"),
                next_hop=route_data.get("next_hop"),
                equipement_id=eq.id
            )
            db.add(route)

        db.commit()

    # 3. Insertion des liaisons point-à-point entre interfaces
    for link in data.get("links", []):
        src_node = link.get("node1")
        src_port = link.get("port1")
        dst_node = link.get("node2")
        dst_port = link.get("port2")

        if src_node in eq_map and dst_node in eq_map:
            iface_src = db.query(Interface).filter(
                Interface.nom == src_port,
                Interface.equipement_id == eq_map[src_node].id
            ).first()
            if not iface_src:
                iface_src = Interface(nom=src_port, statut="down", equipement_id=eq_map[src_node].id)
                db.add(iface_src)
                db.commit()
                db.refresh(iface_src)

            iface_dst = db.query(Interface).filter(
                Interface.nom == dst_port,
                Interface.equipement_id == eq_map[dst_node].id
            ).first()
            if not iface_dst:
                iface_dst = Interface(nom=dst_port, statut="down", equipement_id=eq_map[dst_node].id)
                db.add(iface_dst)
                db.commit()
                db.refresh(iface_dst)

            iface_src.target_interface_id = iface_dst.id
            iface_dst.target_interface_id = iface_src.id
            db.commit()

    return {
        "status": "success",
        "message": f"Le fichier YAML a été synchronisé avec succès pour le projet '{nom_projet}'."
    }



@router.post("/configurer_reseau/{nom_projet}")
def lancer_configuration_reseau(nom_projet: str, db: Session = Depends(get_db)):
    topologie = db.query(Topology).filter(Topology.nom == nom_projet).first()
    if not topologie:
        raise HTTPException(status_code=404, detail="Topologie introuvable en base de données.")

    if not topologie.gns3_project_id:
        raise HTTPException(status_code=400, detail="Cette topologie n'est liée à aucun projet GNS3.")

    resultats = []

    for eq in topologie.equipements:
        # Les VPCS n'ont pas de CLI Cisco IOS — on les exclut de la configuration Netmiko
        if "VPCS" in (eq.type_equipement or "").strip().upper():
            resultats.append({
                "equipement": eq.nom,
                "ip": eq.adresse_ip,
                "resultat": {"success": True, "output": "VPCS ignoré (pas de configuration IOS applicable)."}
            })
            continue

        # Résolution dynamique du host/port console via l'API GNS3
        # (ne pas utiliser eq.port, qui n'est pas maintenu en base)
        try:
            console_host, console_port = gns3.get_node_console(
                project_id=topologie.gns3_project_id, node_name=eq.nom
            )
        except Exception as e:
            resultats.append({
                "equipement": eq.nom,
                "ip": eq.adresse_ip,
                "resultat": {"success": False, "error": f"Erreur de résolution GNS3 : {str(e)}"}
            })
            continue

        print(f"DEBUG EQUIPEMENT -> Nom: {eq.nom}, Host: {console_host}, Port: {console_port}")

        device_params = {
            "device_type": "cisco_ios_telnet",
            "ip": console_host,
            "port": console_port,
            "username": "",
            "password": ""
        }

        commandes = []

        for vlan in eq.vlans:
            commandes.append(f"vlan {vlan.vlan_id}")
            if vlan.nom:
                commandes.append(f"name {vlan.nom}")

        for iface in eq.interfaces:
            if iface.adresse_ip and iface.masque:
                commandes.append(f"interface {iface.nom}")
                commandes.append("no switchport")
                commandes.append(f"ip address {iface.adresse_ip} {iface.masque}")
                commandes.append("no shutdown")
            elif iface.vlan:
                commandes.append(f"interface {iface.nom}")
                commandes.append("switchport mode access")
                commandes.append(f"switchport access vlan {iface.vlan}")

        # Routage statique (nécessite "ip routing" sur les switches multicouches)
        if eq.routes:
            commandes.append("ip routing")
            for route in eq.routes:
                commandes.append(f"ip route {route.destination} {route.masque} {route.next_hop}")

        if not commandes:
            commandes = [f"hostname {eq.nom}"]

        commandes.append("end")
        commandes.append("write memory")

        res = send_config_to_device(device_params, commandes)
        resultats.append({
            "equipement": eq.nom,
            "ip": eq.adresse_ip,
            "resultat": res
        })

    return {
        "status": "success",
        "message": "Configuration Netmiko exécutée sur les équipements.",
        "details": resultats
    }

@router.post("/valider_reseau/{nom_projet}")
def valider_reseau(nom_projet: str, db: Session = Depends(get_db)):
    topologie = db.query(Topology).filter(Topology.nom == nom_projet).first()
    if not topologie:
        raise HTTPException(status_code=404, detail="Topologie introuvable en base de données.")
    if not topologie.gns3_project_id:
        raise HTTPException(status_code=400, detail="Cette topologie n'est liée à aucun projet GNS3.")

    resultats = []

    for eq in topologie.equipements:
        interfaces_res = verify_interfaces(gns3, topologie.gns3_project_id, eq.nom)

        # Ping vers chaque interface distante déclarée via target_interface_id
        pings = []
        for iface in eq.interfaces:
            if iface.target_interface_id and iface.adresse_ip:
                target_iface = db.query(Interface).filter(Interface.id == iface.target_interface_id).first()
                if target_iface and target_iface.adresse_ip:
                    ping_res = verify_ping(gns3, topologie.gns3_project_id, eq.nom, target_iface.adresse_ip)
                    pings.append({"cible": target_iface.adresse_ip, "resultat": ping_res})

        resultats.append({
            "equipement": eq.nom,
            "interfaces": interfaces_res,
            "pings": pings
        })

    # Test de connectivité inter-LAN (bout en bout via le routage R1↔R2)
    cross_tests = [("SW_L23_1", "192.168.2.2"), ("SW2", "192.168.1.2")]
    for src_name, target_ip in cross_tests:
        if any(e.nom == src_name for e in topologie.equipements):
            ping_res = verify_ping(gns3, topologie.gns3_project_id, src_name, target_ip)
            resultats.append({
                "equipement": f"{src_name} (test inter-LAN)",
                "cible": target_ip,
                "resultat": ping_res
            })

    return {
        "status": "success",
        "message": "Validation réseau exécutée.",
        "details": resultats
    }


from datetime import datetime

@router.post("/generer_rapport/{nom_projet}")
def generer_rapport(nom_projet: str, db: Session = Depends(get_db)):
    topologie = db.query(Topology).filter(Topology.nom == nom_projet).first()
    if not topologie:
        raise HTTPException(status_code=404, detail="Topologie introuvable en base de données.")

    # Ré-exécute la configuration et la validation pour avoir des résultats frais
    config_result = lancer_configuration_reseau(nom_projet, db)
    validation_result = valider_reseau(nom_projet, db)

    lignes = []
    lignes.append("# Rapport Automatique de Déploiement DEVNET\n")
    lignes.append(f"**Projet :** {nom_projet}  ")
    lignes.append(f"**Date de génération :** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lignes.append(f"**Projet GNS3 lié :** `{topologie.gns3_project_id}`\n")

    lignes.append("## 1. Contexte & Topologie Déployée")
    lignes.append(
        "Déploiement automatisé d'une infrastructure bi-site (LAN A / LAN B) reliée par un lien "
        "inter-site routé, avec réseau de management, via l'API REST GNS3 et Netmiko.\n"
    )

    lignes.append("## 2. Équipements Déployés\n")
    lignes.append("| Équipement | Type | IP de management |")
    lignes.append("|---|---|---|")
    for eq in topologie.equipements:
        lignes.append(f"| {eq.nom} | {eq.type_equipement} | {eq.adresse_ip or '—'} |")
    lignes.append("")

    lignes.append("## 3. Configuration Appliquée\n")
    for item in config_result["details"]:
        statut = "✅ SUCCÈS" if item["resultat"].get("success") else "❌ ÉCHEC"
        lignes.append(f"### {item['equipement']} — {statut}")
        if item["resultat"].get("success"):
            lignes.append("```")
            lignes.append(item["resultat"].get("output", "")[:1000])
            lignes.append("```")
        else:
            lignes.append(f"- Erreur : {item['resultat'].get('error', 'Inconnue')}")
        lignes.append("")

    lignes.append("## 4. Extension Obligatoire — VLANs\n")
    lignes.append(
        "Extension choisie : **configuration de VLANs** sur `SW_L23_1` "
        "(VLAN 10 - ADMINISTRATION, VLAN 20 - PEDAGOGIE), avec routage statique "
        "assurant la connectivité inter-LAN.\n"
    )

    lignes.append("## 5. Tests de Validation\n")
    tous_reussis = True
    for item in validation_result["details"]:
        if "pings" in item:
            for p in item["pings"]:
                statut = "✅ SUCCÈS" if p["resultat"].get("success") else "❌ ÉCHEC"
                if not p["resultat"].get("success"):
                    tous_reussis = False
                lignes.append(f"- Ping **{item['equipement']}** → `{p['cible']}` : {statut}")
        elif "resultat" in item:
            statut = "✅ SUCCÈS" if item["resultat"].get("success") else "❌ ÉCHEC"
            if not item["resultat"].get("success"):
                tous_reussis = False
            lignes.append(f"- {item['equipement']} → `{item.get('cible', '')}` : {statut}")
    lignes.append("")

    bilan = "✅ SUCCÈS" if tous_reussis else "❌ ÉCHEC"
    lignes.append(f"## Bilan Final : **{bilan}**\n")

    contenu = "\n".join(lignes)

    rapport_path = Path("rapport.md")
    with open(rapport_path, "w", encoding="utf-8") as f:
        f.write(contenu)

    return {
        "status": "success",
        "message": "rapport.md généré avec succès.",
        "bilan": bilan
    }