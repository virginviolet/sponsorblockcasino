# region Imports
# Standard Library
import os
import json
from sys import exit as sys_exit
from typing import Tuple, Dict, List, Any

# Third party
from flask import Flask, request, jsonify, Response, send_file
from dotenv import load_dotenv

# Local
import blockchain.extensions.discord_coin_bot_extension \
    as discord_coin_bot_extension
from blockchain.sbchain_type_aliases import TransactionDict
from blockchain.models.block import Block
from blockchain.models.blockchain import Blockchain
# endregion

# region Init
app = Flask(__name__)
# Load .env file for the server token
load_dotenv()
SERVER_TOKEN: str | None = os.getenv('SERVER_TOKEN')
# Register the API routes from extension
discord_coin_bot_extension.register_routes(app)
# endregion

# region Start chain
blockchain = Blockchain()

# endregion


# region API Routes


@app.route("/add_block", methods=["POST"])
# API Route: Add a new block to the blockchain
def add_block() -> Tuple[Response, int]:
    print("Received request to add a block.")
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
        request_data: Any = request.get_json()
    except Exception as e:
        message = f"Request data could not be retrieved: {e}"
        print(message)
        return jsonify({"message": message}), 400
    print(f"Request: {request.get_json()}")
    if "data" not in request_data:
        message = "'data' key not found in request."
        print(message)
        return jsonify({"message": message}), 400
    data = request.get_json().get("data")
    if not data:
        message = "The 'data' key is empty."
        print(message)
        return jsonify({"message": message}), 400
    # IMPROVE Make data a named tuple?
    if not isinstance(data, list) and (
            all(isinstance(item, (str, dict)) for item in data)):
        message = "Data must be a list of strings or dictionaries."
        print(message)
        return jsonify({"message": message}), 400
    data_cast: List[str | Dict[str, TransactionDict]] = data

    try:
        blockchain.add_block(data_cast)
        last_block: None | Block = blockchain.get_last_block()
        if last_block and last_block.data != data:
            message = "Block could not be added."
            print(message)
            return jsonify({"message": message}), 500
        else:
            message = "Block added successfully."
            print(message)
            return jsonify({"message": message,
                            "block": last_block.__dict__}), 200
    except Exception as e:
        message = f"An error occurred: {e}"
        print(message)
        return jsonify({"message": message}), 500


@app.route("/get_chain", methods=["GET"])
# API Route: Get the blockchain
def get_chain() -> Tuple[Response, int]:
    print("Received request to get the blockchain.")
    print("Retrieving blockchain...")
    with open(blockchain.blockchain_file_name, "r") as file:
        chain_data: list[dict[str, Any]] = [
            json.loads(line) for line in file.readlines()]
        print("Blockchain retrieved.")
        print("Blockchain will be returned.")
        return jsonify({"length": len(chain_data), "chain": chain_data}), 200


@app.route("/download_chain", methods=["GET"])
# API Route: Download the blockchain
def download_chain() -> Tuple[Response | Any, int]:
    print("Received request to download the blockchain.")
    file_exists: bool = os.path.exists(blockchain.blockchain_file_name)
    if not file_exists:
        message = "No blockchain found."
        print(message)
        return jsonify({"message": message}), 404
    else:
        print("Blockchain will be sent as a file.")
        return send_file(
            blockchain.blockchain_file_name,
            as_attachment=True), 200


@app.route("/get_last_block", methods=["GET"])
# API Route: Get the last block of the blockchain
def get_last_block() -> Tuple[Response, int]:
    print("Received request to get the last block.")
    last_block: None | Block = blockchain.get_last_block()
    if last_block:
        print("Last block found.")
        print("Last block will be returned.")
        return jsonify({"block": last_block.__dict__}), 200
    else:
        message = "No blocks found."
        print(message)
        return jsonify({"message": message}), 404


@app.route("/validate_chain", methods=["GET"])
# API Route: Validate the blockchain
def validate_chain() -> Tuple[Response | Dict[str, str], int]:
    print("Received request to validate the blockchain.")
    is_valid: bool = blockchain.is_chain_valid()
    message: str = "The blockchain is valid." if is_valid else (
        "The blockchain is not valid.")
    print(message)
    return jsonify({"message": message}), 200


@app.route("/validate_transactions", methods=["GET"])
# API Route: Validate the blockchain
def validate_transactions() -> Tuple[Response | Dict[str, str], int]:
    token: str | None = request.headers.get("token")
    repair: bool = request.args.get("repair", "false").lower() == "true"
    force: bool = request.args.get("force", "false").lower() == "true"
    message: str
    is_valid: bool
    if token:
        message, is_valid = blockchain.is_transactions_file_valid(
            repair, force)
    else:
        message, is_valid = blockchain.is_transactions_file_valid(force)

    return jsonify({"message": message}), 200 if is_valid else 400


@app.route("/shutdown", methods=["POST"])
# API Route: Shutdown the Flask app
def shutdown() -> Tuple[Response, int]:
    print("Received request to shutdown the blockchain app.")
    try:
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
    except Exception as e:
        message = f"An error occurred: {e}"
        print(message)
        return jsonify({"message": message}), 500

    print("The blockchain app will now exit.")
    sys_exit(0)


@app.route("/download_transactions", methods=["GET"])
# API Route: Download the transactions file
def download_transactions() -> Tuple[Response | Any, int]:
    print("Received request to download the transactions file.")
    file_exists: bool = os.path.exists(blockchain.transactions_file_name)
    if not file_exists:
        message = "No transactions found."
        print(message)
        return jsonify({"message": message}), 404
    else:
        print("Transactions file will be sent as a file.")
        return send_file(
            blockchain.transactions_file_name,
            as_attachment=True), 200


@app.route("/get_balance", methods=["GET"])
# API Route: Get the balance of a user
def get_balance() -> Tuple[Response, int]:
    print("Received request to get balance for a user.")
    user: str | None = request.args.get(str("user"))
    user_unhashed: str | None = request.args.get("user_unhashed")
    message: str

    # Debugging: Print the received query parameters
    print(f"Received user: {user}")
    print(f"Received user_unhashed: {user_unhashed}")

    if not user and not user_unhashed:
        message = "User or user_unhashed is required."
        print(message)
        return jsonify({"message": message}), 400
    elif user and user_unhashed:
        message = "Only one of user or user_unhashed is allowed."
        print(message)
        return jsonify({"message": message}), 400

    # Validate the transactions file
    blockchain.is_transactions_file_valid()

    # Retrieve the balance
    if user:
        balance: int | None = blockchain.get_balance(user=user)
    else:
        balance: int | None = blockchain.get_balance(
            user_unhashed=user_unhashed)

    # Debugging: Print the retrieved balance
    print(f"Retrieved balance: {balance}")

    # Return the balance or an error message
    if balance is not None:
        # Convert to int64 to int for JSON serialization
        balance = int(balance)
        print("Balance will be returned.")
        return jsonify({"balance": balance}), 200
    else:
        message = "No transactions found for user."
        print(message)
        return jsonify({"message": message}), 404
# endregion


# region Run Flask app
if __name__ == "__main__":
    app.run(port=8080, debug=True)
# endregion
