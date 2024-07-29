from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This allows cross-origin requests, which is necessary when running React and Flask on different ports.

@app.route('/api/button1', methods=['POST'])
def button1_function():
    response = {'message': 'Button 1 was clicked!'}
    return jsonify(response)

@app.route('/api/button2', methods=['POST'])
def button2_function():
    response = {'message': 'Button 2 was clicked!'}
    return jsonify(response)

@app.route('/api/button3', methods=['POST'])
def button3_function():
    response = {'message': 'Button 3 was clicked!'}
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
