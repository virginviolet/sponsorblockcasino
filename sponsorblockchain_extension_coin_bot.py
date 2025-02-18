# region Imports
from flask import Flask, request, jsonify, Response
import os
import json
from dotenv import load_dotenv
from typing import Tuple
from sponsorblockchain_coin_bot_types import SlotMachineConfig, BotConfig
# endregion

# region Constants
# Load .env file for the server token
load_dotenv()
SERVER_TOKEN: str | None = os.getenv('SERVER_TOKEN')
slot_machine_config_path = "data/slot_machine.json"
bot_config_path = "data/bot_config.json"
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


def save_bot_config(config: BotConfig) -> None:
    file_name: str = bot_config_path
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
# TODO Get and set save data
# TODO Get and set checkpoints


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

    @app.route("/get_slot_machine_config", methods=["GET"])
    # API Route: Get the slot machine config
    def get_slot_machine_config() -> Tuple[Response, int]:
        token: str | None = request.headers.get("token")
        if not token:
            return jsonify({"message": "Token is required."}), 400
        if token != SERVER_TOKEN:
            return jsonify({"message": "Invalid token."}), 400
        if not os.path.exists(slot_machine_config_path):
            return jsonify({"message": "Slot machine config not found."}), 404
        with open(slot_machine_config_path, "r") as file:
            data: SlotMachineConfig = json.load(file)
            return jsonify(data), 200

    @app.route("/set_bot_config", methods=["POST"])
    # API Route: Set the bot config
    def set_bot_config() -> Tuple[Response, int]:
        token: str | None = request.headers.get("token")
        if not token:
            return jsonify({"message": "Token is required."}), 400
        if token != SERVER_TOKEN:
            return jsonify({"message": "Invalid token."}), 400
        data: BotConfig = request.get_json()
        if not data:
            return jsonify({"message": "Data is required."}), 400
        try:
            save_bot_config(config=data)
            return jsonify({"message": "Bot config updated."}), 200
        except Exception as e:
            return jsonify(
                {"message": f"Error saving bot config: {str(e)}"}), 500

    @app.route("/get_bot_config", methods=["GET"])
    # API Route: Get the bot config
    def get_bot_config() -> Tuple[Response, int]:
        token: str | None = request.headers.get("token")
        if not token:
            return jsonify({"message": "Token is required."}), 400
        if token != SERVER_TOKEN:
            return jsonify({"message": "Invalid token."}), 400
        if not os.path.exists(bot_config_path):
            return jsonify({"message": "Bot config not found."}), 404
        with open(bot_config_path, "r") as file:
            data: BotConfig = json.load(file)
            return jsonify(data), 200
        
    # endregion
