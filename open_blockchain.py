# region Init
import hashlib
import time
from flask import Flask, request, jsonify, Response
from typing import Tuple, Dict

app = Flask(__name__)
# endregion

# region Classes


class Block:
    def __init__(self, index: int, data: str, previous_hash: str) -> None:
        self.index: int = index
        self.timestamp: float = time.time()
        self.data: str = data
        self.previous_hash: str = previous_hash
        self.nonce = 0
        self.hash: str = self.calculate_hash()

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
    def __init__(self) -> None:
        self.chain: list[Block] = [self.create_genesis_block()]

    def create_genesis_block(self) -> Block:
        return Block(0, "Genesis Block", "0")

    def add_block(self, data: str, difficulty: int = 0) -> None:
        latest_block: Block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            data=data,
            previous_hash=latest_block.hash
        )
        if difficulty > 0:
            new_block.mine_block(difficulty)
        self.chain.append(new_block)

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block: Block = self.chain[i]
            calculated_hash = current_block.calculate_hash()
            print(f"\nCurrent Block Hash: {current_block.hash}")
            print(f"Calculated Hash: {calculated_hash}")
            if current_block.hash != calculated_hash:
                print(f"Block {i} hash does not match calculated hash.")
                print("The blockchain is not valid.")
                return False
            else:
                print(f"Block {i} hash matches calculated hash.")
            previous_block: Block = self.chain[i - 1]
            print(f"Previous Block Hash: {previous_block.hash}")
            print(f"Current Block Previous Hash: {
                  current_block.previous_hash}")
            if current_block.previous_hash != previous_block.hash:
                print(
                    f"Block {i} previous hash does not match previous block's hash.")
                print("The blockchain is not valid.")
                return False
            else:
                print(
                    f"Block {i} previous hash matches previous block's hash.")
        print("The blockchain is valid.")
        return True
# endregion


# region Init blockchain
blockchain = Blockchain()
# endregion


# region API Routes


@app.route("/add_block", methods=["POST"])
# API Route: Add a new block to the blockchain
def add_block() -> Tuple[Response, int]:
    data: str = request.get_json().get("data")
    if not data:
        return jsonify({"message": "Data is required."}), 400

    blockchain.add_block(data)
    return jsonify({"message": "Block added successfully.",
                    "block": blockchain.chain[-1].__dict__}), 200


@app.route("/get_chain", methods=["GET"])
# API Route: Get the blockchain
def get_chain() -> Tuple[Response, int]:
    chain_data: list[dict[str, str]] = [
        block.__dict__ for block in blockchain.chain]
    return jsonify({"length": len(chain_data), "chain": chain_data}), 200


@app.route("/validate_chain", methods=["GET"])
# API Route: Validate the blockchain
def validate_chain() -> Tuple[Response | Dict[str, str], int]:
    is_valid: bool = blockchain.is_chain_valid()
    return jsonify({"message": "The blockchain is valid." if is_valid else
                    "The blockchain is not valid."}), 200
# endregion


# region Run Flask app
if __name__ == "__main__":
    app.run(port=5000, debug=True)
# endregion
