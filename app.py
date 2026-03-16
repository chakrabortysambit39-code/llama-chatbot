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

.voice-btn{background:#10b981;}
.accept-btn{background:#22c55e;}
.cancel-btn{background:#ef4444;}

.voice-wave{
display:none;
justify-content:center;
gap:4px;
height:40px;
}

.voice-wave span{
width:6px;
height:20px;
background:#22c55e;
animation:wave 1s infinite;
}

@keyframes wave{
0%,100%{height:10px;}
50%{height:30px;}
}

</style>
</head>

<body>

<div class="header">Sambit Chatbot</div>

<div class="messages" id="messages"></div>

<div id="voiceWave" class="voice-wave">
<span></span><span></span><span></span><span></span><span></span>
</div>

<div class="input-area">

<input id="input" placeholder="Ask me anything...">

<button onclick="openCamera()">📷</button>

<button id="micBtn" class="voice-btn">🎤</button>

<button id="acceptBtn" class="accept-btn" style="display:none;">✔</button>

<button id="cancelBtn" class="cancel-btn" style="display:none;">❌</button>

<button onclick="sendMessage()">Send</button>

<input type="file" id="cameraInput" accept="image/*" capture="environment" style="display:none">

</div>

<script>

let recognition;
let transcript="";

const micBtn=document.getElementById("micBtn");
const acceptBtn=document.getElementById("acceptBtn");
const cancelBtn=document.getElementById("cancelBtn");
const voiceWave=document.getElementById("voiceWave");
const input=document.getElementById("input");

async function requestMic(){
try{
await navigator.mediaDevices.getUserMedia({audio:true});
}catch(e){
console.log("Mic permission denied");
}
}

requestMic();

if('webkitSpeechRecognition' in window){

recognition=new webkitSpeechRecognition();

recognition.continuous=true;
recognition.interimResults=true;

recognition.onresult=function(event){

transcript="";

for(let i=event.resultIndex;i<event.results.length;i++){
transcript+=event.results[i][0].transcript;
}

};

}

micBtn.onclick=function(){

if(!recognition){
alert("Voice not supported");
return;
}

voiceWave.style.display="flex";

micBtn.style.display="none";
acceptBtn.style.display="inline";
cancelBtn.style.display="inline";

recognition.start();

};

acceptBtn.onclick=function(){

recognition.stop();

input.value=transcript;

voiceWave.style.display="none";

micBtn.style.display="inline";
acceptBtn.style.display="none";
cancelBtn.style.display="none";

};

cancelBtn.onclick=function(){

recognition.stop();

transcript="";

voiceWave.style.display="none";

micBtn.style.display="inline";
acceptBtn.style.display="none";
cancelBtn.style.display="none";

};

function openCamera(){

document.getElementById("cameraInput").click();

}

document.getElementById("cameraInput").addEventListener("change",function(){

let file=this.files[0];

if(!file) return;

let reader=new FileReader();

reader.onload=function(){

sendImage(reader.result);

};

reader.readAsDataURL(file);

});

function sendImage(imageData){

fetch("/analyze",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
image:imageData
})

})

.then(res=>res.json())

.then(data=>{

const messages=document.getElementById("messages");

messages.innerHTML+=`<div class="bot">${data.reply}</div>`;

messages.scrollTop=messages.scrollHeight;

});

}

function sendMessage(){

let message=input.value.trim();

if(!message) return;

const messages=document.getElementById("messages");

messages.innerHTML+=`<div class="user">${message}</div>`;

input.value="";

fetch("/chat",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({message:message})
})

.then(res=>res.json())

.then(data=>{

messages.innerHTML+=`<div class="bot">${data.reply}</div>`;

messages.scrollTop=messages.scrollHeight;

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

    user_msg=request.json.get("message","")

    headers={
        "Authorization":f"Bearer {GROQ_API_KEY}",
        "Content-Type":"application/json"
    }

    payload={
        "model":"llama-3.1-8b-instant",
        "messages":[
            {"role":"system","content":"You are a helpful AI assistant."},
            {"role":"user","content":user_msg}
        ]
    }

    response=requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )

    data=response.json()

    reply=data["choices"][0]["message"]["content"]

    return jsonify({"reply":reply})


@app.route("/analyze", methods=["POST"])
def analyze():

    data=request.json
    image=data.get("image")

    headers={
        "Authorization":f"Bearer {GROQ_API_KEY}",
        "Content-Type":"application/json"
    }

    payload={
        "model":"llava-v1.5-7b-4096-preview",
        "messages":[
            {
                "role":"user",
                "content":[
                    {"type":"text","text":"Describe this image."},
                    {"type":"image_url","image_url":{"url":image}}
                ]
            }
        ]
    }

    response=requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )

    data=response.json()

    reply=data["choices"][0]["message"]["content"]

    return jsonify({"reply":reply})


if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
