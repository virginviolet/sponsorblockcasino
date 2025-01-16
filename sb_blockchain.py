# region Init
import hashlib
import time
import os
import json
from flask import Flask, request, jsonify, Response, send_file
from dotenv import load_dotenv
from sys import exit as sys_exit
from typing import Tuple, Dict, List, Any

app = Flask(__name__)
# Load .env file for the server token
load_dotenv()
SERVER_TOKEN: str | None = os.getenv('SERVER_TOKEN')
# endregion

# region Classes


class Block:
    def __init__(self, index: int, data: str | List[Dict[str, Dict[str, str]]], previous_hash: str, timestamp: float = 0.0, nonce: int = 0, block_hash: str | None = None) -> None:
        self.index: int = index
        self.timestamp: float = timestamp if timestamp else time.time()
        self.data: str | List[Dict[str, Dict[str, str]]] = data
        self.previous_hash: str = previous_hash
        self.nonce = nonce
        self.hash: str = block_hash if block_hash else self.calculate_hash()

    def calculate_hash(self) -> str:
        block_contents: str = f"{self.index}{self.timestamp}{
            self.data}{self.previous_hash}{self.nonce}"
        hash_string: str = hashlib.sha256(block_contents.encode()).hexdigest()
        # print(f"Hash: {hash_string}")
        return hash_string

    def mine_block(self, difficulty: int) -> None:
        target: str = "0" * difficulty  # Create a string of zeros
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()


class Blockchain:
    def __init__(self, filename: str = "data/blockchain.json", transactions_filename: str = "data/transactions.tsv") -> None:
        self.filename: str = filename
        self.transactions_filename: str = transactions_filename
        file_exists: bool = os.path.exists(filename)
        file_empty: bool = file_exists and os.stat(filename).st_size == 0
        if not file_exists or file_empty:
            self.create_genesis_block()

    def create_genesis_block(self) -> None:
        genesis_block = Block(0, "Genesis Block", "0")
        self.write_block_to_file(genesis_block)

    def write_block_to_file(self, block: Block) -> None:
        # Open the file in append mode
        with open(self.filename, "a") as file:
            # Convert the block object to dictionary, serialize it to JSON, and write it to the file with a newline
            file.write(json.dumps(block.__dict__) + "\n")

    def add_block(self, data: str | List[Dict[str, Dict[str,str]]], difficulty: int = 0) -> None:
        latest_block: None | Block = self.get_last_block()
        new_block = Block(
            index=(latest_block.index + 1) if latest_block else 0,
            data=data,
            previous_hash=latest_block.hash if latest_block else "0"
        )
        if difficulty > 0:
            new_block.mine_block(difficulty)
        if isinstance(new_block.data, list) and "transaction" in new_block.data[0]:
            self.store_transaction(new_block.data, new_block.timestamp)
        self.write_block_to_file(new_block)

    def store_transaction(self, data: List[Dict[str, Dict[str, str]]], timestamp: float) -> None:
        time: float = timestamp
        sender: str = data[0]["transaction"]["sender"]
        receiver: str = data[0]["transaction"]["receiver"]
        amount: str = data[0]["transaction"]["amount"]
        method: str = data[0]["transaction"]["method"]
        file_existed: bool = os.path.exists(self.transactions_filename)
        with open(self.transactions_filename, "a") as file:
            if not file_existed:
                file.write("Time\tSender\tReceiver\tAmount\tMethod\n")
            file.write(f"{time}\t{sender}\t{receiver}\t{amount}\t{method}\n")

    def get_last_block(self) -> None | Block:
        if not os.path.exists(self.filename):
            return None
        # Get the last line of the file
        with open(self.filename, "rb") as file:
            # Go to the second last byte
            file.seek(-2, os.SEEK_END)
            try:
                # Seek backwards until a newline is found
                # Move one byte at a time
                while file.read(1) != b"\n":
                    # Look two bytes back
                    file.seek(-2, os.SEEK_CUR)
            except OSError:
                # Move to the start of the file if for example no newline is found
                file.seek(0)
            last_line: str = file.readline().decode()

        for block_key in [json.loads(last_line)]:
            return Block(
                index=block_key["index"],
                timestamp=block_key["timestamp"],
                data=block_key["data"],
                previous_hash=block_key["previous_hash"],
                nonce=block_key["nonce"],
                block_hash=block_key["hash"]
            )

    def is_chain_valid(self) -> bool:
        chain_validity = True
        if not os.path.exists(self.filename):
            chain_validity = False
        else:
            current_block: None | Block = None
            previous_block: None | Block = None
            # Open the blockchain file
            with open(self.filename, "r") as file:
                for line in file:
                    if current_block:
                        previous_block = current_block
                    # Deserialize the line's JSON data to a dictionary
                    current_line_json: Dict[str, Any] = json.loads(line)
                    # Create a new block object from the dictionary
                    current_block = Block(
                        index=current_line_json["index"],
                        timestamp=current_line_json["timestamp"],
                        data=current_line_json["data"],
                        previous_hash=current_line_json["previous_hash"],
                        nonce=current_line_json["nonce"],
                        block_hash=current_line_json["hash"]
                    )
                    del current_line_json  # Free up a small amount of memory
                    # Calculate the hash of the current block
                    calculated_hash: str = current_block.calculate_hash()
                    print(f"\nCurrent block's \"Hash\": {current_block.hash}")
                    print(f"Calculated hash:\t{calculated_hash}")
                    if current_block.hash != calculated_hash:
                        print(f"Block {current_block.index}'s hash does not match the calculated "
                              "hash. This could mean that a block has been tampered with.")
                        chain_validity = False
                        break
                    else:
                        print(f"Block {current_block.index}'s hash matches "
                              "the calculated hash.")
                    if previous_block:
                        print(f"\nPrevious block's hash:\t\t\t{
                              previous_block.hash}")
                        print(f"Current block's \"Previous Hash\":\t{
                            current_block.previous_hash}")
                        if current_block.previous_hash != previous_block.hash:
                            print(f"Block {current_block.index} \"Previous Hash\" value does not "
                                  "match the previous block's hash. This could mean that a block is "
                                  "missing or that one has been incorrectly inserted.")
                            chain_validity = False
                            break
                        else:
                            print(f"Block {current_block.index}  \"Previous Hash\" value matches "
                                  "the previous block's hash.")
        if chain_validity:
            print("The blockchain is valid.")
            return True
        else:
            print("The blockchain is invalid.")
            return False
