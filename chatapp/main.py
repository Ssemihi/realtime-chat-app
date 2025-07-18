import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_socketio import SocketIO, emit
from flask_session import Session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "gizli_anahtar"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

socketio = SocketIO(app, manage_session=False)

DB_PATH = "chat_users.db"

# DB bağlantısı ve tablo oluşturma
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Kayıt sayfası
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not email or not username or not password or not password2:
            flash("Lütfen tüm alanları doldurun.", "error")
            return redirect(url_for("register"))

        if password != password2:
            flash("Şifreler eşleşmiyor.", "error")
            return redirect(url_for("register"))

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Kullanıcı adı veya email mevcut mu kontrolü
        c.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if c.fetchone():
            flash("Kullanıcı adı veya e-posta zaten kullanılıyor.", "error")
            conn.close()
            return redirect(url_for("register"))

        pw_hash = generate_password_hash(password)

        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, pw_hash))
        conn.commit()
        conn.close()

        flash("Kayıt başarılı! Giriş yapabilirsiniz.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# Giriş sayfası
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("chat"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Lütfen kullanıcı adı ve şifre girin.", "error")
            return redirect(url_for("login"))

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session["username"] = username
            return redirect(url_for("chat"))
        else:
            flash("Kullanıcı adı veya şifre yanlış.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("chat.html", username=session["username"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# SocketIO bölümü (aynı kalabilir, users sözlüğü güncellenmeli)
users = {}  # { sid: username }

@socketio.on("connect")
def handle_connect():
    username = session.get("username", "Anonim")
    users[request.sid] = username
    user_list = list(users.values())
    user_count = len(user_list)
    emit("user_list", {"users": user_list, "count": user_count}, broadcast=True)
    emit("receive_system_message", {"message": f"{username} sohbete katıldı."}, broadcast=True)

@socketio.on("disconnect")
def handle_disconnect():
    username = users.pop(request.sid, "Bir kullanıcı")
    user_list = list(users.values())
    user_count = len(user_list)
    emit("user_list", {"users": user_list, "count": user_count}, broadcast=True)
    emit("receive_system_message", {"message": f"{username} sohbetten ayrıldı."}, broadcast=True)

@socketio.on("send_message")
def handle_send_message(data):
    username = users.get(request.sid, "Anonim")
    message = data.get("message", "")
    timestamp = datetime.now().strftime("%H:%M")
    emit("receive_message", {
        "username": username,
        "message": message,
        "timestamp": timestamp
    }, broadcast=True)

@socketio.on("private_message")
def handle_private_message(data):
    recipient = data.get("to")
    message = data.get("message")
    sender = users.get(request.sid, "Anonim")
    timestamp = datetime.now().strftime("%H:%M")

    recipient_sid = None
    for sid, user in users.items():
        if user == recipient:
            recipient_sid = sid
            break
    if recipient_sid:
        emit("receive_private_message", {
            "username": sender,
            "message": message,
            "timestamp": timestamp
        }, room=recipient_sid)
        emit("receive_private_message", {
            "username": sender,
            "message": message,
            "timestamp": timestamp,
            "self": True
        }, room=request.sid)

if __name__ == "__main__":
    socketio.run(app, debug=True)
