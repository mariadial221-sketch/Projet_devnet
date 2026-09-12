import logging
import time
from netmiko import ConnectHandler

logger = logging.getLogger(__name__)

IOS_ERROR_MARKERS = [
    "% Invalid input",
    "% Incomplete command",
    "% Ambiguous command",
    "% Unrecognized command",
]

def send_config_to_device(device_params: dict, config_command_list: list):
    try:
        for key in ["username", "password", "secret"]:
            if not device_params.get(key):
                device_params.pop(key, None)

        device_params["device_type"] = "cisco_ios_telnet"
        device_params["fast_cli"] = False
        device_params["conn_timeout"] = 60
        device_params["global_delay_factor"] = 8  # augmenté : IOU distant plus lent que prévu

        print(
            "DEBUG NETMIKO PARAMS -> IP:", device_params.get("ip"),
            "Port:", device_params.get("port"),
            "Type:", device_params.get("device_type")
        )

        with ConnectHandler(**device_params) as net_connect:
            try:
                net_connect.enable()
            except Exception:
                pass

            net_connect.config_mode()
            time.sleep(1)  # laisse l'IOU stabiliser le prompt avant d'envoyer les commandes

            output_log = []
            for cmd in config_command_list:
                out = net_connect.send_command(
                    cmd,
                    expect_string=r"#",
                    read_timeout=30,
                    strip_prompt=False,
                    strip_command=False,
                )
                output_log.append(out)
                time.sleep(0.5)  # petite pause entre chaque commande

            net_connect.exit_config_mode()
            output = "\n".join(output_log)

            for marker in IOS_ERROR_MARKERS:
                if marker in output:
                    error_msg = f"Commande rejetée par l'équipement :\n{output}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}

            return {"success": True, "output": output}

    except Exception as e:
        error_msg = f"Erreur de connexion Netmiko : {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}