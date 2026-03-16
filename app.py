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

body{
margin:0;
font-family:Arial;
background:#0f172a;
color:white;
display:flex;
flex-direction:column;
height:100vh;
}

.header{
background:#111827;
padding:15px;
text-align:center;
font-size:20px;
font-weight:bold;
}

.messages{
flex:1;
overflow-y:auto;
padding:20px;
display:flex;
flex-direction:column;
}

.user{
align-self:flex-end;
background:#2563eb;
padding:10px;
border-radius:10px;
margin:5px;
max-width:70%;
}

.bot{
align-self:flex-start;
background:#1f2937;
padding:10px;
border-radius:10px;
margin:5px;
max-width:70%;
}

.input-area{
display:flex;
padding:10px;
background:#111827;
}

input{
flex:1;
padding:12px;
border:none;
border-radius:8px;
font-size:16px;
}

button{
margin-left:6px;
padding:10px;
border:none;
border-radius:8px;
background:#2563eb;
color:white;
font-size:16px;
cursor:pointer;
}

button:hover{
background:#1d4ed8;
}

.voice-btn{
background:#10b981;
}

/* voice wave animation */

#wave{
display:none;
text-align:center;
font-size:28px;
margin-top:5px;
animation:pulse 1s infinite;
}

@keyframes pulse{
0%{opacity:0.3;}
50%{opacity:1;}
100%{opacity:0.3;}
}

</style>
</head>

<body>

<div class="header">Sambit Chatbot</div>

<div class="messages" id="messages"></div>

<div id="wave">🎤 Listening...</div>

<div class="input-area">

<input id="input" placeholder="Ask me anything...">

<button class="voice-btn" onclick="startVoice()">🎤</button>

<button onclick="sendMessage()">Send</button>

</div>

<script>

let recognition;
let listening=false;

async function requestMic(){

try{
await navigator.mediaDevices.getUserMedia({audio:true});
}
catch(e){
alert("Microphone permission denied");
}

}

requestMic();

if('webkitSpeechRecognition' in window){

recognition = new webkitSpeechRecognition();

recognition.continuous=false;
recognition.interimResults=false;

recognition.onstart=function(){

listening=true;

document.getElementById("wave").style.display="block";

};

recognition.onend=function(){

listening=false;

document.getElementById("wave").style.display="none";

};

recognition.onresult=function(event){

let text=event.results[0][0].transcript;

document.getElementById("input").value=text;

};

}

function startVoice(){

if(!recognition){

alert("Voice not supported in this browser");

return;

}

recognition.start();

}

function sendMessage(){

let input=document.getElementById("input");

let message=input.value.trim();

if(!message) return;

let messages=document.getElementById("messages");

messages.innerHTML += `<div class="user">${message}</div>`;

input.value="";

messages.scrollTop=messages.scrollHeight;

fetch("/chat",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({message:message})
})

.then(res=>res.json())

.then(data=>{

messages.innerHTML += `<div class="bot">${data.reply}</div>`;

messages.scrollTop=messages.scrollHeight;

})

.catch(()=>{

messages.innerHTML += `<div class="bot">Server error</div>`;

});

}

document.getElementById("input").addEventListener("keydown",function(e){

if(e.key==="Enter"){

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

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role":"system","content":"You are a helpful AI assistant."},
            {"role":"user","content":user_msg}
        ]
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )

    data = response.json()

    reply = data["choices"][0]["message"]["content"]

    return jsonify({"reply":reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
