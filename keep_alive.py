from threading import Thread

from flask import Flask

app = Flask("")

@app.route('/')
def home():
    return "Your bot is running!"

def run():
    app.run(host="0.0.0.0", port=8000)

def keep_alive():
    server = Thread(target=run)
    server.start()
