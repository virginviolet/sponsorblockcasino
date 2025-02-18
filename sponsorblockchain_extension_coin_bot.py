# region Imports
from flask import Flask, request, jsonify, Response
import os
import json
from dotenv import load_dotenv
from typing import Tuple
from sponsorblockchain_coin_bot_types import SlotMachineConfig
# endregion

# region Constants
# Load .env file for the server token
load_dotenv()
SERVER_TOKEN: str | None = os.getenv('SERVER_TOKEN')
slot_machine_config_path = "data/slot_machine.json"
# endregion

# region Function


def save_slot_config(config: SlotMachineConfig) -> None:
    file_name: str = slot_machine_config_path
    file_exists: bool = os.path.exists(file_name)
    file_empty: bool = file_exists and os.stat(
        file_name).st_size == 0
    if not file_exists or file_empty:
        directories: str = (file_name[:file_name.rfind("/")])
        os.makedirs(directories, exist_ok=True)
    with open(file_name, "w") as file:
        file.write(json.dumps(config))
# endregion

# region API Routes
# TODO Command to restart the bot


def register_routes(app: Flask) -> None:
    @app.route("/set_slot_machine_config", methods=["POST"])
    # API Route: Add a slot machine config
    def set_slot_machine_config() -> Tuple[Response, int]:
        token: str | None = request.headers.get("token")
        if not token:
            return jsonify({"message": "Token is required."}), 400
        if token != SERVER_TOKEN:
            return jsonify({"message": "Invalid token."}), 400
        data: SlotMachineConfig = request.get_json()
        if not data:
            return jsonify({"message": "Data is required."}), 400
        try:
            save_slot_config(config=data)
            # Use the `reboot` parameter of the /slots command
            # to reload the slot machine config
            return jsonify({"message": "Slot machine config updated."}), 200
        except Exception as e:
            return jsonify(
                {"message": f"Error saving slot machine config: {str(e)}"}), 500
    # endregion