# endregion


# region Init blockchain
blockchain = Blockchain()
# endregion


# region API Routes


@app.route("/add_block", methods=["POST"])
# API Route: Add a new block to the blockchain
def add_block() -> Tuple[Response, int]:
    token: str | None = request.headers.get("token")
    if not token:
        return jsonify({"message": "Token is required."}), 400
    if token != SERVER_TOKEN:
        return jsonify({"message": "Invalid token."}), 400
    
    data: str | List[Dict[str, Dict[str,str]]] = request.get_json().get("data")
    if not data:
        return jsonify({"message": "Data is required."}), 400

    blockchain.add_block(data)
    try:
        last_block: None | Block = blockchain.get_last_block()
        if last_block and last_block.data != data:
            return jsonify({"message": "Block could not be added."}), 500
        else:
            return jsonify({"message": "Block added successfully.",
                            "block": last_block.__dict__}), 200
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "An error occurred."}), 500


@app.route("/get_chain", methods=["GET"])
# API Route: Get the blockchain
def get_chain() -> Tuple[Response, int]:
    print("Retrieving blockchain...")
    with open(blockchain.filename, "r") as file:
        chain_data: list[dict[str, Any]] = [
            json.loads(line) for line in file.readlines()]
        print("Blockchain retrieved.")
        return jsonify({"length": len(chain_data), "chain": chain_data}), 200


@app.route("/get_last_block", methods=["GET"])
# API Route: Get the last block of the blockchain
def get_last_block() -> Tuple[Response, int]:
    last_block: None | Block = blockchain.get_last_block()
    if last_block:
        return jsonify({"block": last_block.__dict__}), 200
    else:
        return jsonify({"message": "No blocks found."}), 404


@app.route("/validate_chain", methods=["GET"])
# API Route: Validate the blockchain
def validate_chain() -> Tuple[Response | Dict[str, str], int]:
    is_valid: bool = blockchain.is_chain_valid()
    return jsonify({"message": "The blockchain is valid." if is_valid else
                    "The blockchain is not valid."}), 200

@app.route("/shutdown", methods=["POST"])
# API Route: Shutdown the Flask app
def shutdown() -> Tuple[Response, int]:
    try:
        token: str | None = request.headers.get("token")
        if not token:
            return jsonify({"message": "Token is required."}), 400
        if token != SERVER_TOKEN:
            return jsonify({"message": f"Invalid token."}), 400
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "An error occurred."}), 500

    print("The blockchain app will now exit.")
    sys_exit(0)

@app.route("/transactions", methods=["GET"])
# API Route: Download the transactions file
def download_transactions() -> Tuple[Response | Any, int]:
    file_exists: bool = os.path.exists(blockchain.transactions_filename)
    if not file_exists:
        return jsonify({"message": "No transactions found."}), 404
    else:
        return send_file(blockchain.transactions_filename, as_attachment=True), 200
# endregion


# region Run Flask app
if __name__ == "__main__":
    app.run(port=8080, debug=True)
# endregion
