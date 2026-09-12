import logging
from netmiko import ConnectHandler

logger = logging.getLogger(__name__)

def verify_ping(gns3_service, project_id: str, device_name: str, target_ip: str):
    """Se connecte à un équipement via sa console GNS3 (telnet) et teste un ping vers target_ip."""
    try:
        console_host, console_port = gns3_service.get_node_console(
            project_id=project_id, node_name=device_name
        )
    except Exception as e:
        error_msg = f"Impossible de résoudre la console GNS3 pour {device_name} : {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    device_params = {
        "device_type": "cisco_ios_telnet",
        "ip": console_host,
        "port": console_port,
        "username": "",
        "password": "",
        "fast_cli": False,
        "conn_timeout": 60,
        "global_delay_factor": 8,
    }

    try:
        with ConnectHandler(**device_params) as net_connect:
            output = net_connect.send_command(f"ping {target_ip}", read_timeout=30)

        success = "Success rate is 80" in output or "Success rate is 100" in output
        logger.info(f"Test Ping {device_name} -> {target_ip} : {'SUCCÈS' if success else 'ÉCHEC'}")
        return {"success": success, "output": output}

    except Exception as e:
        error_msg = f"Erreur lors du ping depuis {device_name} vers {target_ip} : {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


def verify_interfaces(gns3_service, project_id: str, device_name: str):
    """Vérifie l'état des interfaces d'un équipement (show ip interface brief)."""
    try:
        console_host, console_port = gns3_service.get_node_console(
            project_id=project_id, node_name=device_name
        )
    except Exception as e:
        return {"success": False, "error": f"Résolution GNS3 échouée : {e}"}

    device_params = {
        "device_type": "cisco_ios_telnet",
        "ip": console_host,
        "port": console_port,
        "username": "",
        "password": "",
        "fast_cli": False,
        "conn_timeout": 60,
        "global_delay_factor": 8,
    }

    try:
        with ConnectHandler(**device_params) as net_connect:
            output = net_connect.send_command("show ip interface brief", read_timeout=30)
        return {"success": True, "output": output}
    except Exception as e:
        error_msg = f"Erreur lors de la vérification des interfaces sur {device_name} : {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}