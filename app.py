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

#voiceWave{
display:none;
text-align:center;
font-size:20px;
padding:6px;
animation:pulse 1s infinite;
}

@keyframes pulse{
0%{opacity:0.3;}
50%{opacity:1;}
100%{opacity:0.3;}
}

.input-area{
display:flex;
padding:10px;
background:#111827;
align-items:center;
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

.accept-btn{
background:#22c55e;
}

.cancel-btn{
background:#ef4444;
}

</style>
</head>

<body>

<div class="header">Sambit Chatbot</div>

<div class="messages" id="messages"></div>

<div id="voiceWave">🌊 Listening...</div>

<div class="input-area">

<input id="input" placeholder="Ask me anything...">

<button id="micBtn" class="voice-btn">🎤</button>

<button id="acceptBtn" class="accept-btn" style="display:none;">✔</button>

<button id="cancelBtn" class="cancel-btn" style="display:none;">❌</button>

<button onclick="sendMessage()">Send</button>

</div>

<script>

let recognition;
let transcript = "";

const micBtn = document.getElementById("micBtn");
const acceptBtn = document.getElementById("acceptBtn");
const cancelBtn = document.getElementById("cancelBtn");
const voiceWave = document.getElementById("voiceWave");
const input = document.getElementById("input");

async function requestMic(){

try{
await navigator.mediaDevices.getUserMedia({audio:true});
}catch(e){
console.log("Mic permission denied");
}

}

requestMic();

if ('webkitSpeechRecognition' in window){

recognition = new webkitSpeechRecognition();

recognition.continuous = true;
recognition.interimResults = true;

recognition.onresult = function(event){

transcript="";

for(let i=event.resultIndex;i<event.results.length;i++){

transcript += event.results[i][0].transcript;

}

};

}

micBtn.onclick = () => {

if(!recognition){
alert("Voice not supported in this browser");
return;
}

transcript="";

voiceWave.style.display="block";

micBtn.style.display="none";
acceptBtn.style.display="inline";
cancelBtn.style.display="inline";

recognition.start();

};

acceptBtn.onclick = () => {

recognition.stop();

input.value = transcript;

voiceWave.style.display="none";

micBtn.style.display="inline";
acceptBtn.style.display="none";
cancelBtn.style.display="none";

};

cancelBtn.onclick = () => {

recognition.stop();

transcript="";

voiceWave.style.display="none";

micBtn.style.display="inline";
acceptBtn.style.display="none";
cancelBtn.style.display="none";

};

function sendMessage(){

let message=input.value.trim();

if(!message) return;

const messages=document.getElementById("messages");

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

input.addEventListener("keydown",function(e){

if(e.key==="Enter") sendMessage();

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
        "model": "llama-3.1-8b-instant",
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
            reply = str(data)

    except Exception as e:
        reply = "Server error: " + str(e)

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
