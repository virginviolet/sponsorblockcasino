import hashlib
import time


class Block:
    def __init__(self, index: int, data: str, previous_hash: str):
        self.index = index
        self.timestamp = time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_contents = f"{self.index}{self.timestamp}{
            self.data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_contents.encode()).hexdigest()


class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block(0, "Genesis Block", "0")

    def add_block(self, data: str):
        latest_block = self.chain[-1]
        new_block = Block(len(self.chain), data, latest_block.hash)
        self.chain.append(new_block)


# Create a blockchain and add the genesis block
blockchain = Blockchain()
print(f"Genesis Block:")
print(f"Hash: {blockchain.chain[0].hash}")

# Add a new block
blockchain.add_block("Block 1 data")
print("\nNew Block:")
print(f"Hash: {blockchain.chain[1].hash}")

# print(f"\nBlockchain: {blockchain.chain}")