# region Imports
from io import BytesIO
from flask import Flask, request, jsonify, Response, send_file
import os
import json
import zipfile
from dotenv import load_dotenv
from werkzeug.datastructures.file_storage import FileStorage
from typing import Tuple
from sponsorblockchain_coin_bot_types import SlotMachineConfig, BotConfig
# endregion

# region Constants
# Load .env file for the server token
load_dotenv()
SERVER_TOKEN: str | None = os.getenv('SERVER_TOKEN')
slot_machine_config_path = "data/slot_machine.json"
bot_config_path = "data/bot_config.json"
checkpoints_path = "data/checkpoints"
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
        print("Received request to set slot machine config.")
        token: str | None = request.headers.get("token")
        message: str
        if not token:
            message = "Token is required."
            print(message)
            return jsonify({"message": message}), 400
        if token != SERVER_TOKEN:
            message = "Invalid token."
            print(message)
            return jsonify({"message": message}), 400
        data: SlotMachineConfig = request.get_json()
        if not data:
            message = "Data is required."
            print(message)
            return jsonify({"message": message}), 400
        try:
            save_slot_config(config=data)
            # Use the `reboot` parameter of the /slots command
            # to reload the slot machine config
            message = "Slot machine config updated."
            print(message)
            return jsonify({"message": message}), 200
        except Exception as e:
            message = f"Error saving slot machine config: {str(e)}"
            return jsonify(
                {"message": message}), 500

    @app.route("/get_slot_machine_config", methods=["GET"])
    # API Route: Get the slot machine config
    def get_slot_machine_config() -> Tuple[Response, int]:
        print("Received request to get slot machine config.")
        message: str
        token: str | None = request.headers.get("token")
        if not token:
            message = "Token is required."
            print(message)
            return jsonify({"message": message}), 400
        if token != SERVER_TOKEN:
            message = "Invalid token."
            print(message)
            return jsonify({"message": message}), 400
        if not os.path.exists(slot_machine_config_path):
            message = "Slot machine config not found."
            print(message)
            return jsonify({"message": message}), 404
        with open(slot_machine_config_path, "r") as file:
            data: SlotMachineConfig = json.load(file)
            print("Slot machine config will be returned.")
            return jsonify(data), 200

    @app.route("/set_bot_config", methods=["POST"])
    # API Route: Set the bot config
    def set_bot_config() -> Tuple[Response, int]:
        print("Received request to set bot config.")
        message: str
        token: str | None = request.headers.get("token")
        if not token:
            message = "Token is required."
            print(message)
            return jsonify({"message": message}), 400
        if token != SERVER_TOKEN:
            message = "Invalid token."
            print(message)
            return jsonify({"message": message}), 400
        data: BotConfig = request.get_json()
        if not data:
            message = "Data is required."
            print(message)
            return jsonify({"message": message}), 400
        try:
            save_bot_config(config=data)
            message = "Bot config updated."
            print(message)
            return jsonify({"message": message}), 200
        except Exception as e:
            message = f"Error saving bot config: {str(e)}"
            print(message)
            return jsonify(
                {"message": message}), 500

    @app.route("/get_bot_config", methods=["GET"])
    # API Route: Get the bot config
    def get_bot_config() -> Tuple[Response, int]:
        print("Received request to get bot config.")
        message: str
        token: str | None = request.headers.get("token")
        if not token:
            message = "Token is required."
            print(message)
            return jsonify({"message": message}), 400
        if token != SERVER_TOKEN:
            message = "Invalid token."
            print(message)
            return jsonify({"message": message}), 400
        if not os.path.exists(bot_config_path):
            message = "Bot config not found."
            print(message)
            return jsonify({"message": message}), 404
        with open(bot_config_path, "r") as file:
            data: BotConfig = json.load(file)
            print("Bot config will be returned.")
            return jsonify(data), 200
    
    @app.route("/download_checkpoints", methods=["GET"])
    # API Route: Download the checkpoints
    def download_checkpoints() -> Tuple[Response, int]:
        print("Received request to download checkpoints.")
        message: str
        token: str | None = request.headers.get("token")
        if not token:
            message = "Token is required."
            print(message)
            return jsonify({"message": message}), 400
        if token != SERVER_TOKEN:
            message = "Invalid token."
            print(message)
            return jsonify({"message": message}), 400
        if not os.path.exists(checkpoints_path):
            message = "Checkpoints not found."
            print(message)
            return jsonify({"message": message}), 404
        try:
            # Easier to store the file in memory than to add threading to remove
            # the file after the response is sent
            print("Creating zip file in memory...")
            memory_file = BytesIO()
            with zipfile.ZipFile(
                memory_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for root, _, files in os.walk(checkpoints_path):
                    for file in files:
                        zip_file.write(os.path.join(root, file))
            print("Zip file created in memory.")
        except Exception as e:
            return jsonify(
                {"message": f"Error downloading checkpoints: {str(e)}"}), 500
        memory_file.seek(0)
        print("Checkpoints will be sent.")
        response: Response = send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name="checkpoints.zip")
        return response, 200
    
    @app.route("/upload_checkpoints", methods=["POST"])
    # API Route: Upload checkpoints
    def upload_checkpoints() -> Tuple[Response, int]:
        print("Received request to upload checkpoints.")
        message: str
        token: str | None = request.headers.get("token")
        if not token:
            return jsonify({"message": "Token is required."}), 400
        if token != SERVER_TOKEN:
            message = "Invalid token."
            print(message)
            return jsonify({"message": message}), 400
        if "file" not in request.files:
            message = "File is required."
            print(message)
            return jsonify({"message": message}), 400
        file: FileStorage = request.files["file"]
        file_name: None | str = file.filename
        if file_name == "" or file.filename is None:
            message = "File is required."
            print(message)
            return jsonify({"message": message}), 400
        try:
            if not os.path.exists(checkpoints_path):
                os.makedirs(checkpoints_path)
            file_path: str = os.path.join('data', file.filename)
            file.save(file_path)
            print("File saved.")
            print("Extracting checkpoints...")
            with zipfile.ZipFile(file_path, "r") as zip_file:
                zip_file.extractall(checkpoints_path)
            print("Checkpoints extracted.")
            print("Removing uploaded file...")
            os.remove(file_path)
            print("Uploaded file removed.")
            message = "Checkpoints uploaded."
            print(message)
            return jsonify({"message": message}), 200
        except Exception as e:
            message = f"Error uploading checkpoints: {str(e)}"
            print(message)
            return jsonify(
                {"message": message}), 500
    # endregion
