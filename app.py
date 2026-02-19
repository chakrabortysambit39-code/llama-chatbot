from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sambit Chatbot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { box-sizing: border-box; }

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #0f172a;
                color: white;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }

            .header {
                padding: 15px;
                background: #111827;
                text-align: center;
                font-size: 20px;
                font-weight: bold;
            }

            .messages {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }

            .user {
                align-self: flex-end;
                background: #2563eb;
                padding: 10px 14px;
                border-radius: 12px;
                margin: 6px 0;
                max-width: 70%;
            }

            .bot {
                align-self: flex-start;
                background: #1f2937;
                padding: 10px 14px;
                border-radius: 12px;
                margin: 6px 0;
                max-width: 70%;
            }

            .input-area {
                display: flex;
                padding: 10px;
                background: #111827;
            }

            input {
                flex: 1;
                padding: 12px;
                border-radius: 8px;
                border: none;
                outline: none;
                font-size: 16px;
            }

            button {
                margin-left: 10px;
                padding: 12px 20px;
                border-radius: 8px;
                border: none;
                background: #2563eb;
                color: white;
                font-size: 16px;
                cursor: pointer;
            }

            button:hover {
                background: #1d4ed8;
            }
        </style>
    </head>
    <body>

        <div class="header">Sambit Chatbot</div>

        <div class="messages" id="messages"></div>

        <div class="input-area">
            <input id="input" placeholder="Ask me anything..." />
            <button onclick="sendMessage()">Send</button>
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
                })
                .catch(() => {
                    messages.innerHTML += `<div class="bot">Server connection error.</div>`;
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
        return jsonify({"reply": "API key not configured on server."})

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": user_msg}
        ]
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        data = response.json()

        if "choices" in data:
            reply = data["choices"][0]["message"]["content"]
        else:
            reply = f"API Error: {data}"

    except Exception as e:
        reply = f"Server Error: {str(e)}"

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
