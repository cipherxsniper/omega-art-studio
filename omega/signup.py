from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json

    return jsonify({
        "status": "success",
        "lead": data,
        "message": "Stripe checkout initiated"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
