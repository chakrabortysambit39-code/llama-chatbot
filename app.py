from flask import Flask, request, jsonify
import requests
import os
import base64

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HF_API_KEY = os.environ.get("HF_API_KEY")


@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<title>Sambit AI</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{margin:0;font-family:Arial;background:#343541;color:white;display:flex;height:100vh;}
.sidebar{width:250px;background:#202123;padding:10px;}
.chat-item{padding:8px;margin:5px;background:#2a2b32;border-radius:5px;cursor:pointer;}
.main{flex:1;display:flex;flex-direction:column;}
.messages{flex:1;overflow-y:auto;padding:20px;}
.user{background:#19c37d;padding:10px;margin:5px;border-radius:10px;align-self:flex-end;}
.bot{background:#444654;padding:10px;margin:5px;border-radius:10px;}
.input-area{display:flex;padding:10px;background:#40414f;}
input{flex:1;padding:10px;border:none;border-radius:6px;}
button{margin-left:5px;padding:10px;border:none;border-radius:6px;background:#19c37d;color:white;}
</style>
</head>

<body>

<div class="sidebar">
<button onclick="newChat()">➕ New Chat</button>
<div id="chatList"></div>
</div>

<div class="main">

<div class="messages" id="messages"></div>

<div class="input-area">
<input id="input" placeholder="Message...">
<button onclick="startVoice()">🎤</button>
<button onclick="startCamera()">📷</button>
<button onclick="sendMessage()">Send</button>
<button onclick="toggleVoice()">🔊</button>
</div>

</div>

<video id="camera" style="display:none;width:100%;"></video>
<button id="captureBtn" style="display:none;">📸</button>
<canvas id="canvas" style="display:none;"></canvas>

<script>

let chats = JSON.parse(localStorage.getItem("chats")) || {};
let currentChat = null;
let voiceEnabled = true;

/* CHAT SYSTEM */

function newChat(){
let id="chat_"+Date.now();
chats[id]={title:"New Chat",messages:[]};
currentChat=id;
save();renderChats();renderMessages();
}

function save(){
localStorage.setItem("chats",JSON.stringify(chats));
}

function renderChats(){
let list=document.getElementById("chatList");
list.innerHTML="";
for(let id in chats){
let div=document.createElement("div");
div.className="chat-item";
div.innerText=chats[id].title;
div.onclick=()=>{currentChat=id;renderMessages();}
list.appendChild(div);
}
}

function renderMessages(){
let m=document.getElementById("messages");
m.innerHTML="";
if(!currentChat) return;
chats[currentChat].messages.forEach(msg=>{
m.innerHTML+=`<div class="${msg.type}">${msg.text}</div>`;
});
m.scrollTop=m.scrollHeight;
}

function addMessage(type,text){
if(!currentChat) newChat();
let chat=chats[currentChat];
chat.messages.push({type,text});
if(chat.title==="New Chat" && type==="user"){
chat.title=text.substring(0,20);
}
save();renderChats();renderMessages();
}

/* SEND MESSAGE */

function sendMessage(){
let input=document.getElementById("input");
let msg=input.value.trim();
if(!msg) return;

addMessage("user",msg);
input.value="";

fetch("/chat",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({message:msg})
})
.then(res=>res.json())
.then(data=>{
addMessage("bot",data.reply);
speak(data.reply);
});
}

/* SPEAK */

function speak(text){
if(!voiceEnabled) return;
let s=new SpeechSynthesisUtterance(text);
speechSynthesis.speak(s);
}

function toggleVoice(){voiceEnabled=!voiceEnabled;}

/* VOICE INPUT */

function startVoice(){
if(!('webkitSpeechRecognition' in window)){
alert("Voice not supported");
return;
}
let r=new webkitSpeechRecognition();
r.onresult=e=>{
document.getElementById("input").value=e.results[0][0].transcript;
};
r.start();
}

/* CAMERA */

async function startCamera(){
let video=document.getElementById("camera");
let btn=document.getElementById("captureBtn");
video.style.display="block";
btn.style.display="block";

let stream=await navigator.mediaDevices.getUserMedia({video:true});
video.srcObject=stream;
}

document.getElementById("captureBtn").onclick=function(){
let video=document.getElementById("camera");
let canvas=document.getElementById("canvas");

canvas.width=video.videoWidth*0.5;
canvas.height=video.videoHeight*0.5;

let ctx=canvas.getContext("2d");
ctx.drawImage(video,0,0,canvas.width,canvas.height);

let img=canvas.toDataURL("image/jpeg",0.6);

fetch("/analyze",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({image:img})
})
.then(res=>res.json())
.then(data=>{
addMessage("bot",data.reply);
speak(data.reply);
});
}

renderChats();

</script>

</body>
</html>
"""


@app.route("/chat", methods=["POST"])
def chat():
    try:
        user = request.json.get("message", "")

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": user}]
        }

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )

        data = r.json()
        reply = data["choices"][0]["message"]["content"]

    except Exception as e:
        reply = "Error: " + str(e)

    return jsonify({"reply": reply})


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json
        image_data = data.get("image")

        if not image_data:
            return jsonify({"reply": "❌ No image received"})

        image_base64 = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_base64)

        headers = {
            "Authorization": f"Bearer {HF_API_KEY}"
        }

        r = requests.post(
            "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base",
            headers=headers,
            data=image_bytes
        )

        result = r.json()

        if isinstance(result, list):
            reply = result[0]["generated_text"]
        else:
            reply = "❌ HF error: " + str(result)

    except Exception as e:
        reply = "❌ Vision error: " + str(e)

    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
