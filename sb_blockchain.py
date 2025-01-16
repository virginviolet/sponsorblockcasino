# region Init
import hashlib
from io import TextIOWrapper
from sqlite3.dbapi2 import Timestamp
import time
import os
import json
from flask import Flask, request, jsonify, Response, send_file
from dotenv import load_dotenv
from sys import exit as sys_exit
from typing import Tuple, Dict, List, Any, TypedDict

app = Flask(__name__)
# Load .env file for the server token
load_dotenv()
SERVER_TOKEN: str | None = os.getenv('SERVER_TOKEN')
# endregion

# region Classes


class TransactionDict(TypedDict):
    sender: str
    receiver: str
    amount: int
    method: str

class BlockDict(TypedDict):
    index: int
    timestamp: float
    data: List[str | Dict[str, TransactionDict]]
    previous_hash: str
    nonce: int
    hash: str

class Block:
    def __init__(self,
                 index: int,
                 data: List[str | Dict[str, TransactionDict]],
                 previous_hash: str,
                 timestamp: float = 0.0,
                 nonce: int = 0,
                 block_hash: str | None = None) -> None:
        self.index: int = index
        self.timestamp: float = timestamp if timestamp else time.time()
        self.data: List[str | Dict[str, TransactionDict]] = data
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
    def __init__(self,
                 filename: str = "data/blockchain.json",
                 transactions_filename: str = "data/transactions.tsv") -> None:
        self.filename: str = filename
        self.transactions_filename: str = transactions_filename
        file_exists: bool = os.path.exists(filename)
        file_empty: bool = file_exists and os.stat(filename).st_size == 0
        if not file_exists or file_empty:
            self.create_genesis_block()

    def create_genesis_block(self) -> None:
        # genesis_block = Block(0, "Genesis Block", "0")
        genesis_block = Block(
            0,
            ["Jiraph complained about not being able to access nn block so I "
            "called Jiraph a scraper"],
            "0"
        )
        self.write_block_to_file(genesis_block)

    def write_block_to_file(self, block: Block) -> None:
        # Open the file in append mode
        with open(self.filename, "a") as file:
            # Convert the block object to dictionary, serialize it to JSON, and write it to the file with a newline
            file.write(json.dumps(block.__dict__) + "\n")

    def add_block(
            self,
            data: List[str | Dict[str, TransactionDict]],
            difficulty: int = 0) -> None:
        latest_block: None | Block = self.get_last_block()
        new_block = Block(
            index=(latest_block.index + 1) if latest_block else 0,
            data=data,
            previous_hash=latest_block.hash if latest_block else "0"
        )
        if difficulty > 0:
            new_block.mine_block(difficulty)
        for item in new_block.data:
            if isinstance(item, dict) and "transaction" in item:
                transaction: TransactionDict = item["transaction"]
                self.store_transaction(
                    new_block.timestamp,
                    transaction["sender"],
                    transaction["receiver"],
                    transaction["amount"],
                    transaction["method"]
                )
        self.write_block_to_file(new_block)

    def store_transaction(
            self,
            timestamp: float,
            sender: str,
            receiver: str,
            amount: int,
            method: str) -> None:
        file_existed: bool = os.path.exists(self.transactions_filename)
        if not file_existed:
            self.create_transactions_file()
            
        with open(self.transactions_filename, "a") as file:
            file.write(
                f"{timestamp}\t{sender}\t{receiver}\t{amount}\t{method}\n")

    def create_transactions_file(self) -> None:
        with open(self.transactions_filename, "w") as file:
            file.write("Time\tSender\tReceiver\tAmount\tMethod\n")

    def validate_transactions_file(
            self,
            blockchain_filename: str,
            transactions_filename: str,
            replace: bool = False,
            force: bool = False) -> None:
        def set_bookmark(file: TextIOWrapper,
                            line_number: None | int = None,
                            position: None | int = None) -> int:
            bookmark: int = 0  # Initialize the variable
            if line_number is not None:
                # Store the current position in the file so we can return to it later
                initial_position: int = file.tell()
                for i, _ in enumerate(file):
                    if i == line_number:
                        # Bookmark this position in the file
                        bookmark: int = file.tell()
                        break
                # Return to the initial position in the file
                go_to_bookmark(file, initial_position)
            elif position is not None:
                bookmark = position
            elif position is None and line_number is None:
                # Bookmark the current position in the file
                bookmark: int = file.tell()
            else:
                print("Invalid bookmark creation.")
            return bookmark

        def go_to_bookmark(file: TextIOWrapper, bookmark: int) -> None:
            # Go to the bookmarked position in the file
            file.seek(bookmark)

        def convert_transaction_row_to_list(transaction_tsv: str) -> List[str]:
            return transaction_tsv.split("\t")

        file_existed: bool = os.path.exists(self.transactions_filename)
        if not file_existed:
            self.create_transactions_file()

        with open(self.filename, "r") as blockchain_file:
            validation_failed: bool = False
            with open(self.transactions_filename, "r") as transactions_file:
                bookmark: None | int = None
                for line in blockchain_file:
                    block_dict: (BlockDict) = json.loads(line)
                    data_list: List[str | Dict[str, TransactionDict]] = block_dict["data"]
                    for item in data_list:
                        if isinstance(item, dict) and "transaction" in item:
                            blockchain_transaction: TransactionDict = item["transaction"]
                            blockchain_timestamp: float = block_dict["timestamp"]
                            if bookmark is None:
                                # The first line of the transactions file
                                # contains the column headers
                                # Create a bookmark at the second line
                                bookmark = set_bookmark(
                                    file=transactions_file,
                                    line_number=1)
                                if force:
                                    # This will cause the whole file to be replaced
                                    bookmark = set_bookmark(
                                        transactions_file, line_number=1)
                                    # Clear the file from the second line
                                    transactions_file.truncate()
                            go_to_bookmark(transactions_file, bookmark)
                            transaction_tsv_row: str = transactions_file.readline().strip()
                            transaction_tsv_row_list: List[str] = convert_transaction_row_to_list(transaction_tsv_row)
                            columns: int = len(transaction_tsv_row_list)
                            if columns != 5:
                                print("Invalid transaction format.")
                                validation_failed = True
                            else:
                                transaction_tsv_time = float(transaction_tsv_row_list[0])
                                transaction_tsv_sender: str = transaction_tsv_row_list[1]
                                transaction_tsv_receiver: str = transaction_tsv_row_list[2]
                                transaction_tsv_amount: int = int(transaction_tsv_row_list[3])
                                transaction_tsv_method: str = transaction_tsv_row_list[4]
                            
                                # Check if the transaction in the blockchain matches the transaction in the file
                                if (blockchain_timestamp == transaction_tsv_time and
                                    blockchain_transaction["sender"] == transaction_tsv_sender and
                                    blockchain_transaction["receiver"] == transaction_tsv_receiver and
                                    blockchain_transaction["amount"] == transaction_tsv_amount and
                                    blockchain_transaction["method"] == transaction_tsv_method):
                                    print("Transaction matches.")
                                else: 
                                    print("Transaction not found. The transactions "
                                          "file does not reflect the blockchain.")
                                    validation_failed = True
                            if validation_failed and replace:
                                print("Contents of the transactions file will be "
                                      "replaced.")
                                # Clear the file from bookmark to end
                                transactions_file.truncate()
                                self.store_transaction(
                                    block_dict["timestamp"],
                                    blockchain_transaction["sender"],
                                    blockchain_transaction["receiver"],
                                    blockchain_transaction["amount"],
                                    blockchain_transaction["method"]
                                )
                            
                            # Move the bookmark to the the end of the file
                            set_bookmark(
                                file=transactions_file,
                                position=os.SEEK_END)

    def get_chain_length(self) -> int:
        # Open the blockchain file in read binary mode (faster than normal read)
        with open(self.filename, "rb") as file:
            # Count the number of lines and return the count
            return sum(1 for _ in file)

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

    data: str | List[Dict[str, Dict[str, str]]
                     ] = request.get_json().get("data")
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
    
@app.route("/download_chain", methods=["GET"])
# API Route: Download the blockchain
def download_chain() -> Tuple[Response | Any, int]:
    file_exists: bool = os.path.exists(blockchain.filename)
    if not file_exists:
        return jsonify({"message": "No blockchain found."}), 404
    else:
        return send_file(blockchain.filename, as_attachment=True), 200


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
    # app.run(port=8080, debug=True)
    blockchain = Blockchain()
    # blockchain.validate_transactions_file(
    #     blockchain_filename=blockchain.filename,
    #     transactions_filename=blockchain.transactions_filename,
        # replace=True,
        # force=True
    blockchain.is_chain_valid()
# endregion
