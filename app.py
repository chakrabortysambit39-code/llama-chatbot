from flask import Flask, request, jsonify, render_template_string, session
import requests, os, sqlite3, base64

app = Flask(__name__)
app.secret_key = "secret123"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, user_id INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, chat_id INTEGER, role TEXT, content TEXT)")

    conn.commit()
    conn.close()

init_db()

# ---------------- UI ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
body {margin:0; display:flex; font-family:sans-serif; background:#0f172a; color:white;}
.sidebar {width:250px; background:#020617; padding:10px;}
.chatbox {flex:1; display:flex; flex-direction:column;}
.messages {flex:1; padding:10px; overflow:auto;}
input {padding:10px; margin:5px;}
button {padding:10px; background:#22c55e; border:none; margin:5px;}
video {margin:10px;}
</style>
</head>

<body>

<div class="sidebar">
<button onclick="newChat()">+ New Chat</button>
<div id="history"></div>
</div>

<div class="chatbox">

<div class="messages" id="messages"></div>

<div>
<input id="msg" placeholder="Type message">
<button onclick="send()">Send</button>
<button onclick="startVoice()">🎤</button>
</div>

<!-- 📷 CAMERA -->
<video id="camera" width="300" autoplay></video><br>
<button onclick="startCamera()">Start Camera</button>
<button onclick="capture()">Capture</button>

<input id="imgQuestion" placeholder="Ask about image">

</div>

<script>
let currentChat = null;

// 🎤 Voice
function startVoice(){
    let recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.start();
    recognition.onresult = function(e){
        document.getElementById("msg").value = e.results[0][0].transcript;
        send();
    }
}

// 🔊 Speak
function speak(text){
    let speech = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(speech);
}

// 💬 Load chats
function loadChats(){
    fetch("/get_chats").then(r=>r.json()).then(data=>{
        let h=document.getElementById("history");
        h.innerHTML="";
        data.forEach(c=>{
            let div=document.createElement("div");
            div.innerText="Chat "+c.id;
            div.onclick=()=>loadMessages(c.id);
            h.appendChild(div);
        });
    });
}

function newChat(){
    fetch("/new_chat").then(()=>loadChats());
}

function loadMessages(id){
    currentChat=id;
    fetch("/get_messages/"+id).then(r=>r.json()).then(data=>{
        let m=document.getElementById("messages");
        m.innerHTML="";
        data.forEach(msg=>{
            m.innerHTML+=`<p><b>${msg.role}:</b> ${msg.content}</p>`;
        });
    });
}

// 💬 Send
async function send(){
    let msg=document.getElementById("msg").value;

    let res=await fetch("/chat",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({message:msg, chat_id:currentChat})
    });

    let data=await res.json();
    loadMessages(currentChat);
    speak(data.reply);
}

// 📷 Camera
let stream;

function startCamera(){
    navigator.mediaDevices.getUserMedia({video:true}).then(s=>{
        stream=s;
        let video=document.getElementById("camera");
        video.srcObject=s;
        video.setAttribute("playsinline", true);
    });
}

function capture(){
    let video=document.getElementById("camera");
    let canvas=document.createElement("canvas");

    canvas.width=video.videoWidth;
    canvas.height=video.videoHeight;

    let ctx=canvas.getContext("2d");
    ctx.drawImage(video,0,0);

    let base64=canvas.toDataURL("image/jpeg").split(",")[1];
    sendCameraImage(base64);
}

async function sendCameraImage(base64){
    let question=document.getElementById("imgQuestion").value;

    let res=await fetch("/vision",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({image:base64, question:question})
    });

    let data=await res.json();
    document.getElementById("messages").innerHTML += "<p>📷 "+data.reply+"</p>";
    speak(data.reply);
}

loadChats();
</script>

</body>
</html>
"""

# ---------------- AUTH ----------------
@app.route("/signup", methods=["POST"])
def signup():
    data=request.json
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("INSERT INTO users (username,password) VALUES (?,?)",(data["username"],data["password"]))
    conn.commit()
    conn.close()
    return "ok"

@app.route("/login", methods=["POST"])
def login():
    data=request.json
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?",(data["username"],data["password"]))
    user=c.fetchone()
    conn.close()

    if user:
        session["user_id"]=user[0]
        return "ok"
    return "fail"

# ---------------- CHAT ----------------
@app.route("/chat", methods=["POST"])
def chat():
    data=request.json
    chat_id=data["chat_id"]
    msg=data["message"]

    conn=sqlite3.connect("chat.db")
    c=conn.cursor()

    c.execute("INSERT INTO messages VALUES (NULL,?,?,?)",(chat_id,"user",msg))

    response=requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={"model":"llama3-70b-8192","messages":[{"role":"user","content":msg}]}
    )

    data_res=response.json()

    if "choices" not in data_res:
        reply=str(data_res)
    else:
        reply=data_res["choices"][0]["message"]["content"]

    c.execute("INSERT INTO messages VALUES (NULL,?,?,?)",(chat_id,"assistant",reply))

    conn.commit()
    conn.close()

    return jsonify({"reply":reply})

# ---------------- VISION ----------------
@app.route("/vision", methods=["POST"])
def vision():
    image=request.json["image"]
    question=request.json.get("question","Describe this image")

    image_bytes=base64.b64decode(image)

    hf=requests.post(
        "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base",
        headers={"Authorization": f"Bearer {HF_API_KEY}"},
        data=image_bytes
    )

    caption_data=hf.json()

    if isinstance(caption_data,list):
        caption=caption_data[0]["generated_text"]
    else:
        caption=str(caption_data)

    final_prompt=f"Image: {caption}. Question: {question}"

    groq=requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={"model":"llama3-70b-8192","messages":[{"role":"user","content":final_prompt}]}
    )

    data_res=groq.json()

    if "choices" not in data_res:
        reply=str(data_res)
    else:
        reply=data_res["choices"][0]["message"]["content"]

    return jsonify({"reply":reply})

# ---------------- HISTORY ----------------
@app.route("/new_chat")
def new_chat():
    user_id=session.get("user_id")
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("INSERT INTO chats (user_id) VALUES (?)",(user_id,))
    conn.commit()
    conn.close()
    return "ok"

@app.route("/get_chats")
def get_chats():
    user_id=session.get("user_id")
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("SELECT id FROM chats WHERE user_id=?",(user_id,))
    chats=[{"id":r[0]} for r in c.fetchall()]
    conn.close()
    return jsonify(chats)

@app.route("/get_messages/<chat_id>")
def get_messages(chat_id):
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("SELECT role,content FROM messages WHERE chat_id=?",(chat_id,))
    msgs=[{"role":r,"content":c} for r,c in c.fetchall()]
    conn.close()
    return jsonify(msgs)

@app.route("/")
def home():
    if "user_id" not in session:
        return "Login first"
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(debug=True)
