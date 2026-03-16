from flask import Flask, request, jsonify
import requests
import os
import base64

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

<button onclick="startVoice()">🎤 Voice</button>

<br><br>

<input type="file" id="imageUpload">

<button onclick="sendImage()">📷 Analyze Image</button>

<script>

async function sendMessage(){

let message=document.getElementById("message").value

let response=await fetch("/chat",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({message:message})
})

let data=await response.json()

let chatbox=document.getElementById("chatbox")

chatbox.innerHTML += "<p><b>You:</b> "+message+"</p>"
chatbox.innerHTML += "<p><b>AI:</b> "+data.reply+"</p>"

document.getElementById("message").value=""

}

function startVoice(){

let recognition = new webkitSpeechRecognition()

recognition.onresult=function(event){

let text=event.results[0][0].transcript

document.getElementById("message").value=text

sendMessage()

}

recognition.start()

}

async function sendImage(){

let fileInput=document.getElementById("imageUpload")

let file=fileInput.files[0]

let formData=new FormData()

formData.append("image",file)

let response=await fetch("/analyze-image",{
method:"POST",
body:formData
})

let data=await response.json()

let chatbox=document.getElementById("chatbox")

chatbox.innerHTML += "<p><b>Image Analysis:</b> "+data.result+"</p>"

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

    user_message = request.json["message"]

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

    reply = response.json()["choices"][0]["message"]["content"]

    return jsonify({"reply": reply})


@app.route("/analyze-image", methods=["POST"])
def analyze_image():

    image = request.files["image"]
    image_bytes = image.read()

    # For now just confirming upload
    return jsonify({"result": "Image received. Image analysis feature coming soon."})


if __name__ == "__main__":
    app.run()
