#!python3
import random
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def hello():
    message = 'esta api contém somente o endpoint "/random_number"'
    return jsonify({'message': message})

@app.route('/random_number')
def random_number():
    number = random.randint(1, 99)
    return jsonify({'data': number})

if __name__ == "__main__":
    app.run(host='0.0.0.0')
