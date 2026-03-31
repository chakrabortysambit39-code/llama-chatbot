from flask import Flask, request, jsonify, render_template_string, session, redirect
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

# ---------------- LOGIN UI ----------------
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
body {background:#0f172a; color:white; text-align:center; font-family:sans-serif;}
input {padding:10px; margin:10px; width:200px;}
button {padding:10px; background:#22c55e; border:none;}
</style>
</head>
<body>

<h2>🔐 Login / Signup</h2>

<input id="user" placeholder="Username"><br>
<input id="pass" type="password" placeholder="Password"><br>

<button onclick="login()">Login</button>
<button onclick="signup()">Signup</button>

<script>
async function login(){
    let res = await fetch("/login", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            username:user.value,
            password:pass.value
        })
    });

    let t = await res.text();
    if(t=="ok") location.reload();
    else alert("Login failed");
}

async function signup(){
    await fetch("/signup", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            username:user.value,
            password:pass.value
        })
    });
    alert("Signup success. Now login.");
}
</script>

</body>
</html>
"""

# ---------------- MAIN UI ----------------
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
<button onclick="logout()">Logout</button>
<div id="history"></div>
</div>

<div class="chatbox">

<div class="messages" id="messages"></div>

<div>
<input id="msg" placeholder="Type message">
<button onclick="send()">Send</button>
<button onclick="startVoice()">🎤</button>
</div>

<!-- CAMERA -->
<video id="camera" width="300" autoplay></video><br>
<button onclick="startCamera()">Start Camera</button>
<button onclick="capture()">Capture</button>

<input id="imgQuestion" placeholder="Ask about image">

</div>

<script>
let currentChat = null;

// 🎤 Voice input
function startVoice(){
    let r = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    r.start();
    r.onresult = e => {
        msg.value = e.results[0][0].transcript;
        send();
    }
}

// 🔊 Speak
function speak(t){
    let s = new SpeechSynthesisUtterance(t);
    speechSynthesis.speak(s);
}

// Load chats
function loadChats(){
    fetch("/get_chats").then(r=>r.json()).then(data=>{
        history.innerHTML="";
        data.forEach(c=>{
            let d=document.createElement("div");
            d.innerText="Chat "+c.id;
            d.onclick=()=>loadMessages(c.id);
            history.appendChild(d);
        });
    });
}

function newChat(){
    fetch("/new_chat").then(()=>loadChats());
}

function loadMessages(id){
    currentChat=id;
    fetch("/get_messages/"+id).then(r=>r.json()).then(data=>{
        messages.innerHTML="";
        data.forEach(m=>{
            messages.innerHTML+=`<p><b>${m.role}:</b> ${m.content}</p>`;
        });
    });
}

// Send message
async function send(){
    if(!currentChat){
        await fetch("/new_chat");
        let chats = await fetch("/get_chats").then(r=>r.json());
        currentChat = chats[chats.length - 1].id;}
    let res = await fetch("/chat", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            message:msg.value,
            chat_id:currentChat
        })
    });

    let data = await res.json();
    loadMessages(currentChat);
    speak(data.reply);
}

// Logout
function logout(){
    fetch("/logout").then(()=>location.reload());
}

// Camera
let stream;
function startCamera(){
    navigator.mediaDevices.getUserMedia({video:true}).then(s=>{
        stream=s;
        camera.srcObject=s;
        camera.setAttribute("playsinline", true);
    });
}

function capture(){
    let c=document.createElement("canvas");
    c.width=camera.videoWidth;
    c.height=camera.videoHeight;
    c.getContext("2d").drawImage(camera,0,0);

    let base64=c.toDataURL("image/jpeg").split(",")[1];
    sendImage(base64);
}

async function sendImage(img){
    let res = await fetch("/vision", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            image:img,
            question:imgQuestion.value
        })
    });

    let d = await res.json();
    messages.innerHTML += "<p>📷 "+d.reply+"</p>";
    speak(d.reply);
}

loadChats();
</script>

</body>
</html>
"""

# ---------------- AUTH ----------------
@app.route("/signup", methods=["POST"])
def signup():
    d = request.json
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("INSERT INTO users (username,password) VALUES (?,?)",(d["username"],d["password"]))
    conn.commit()
    conn.close()
    return "ok"

@app.route("/login", methods=["POST"])
def login():
    d = request.json
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?",(d["username"],d["password"]))
    u = c.fetchone()
    conn.close()
    if u:
        session["user_id"]=u[0]
        return "ok"
    return "fail"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- CHAT ----------------
@app.route("/chat", methods=["POST"])
def chat():
    d = request.json
    chat_id = d["chat_id"]
    msg = d["message"]

    conn = sqlite3.connect("chat.db")
    c = conn.cursor()

    c.execute("INSERT INTO messages VALUES (NULL,?,?,?)",(chat_id,"user",msg))

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":msg}]}
    )

    data = r.json()
    reply = data["choices"][0]["message"]["content"] if "choices" in data else str(data)

    c.execute("INSERT INTO messages VALUES (NULL,?,?,?)",(chat_id,"assistant",reply))

    conn.commit()
    conn.close()

    return jsonify({"reply":reply})

# ---------------- VISION ----------------
@app.route("/vision", methods=["POST"])
def vision():
    image = request.json["image"]
    question = request.json.get("question","Describe this image")

    img_bytes = base64.b64decode(image)

    hf = requests.post(
        "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base",
        headers={"Authorization": f"Bearer {HF_API_KEY}"},
        data=img_bytes
    )

    cap = hf.json()
    caption = cap[0]["generated_text"] if isinstance(cap,list) else str(cap)

    prompt = f"Image: {caption}. Question: {question}"

    g = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":prompt}]}
    )

    data = g.json()
    reply = data["choices"][0]["message"]["content"] if "choices" in data else str(data)

    return jsonify({"reply":reply})

# ---------------- HISTORY ----------------
@app.route("/new_chat")
def new_chat():
    uid = session.get("user_id")
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("INSERT INTO chats (user_id) VALUES (?)",(uid,))
    conn.commit()
    conn.close()
    return "ok"

@app.route("/get_chats")
def get_chats():
    uid = session.get("user_id")
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT id FROM chats WHERE user_id=?",(uid,))
    chats = [{"id":r[0]} for r in c.fetchall()]
    conn.close()
    return jsonify(chats)

@app.route("/get_messages/<chat_id>")
def get_messages(chat_id):
    conn = sqlite3.connect("chat.db")
    c = conn.cursor()
    c.execute("SELECT role,content FROM messages WHERE chat_id=?",(chat_id,))
    msgs = [{"role":r,"content":c} for r,c in c.fetchall()]
    conn.close()
    return jsonify(msgs)

# ---------------- HOME ----------------
@app.route("/")
def home():
    if "user_id" not in session:
        return render_template_string(LOGIN_HTML)
    return render_template_string(HTML)

if __name__ == "__main__":
    app.run(debug=True)
