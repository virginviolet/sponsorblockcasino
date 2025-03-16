# region Imports
# Standard library
import os
import json
import zipfile
import shutil
from io import BytesIO
from pathlib import Path
from typing import Tuple

# Third party
from flask import Flask, request, jsonify, Response, send_file
from dotenv import load_dotenv

# Local
from type_aliases import SlotMachineConfig, BotConfig
from utils.decrypt_transactions import (
    DecryptedTransactionsSpreadsheet)
from utils.get_project_root import get_project_root
# endregion

# region Constants
# Load .env file for the server token
load_dotenv()
SERVER_TOKEN: str | None = os.getenv('SERVER_TOKEN')
# FIXME Set path in global_state?
project_root_path: Path = get_project_root()

slot_machine_config_full_path: Path = (
    project_root_path / "data" / "slot_machine.json")

slot_machine_config_path: Path = (
    slot_machine_config_full_path.relative_to(project_root_path))

bot_config_full_path: Path = (
    project_root_path / "data" / "bot_configuration.json")

bot_config_path: Path = (
    bot_config_full_path.relative_to(project_root_path))

checkpoints_dir_full_path: Path = (
    project_root_path / "data" / "checkpoints")

checkpoints_dir_path: Path = (
    checkpoints_dir_full_path.relative_to(project_root_path))

save_data_dir_full_path: Path = (
    project_root_path / "data" / "save_data")

save_data_dir_path: Path = (
    save_data_dir_full_path.relative_to(project_root_path))

decrypted_transactions_path: Path = project_root_path / "data" / "transactions_decrypted.tsv"
decrypted_transactions_spreadsheet = DecryptedTransactionsSpreadsheet()
# endregion

# region Functions


def save_slot_config(config: SlotMachineConfig) -> None:
    file_name: Path = slot_machine_config_path
    file_exists: bool = os.path.exists(file_name)
    file_empty: bool = file_exists and os.stat(
        file_name).st_size == 0
    if not file_exists or file_empty:
        directories: Path = file_name.parent
        os.makedirs(directories, exist_ok=True)
    with open(file_name, "w") as file:
        file.write(json.dumps(config))


def save_bot_config(config: BotConfig) -> None:
    file_name: Path = bot_config_path
    file_exists: bool = os.path.exists(file_name)
    file_empty: bool = file_exists and os.stat(
        file_name).st_size == 0
    if not file_exists or file_empty:
        directories: Path = file_name.parent
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
            return jsonify({"message": message}), 500

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
            return jsonify({"message": message}), 500

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
        if not os.path.exists(checkpoints_dir_path):
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
                for root, _, files in os.walk(checkpoints_dir_path):
                    for file in files:
                        zip_file_path: str = os.path.join(root, file)
                        zip_file.write(zip_file_path)
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
        file_content: bytes = request.data
        try:
            if not os.path.exists(checkpoints_dir_path):
                os.makedirs(checkpoints_dir_path)
            file_path: str = 'checkpoints.zip'
            with open(file_path, "wb") as file:
                file.write(file_content)
            print("File saved.")
            print("Extracting checkpoints...")
            checkpoints_parent_path: Path = Path(checkpoints_dir_path).parent
            checkpoints_parent_path_str: str = str(checkpoints_parent_path)
            with zipfile.ZipFile(file_path, "r") as zip_file:
                zip_file.extractall(checkpoints_parent_path_str)
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
            return jsonify({"message": message}), 500

    @app.route("/delete_checkpoints", methods=["DELETE"])
    # API Route: Delete checkpoints
    def delete_checkpoints() -> Tuple[Response, int]:
        print("Received request to delete checkpoints.")
        message: str
        token: str | None = request.headers.get("token")
        if not token:
            return jsonify({"message": "Token is required."}), 400
        if token != SERVER_TOKEN:
            message = "Invalid token."
            print(message)
            return jsonify({"message": message}), 400
        try:
            if os.path.exists(checkpoints_dir_path):
                print("Deleting checkpoints...")
                shutil.rmtree(checkpoints_dir_path)
                print("Checkpoints deleted.")
            message = "Checkpoints deleted."
            print(message)
            return jsonify({"message": message}), 200
        except Exception as e:
            message = f"Error deleting checkpoints: {str(e)}"
            print(message)
            return jsonify(
                {"message": message}), 500

    @app.route("/download_save_data", methods=["GET"])
    # API Route: Download the save data
    def download_save_data() -> Tuple[Response, int]:
        print("Received request to download save data.")
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
        try:
            # Easier to store the file in memory than to add threading to remove
            # the file after the response is sent
            print("Creating zip file in memory...")
            memory_file = BytesIO()
            with zipfile.ZipFile(
                    memory_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for root, _, files in os.walk(save_data_dir_path):
                    for file in files:
                        zip_file_path: str = os.path.join(root, file)
                        zip_file.write(zip_file_path)
            print("Zip file created in memory.")
            print("Save data will be sent.")
            memory_file.seek(0)
            return send_file(
                memory_file,
                mimetype="application/zip",
                as_attachment=True,
                download_name="save_data.zip"), 200
        except Exception as e:
            message = f"Error downloading save data: {str(e)}"
            print(message)
            return jsonify({"message": message}), 500

    @app.route("/upload_save_data", methods=["POST"])
    # API Route: Upload save data
    def upload_save_data() -> Tuple[Response, int]:
        print("Received request to upload save data.")
        message: str
        token: str | None = request.headers.get("token")
        if not token:
            return jsonify({"message": "Token is required."}), 400
        if token != SERVER_TOKEN:
            message = "Invalid token."
            print(message)
            return jsonify({"message": message}), 400
        file_content: bytes = request.data
        try:
            if not os.path.exists(save_data_dir_path):
                os.makedirs(save_data_dir_path)
            file_path: str = 'save_data.zip'
            with open(file_path, "wb") as file:
                file.write(file_content)
            print("File saved.")
            print("Extracting save data...")
            save_data_parent_path: Path = Path(save_data_dir_path).parent
            save_data_parent_path_str: str = str(save_data_parent_path)
            with zipfile.ZipFile(file_path, "r") as zip_file:
                zip_file.extractall(save_data_parent_path_str)
            print("Save data extracted.")
            print("Removing uploaded file...")
            os.remove(file_path)
            print("Uploaded file removed.")
            message = "Save data uploaded."
            print(message)
            return jsonify({"message": message}), 200
        except Exception as e:
            message = f"Error uploading save data: {str(e)}"
            print(message)
            return jsonify({"message": message}), 500

    @app.route("/download_transactions_decrypted", methods=["GET"])
    # API Route: Download the decrypted transactions
    def download_transactions_decrypted() -> Tuple[Response, int]:
        print("Received request to download decrypted transactions.")
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
        try:
            file_exists: bool = os.path.exists(decrypted_transactions_path)
            if not file_exists:
                message = "Decrypted transactions not found."
                print(message)
                return jsonify({"message": message}), 404
            decrypted_transactions_spreadsheet.decrypt()
            print("Decrypted transactions will be sent.")
            return send_file(
                decrypted_transactions_path,
                mimetype="text/tab-separated-values",
                as_attachment=True), 200
        except Exception as e:
            message = f"Error downloading decrypted transactions: {str(e)}"
            print(message)
            return jsonify({"message": message}), 500

    # endregion
