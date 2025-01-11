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
        block_contents = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_contents.encode()).hexdigest()

# Test: Create a simple test block
block = Block(1, "Test data", "0")
print(f"Block Index: {block.index}")
print(f"Block Data: {block.data}")
print(f"Block Timestamp: {block.timestamp}")
print(f"Previous Hash: {block.previous_hash}")
print(f"Hash: {block.hash}")