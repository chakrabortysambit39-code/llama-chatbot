from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>Sambit Chatbot</title>

<style>

body{
font-family:Arial;
background:#0f172a;
color:white;
text-align:center;
padding:20px;
}

#chatbox{
height:400px;
overflow:auto;
border:1px solid #334155;
padding:10px;
background:#020617;
margin-bottom:10px;
}

input{
width:60%;
padding:10px;
border-radius:5px;
border:none;
}

button{
padding:10px 15px;
margin:5px;
border:none;
border-radius:5px;
background:#38bdf8;
cursor:pointer;
}

</style>

</head>

<body>

<h1>🤖 Sambit Chatbot</h1>

<div id="chatbox"></div>

<input id="message" placeholder="Type message">

<button onclick="sendMessage()">Send</button>

<script>

async function sendMessage(){

let message = document.getElementById("message").value;

if(message.trim() === ""){
alert("Type something first!");
return;
}

let chatbox = document.getElementById("chatbox");

chatbox.innerHTML += "<p><b>You:</b> " + message + "</p>";

document.getElementById("message").value="";

try{

let response = await fetch("/chat",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({message:message})
});

let data = await response.json();

chatbox.innerHTML += "<p><b>AI:</b> " + data.reply + "</p>";

}catch(error){

chatbox.innerHTML += "<p><b>Error:</b> AI not responding</p>";

}

}

</script>

</body>
</html>
"""


@app.route("/")
def home():
    return HTML_PAGE


@app.route("/chat", methods=["POST"])
def chat():

    user_message = request.json.get("message")

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are Sambit Chatbot."},
            {"role": "user", "content": user_message}
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    result = response.json()

    reply = result["choices"][0]["message"]["content"]

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run()
