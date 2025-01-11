import hashlib
import time
from typing import LiteralString


class Block:
    def __init__(self, index: int, data: str, previous_hash: str) -> None:
        self.index: int = index
        self.timestamp: float = time.time()
        self.data: str = data
        self.previous_hash: str = previous_hash
        self.nonce = 0
        self.hash: str = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_contents: str = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.nonce}"
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
        new_block = Block(len(self.chain), data, latest_block.hash)
        if difficulty > 0:
            new_block.mine_block(difficulty)
        self.chain.append(new_block)


# Create a blockchain and add the genesis block
blockchain = Blockchain()
print(f"Genesis Block:")
print(f"Hash: {blockchain.chain[0].hash}")

# Add a new block without mining
blockchain.add_block("Block 1 data")
print("\nNew Block:")
print(f"Hash: {blockchain.chain[1].hash}")

# Mine a block
block = Block(index=1, data="Mining test data", previous_hash="0")
difficulty = 4
print(f"\nMining block with difficulty {difficulty}...")
block.mine_block(difficulty=difficulty)
print(f"Block mined. Hash: {block.hash}")
print(f"Nonce: {block.nonce}")

# A new block to the blockchain with mining
difficulty = 4
print(f"\nMining a block to the blockchain with difficulty {difficulty}...")
blockchain.add_block("Blockchain mining test data", difficulty=difficulty)
print(f"Block mined. Hash: {blockchain.chain[2].hash}")
print(f"Nonce: {blockchain.chain[2].nonce}")