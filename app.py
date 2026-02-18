from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Get API key securely from environment variable
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Llama 3 Chatbot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial; background:#f2f2f2; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
            .chat { background:white; width:100%; max-width:400px; height:520px; display:flex; flex-direction:column; border-radius:10px; overflow:hidden; }
            .header { background:black; color:white; padding:10px; text-align:center; }
            .messages { flex:1; padding:10px; overflow-y:auto; }
            .user { text-align:right; color:blue; margin:5px 0; }
            .bot { text-align:left; color:green; margin:5px 0; }
            .input { display:flex; border-top:1px solid #ddd; }
            input { flex:1; padding:10px; border:none; outline:none; }
            button { padding:10px; border:none; background:black; color:white; }
        </style>
    </head>
    <body>
        <div class="chat">
            <div class="header">Llama 3 Chatbot</div>
            <div class="messages" id="messages"></div>
            <div class="input">
                <input id="input" placeholder="Ask something..." />
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>

        <script>
            function sendMessage() {
                const input = document.getElementById("input");
                const message = input.value.trim();
                if (!message) return;

                const messages = document.getElementById("messages");
                messages.innerHTML += `<div class="user">${message}</div>`;
                input.value = "";
                messages.scrollTop = messages.scrollHeight;

                fetch("/chat", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({message: message})
                })
                .then(res => res.json())
                .then(data => {
                    messages.innerHTML += `<div class="bot">${data.reply}</div>`;
                    messages.scrollTop = messages.scrollHeight;
                });
            }

            document.getElementById("input").addEventListener("keydown", function(e) {
                if (e.key === "Enter") {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message", "")

    if not GROQ_API_KEY:
        return jsonify({"reply": "Server error: API key not configured."})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "user", "content": user_msg}
        ]
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )

    data = response.json()

    try:
        reply = data["choices"][0]["message"]["content"]
    except:
        reply = "Error getting response from AI."

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
