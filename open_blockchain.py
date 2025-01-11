from flask import Flask, request, jsonify
from typing import List

app = Flask(__name__)
database: List[str] = []


@app.route('/add_entry', methods=['POST'])
def add_entry():
    data = request.get_json().get("data")
    if not data:
        return jsonify({"error": "No data provided."}), 400

    database.append(data)  # Add the data to our simple list
    return jsonify({"message": "Data added!", "data": data}), 200


@app.route('/get_database', methods=['Get'])
def get_database():
    return jsonify({"entries": database, "count": len(database)}), 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)
