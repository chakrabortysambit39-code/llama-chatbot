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

# ---------------- LOGIN ----------------
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<body style="background:#0f172a;color:white;text-align:center;font-family:sans-serif;">

<h2>Login</h2>
<input id="user" placeholder="Username"><br>
<input id="pass" type="password" placeholder="Password"><br>

<button onclick="login()">Login</button>
<button onclick="signup()">Signup</button>

<script>
async function login(){
    let r = await fetch(window.location.origin + "/login",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({username:user.value,password:pass.value})
    });
    let t=await r.text();
    if(t=="ok") location.reload();
}

async function signup(){
    await fetch(window.location.origin + "/signup",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({username:user.value,password:pass.value})
    });
    alert("Signup done");
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
body {margin:0;display:flex;background:#0f172a;color:white;font-family:sans-serif;}
.sidebar {width:250px;background:#020617;padding:10px;}
.chatbox {flex:1;display:flex;flex-direction:column;}
.messages {flex:1;overflow:auto;padding:10px;}
input {padding:10px;margin:5px;}
button {padding:10px;background:#22c55e;border:none;margin:5px;}
video, img {margin:10px;border-radius:10px;}
</style>
</head>

<body>

<div class="sidebar">
<button onclick="newChat()">+ Chat</button>
<button onclick="logout()">Logout</button>
<div id="history"></div>
</div>

<div class="chatbox">

<div class="messages" id="messages"></div>

<input id="msg" placeholder="Type message">
<button onclick="send()">Send</button>

<!-- CAMERA -->
<video id="camera" width="300" autoplay playsinline></video>
<img id="preview" width="300">

<br>
<button onclick="startCamera()">Start Camera</button>
<button onclick="capture()">Capture</button>

<input id="imgQuestion" placeholder="Ask about image">

</div>

<script>
let currentChat=null;
let video=document.getElementById("camera");

// -------- CHAT --------
async function newChat(){
    await fetch(window.location.origin + "/new_chat");
    loadChats();
}

function loadChats(){
    fetch(window.location.origin + "/get_chats")
    .then(r=>r.json())
    .then(d=>{
        history.innerHTML="";
        d.forEach(c=>{
            let div=document.createElement("div");
            div.innerText="Chat "+c.id;
            div.onclick=()=>loadMessages(c.id);
            history.appendChild(div);
        });
    });
}

function loadMessages(id){
    currentChat=id;
    fetch(window.location.origin + "/get_messages/"+id)
    .then(r=>r.json())
    .then(d=>{
        messages.innerHTML="";
        d.forEach(m=>{
            messages.innerHTML+=`<p><b>${m.role}:</b> ${m.content}</p>`;
        });
    });
}

async function send(){
    if(!currentChat){
        await newChat();
        let chats=await fetch(window.location.origin + "/get_chats").then(r=>r.json());
        currentChat=chats[chats.length-1].id;
    }

    let text=msg.value;
    msg.value="";

    messages.innerHTML+=`<p><b>user:</b> ${text}</p>`;

    let r=await fetch(window.location.origin + "/chat",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({message:text,chat_id:currentChat})
    });

    let d=await r.json();
    messages.innerHTML+=`<p><b>AI:</b> ${d.reply}</p>`;
}

// -------- CAMERA --------
function startCamera(){
    navigator.mediaDevices.getUserMedia({video:true})
    .then(stream=>{
        video.srcObject=stream;
        video.play();
        console.log("Camera started");
    })
    .catch(e=>alert(e));
}

function capture(){
    if(!video.srcObject){
        alert("Start camera first");
        return;
    }

    let canvas=document.createElement("canvas");
    canvas.width=video.videoWidth || 300;
    canvas.height=video.videoHeight || 300;

    let ctx=canvas.getContext("2d");
    ctx.drawImage(video,0,0);

    let data=canvas.toDataURL("image/jpeg");

    document.getElementById("preview").src=data;

    console.log("Sending to backend...");

    sendImage(data.split(",")[1]);
}

// -------- SEND IMAGE --------
async function sendImage(img){
    try{
        let res = await fetch(window.location.origin + "/vision", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                image: img,
                question: document.getElementById("imgQuestion").value || "Describe image"
            })
        });

        let data = await res.json();

        messages.innerHTML+=`<p><b>Vision:</b> ${data.reply}</p>`;

    }catch(e){
        alert("ERROR: " + e);
    }
}

// -------- LOGOUT --------
function logout(){
    fetch(window.location.origin + "/logout").then(()=>location.reload());
}

loadChats();
</script>

</body>
</html>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    if "user_id" not in session:
        return render_template_string(LOGIN_HTML)
    return render_template_string(HTML)

@app.route("/signup", methods=["POST"])
def signup():
    d=request.json
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("INSERT INTO users (username,password) VALUES (?,?)",(d["username"],d["password"]))
    conn.commit()
    conn.close()
    return "ok"

@app.route("/login", methods=["POST"])
def login():
    d=request.json
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("SELECT id FROM users WHERE username=? AND password=?",(d["username"],d["password"]))
    u=c.fetchone()
    conn.close()
    if u:
        session["user_id"]=u[0]
        return "ok"
    return "fail"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/chat", methods=["POST"])
def chat():
    d=request.json
    msg=d["message"]
    chat_id=d["chat_id"]

    conn=sqlite3.connect("chat.db")
    c=conn.cursor()

    c.execute("INSERT INTO messages VALUES (NULL,?,?,?)",(chat_id,"user",msg))

    r=requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":msg}]}
    )

    data=r.json()
    reply=data["choices"][0]["message"]["content"] if "choices" in data else str(data)

    c.execute("INSERT INTO messages VALUES (NULL,?,?,?)",(chat_id,"assistant",reply))
    conn.commit()
    conn.close()

    return jsonify({"reply":reply})

@app.route("/vision", methods=["POST"])
def vision():
    try:
        img=base64.b64decode(request.json["image"])
        q=request.json.get("question","Describe image")

        hf=requests.post(
            "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base",
            headers={"Authorization": f"Bearer {HF_API_KEY}"},
            data=img
        )

        cap=hf.json()
        caption=cap[0]["generated_text"] if isinstance(cap,list) else str(cap)

        prompt=f"{caption}. Question: {q}"

        g=requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}]}
        )

        data=g.json()
        reply=data["choices"][0]["message"]["content"] if "choices" in data else str(data)

        return jsonify({"reply":reply})

    except Exception as e:
        return jsonify({"reply":"Error: "+str(e)})

@app.route("/new_chat")
def new_chat():
    uid=session.get("user_id")
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("INSERT INTO chats (user_id) VALUES (?)",(uid,))
    conn.commit()
    conn.close()
    return "ok"

@app.route("/get_chats")
def get_chats():
    uid=session.get("user_id")
    conn=sqlite3.connect("chat.db")
    c=conn.cursor()
    c.execute("SELECT id FROM chats WHERE user_id=?",(uid,))
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

if __name__ == "__main__":
    app.run(debug=True)
