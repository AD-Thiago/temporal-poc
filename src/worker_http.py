from flask import Flask, request, jsonify
import base64
import os

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    return "OK", 200


@app.route("/pubsub/push", methods=["POST"])
def pubsub_push():
    # Pub/Sub push delivers a JSON body with 'message' field
    envelope = request.get_json()
    if not envelope:
        return ("Bad Request: no JSON body", 400)

    message = envelope.get("message")
    if not message:
        return ("Bad Request: no message field", 400)

    data = message.get("data")
    if data:
        payload = base64.b64decode(data).decode("utf-8")
    else:
        payload = ""

    # Here you would process the payload
    print("Received Pub/Sub message:", payload)

    # Acknowledge by returning 200
    return (jsonify({"status": "processed", "payload": payload}), 200)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
