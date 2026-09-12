import os
import yaml
import logging

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("logs/execution.log"),
            logging.StreamHandler()
        ]
    )

def load_topology(yaml_path="topology.yml"):
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Le fichier {yaml_path} est vide. Veuillez ajouter la configuration YAML.")
        return data

def generate_report(results, extension_info="Routage dynamique OSPF (Zone 0)"):
    report_content = f"""# Rapport Automatique de Déploiement DEVNET

## 1. Contexte & Topologie Déployée
Déploiement automatisé d'une infrastructure bi-site avec réseau de management via l'API REST GNS3 et Netmiko.

## 2. Équipements Configurés
- **R1** : FastEthernet0/0 (LAN Site A), FastEthernet0/1 (Inter-site), FastEthernet1/0 (Management)
- **R2** : FastEthernet0/0 (LAN Site B), FastEthernet0/1 (Inter-site), FastEthernet1/0 (Management)

## 3. Extension Obligatoire
- **Extension choisie** : {extension_info}

## 4. Tests de Validation
"""
    global_status = "SUCCÈS"
    for test_name, success in results.items():
        status_str = "OK" if success else "ÉCHEC"
        report_content += f"- **{test_name}** : {status_str}\n"
        if not success:
            global_status = "ÉCHEC"

    report_content += f"\n## Bilan Final : **{global_status}**\n"

    with open("rapport.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    logging.info("Rapport Markdown 'rapport.md' généré avec succès.")

# Initialisation du logging au chargement du module
setup_logging()
logger = logging.getLogger("projet_devnet")