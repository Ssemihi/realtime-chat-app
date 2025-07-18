const username = document.body.dataset.username;
const socket = io();

const chatBox = document.getElementById('chatBox');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const userList = document.getElementById('userList');
const userCount = document.getElementById('userCount');

const logoutBtn = document.getElementById('logoutBtn');
const settingsBtn = document.getElementById('settingsBtn');

const emojiBtn = document.getElementById('emojiBtn');
const emojiPicker = document.getElementById('emojiPicker');

let privateRecipient = null;

// Mesaj gönderme fonksiyonu
function sendMessage() {
    const msg = messageInput.value.trim();
    if (!msg) return;

    if (privateRecipient) {
        socket.emit('private_message', { to: privateRecipient, message: msg });
    } else {
        socket.emit('send_message', { message: msg });
    }
    messageInput.value = '';
}
sendBtn.onclick = sendMessage;
messageInput.addEventListener("keyup", (e) => {
    if (e.key === "Enter") sendMessage();
});

// Logout butonu
logoutBtn.onclick = () => {
    window.location.href = "/logout";
};

// Settings butonu
settingsBtn.onclick = () => {
    alert("Henüz ayarlar sayfası yok. Yakında eklenecek!");
};

// Emoji picker toggle
emojiBtn.onclick = () => {
    emojiPicker.style.display = emojiPicker.style.display === 'none' ? 'block' : 'none';
};

// Emoji seçildiğinde mesaj alanına ekle
emojiPicker.addEventListener('emoji-click', event => {
    messageInput.value += event.detail.unicode;
    messageInput.focus();
    emojiPicker.style.display = 'none';
});

// Kullanıcı listesi güncelleme ve tıklanabilir özel mesaj için
function updateUserList(users) {
    userList.innerHTML = '';
    users.forEach(user => {
        const li = document.createElement('li');
        li.textContent = user === username ? user + " (siz)" : user;
        if (user === username) {
            li.style.fontWeight = "bold";
            li.style.cursor = "default";
        } else {
            li.style.cursor = "pointer";
            li.onclick = () => {
                if (privateRecipient === user) {
                    privateRecipient = null;
                    li.classList.remove("selected");
                    alert("Özel sohbet kapatıldı.");
                } else {
                    privateRecipient = user;
                    // Seçili olmayan tüm liste elemanlarından "selected" kaldır
                    [...userList.children].forEach(child => child.classList.remove("selected"));
                    li.classList.add("selected");
                    alert(user + " ile özel sohbet moduna geçtiniz.");
                }
            };
        }
        userList.appendChild(li);
    });
}

socket.on('user_list', data => {
    updateUserList(data.users);
    userCount.textContent = data.count;
});

// Genel mesaj alma
socket.on('receive_message', data => {
    if (privateRecipient) return; // Özel moddaysak genel mesaj gösterme

    const el = document.createElement('div');
    el.classList.add('message');
    if (data.username === username) el.classList.add('self');
    el.innerHTML = `<strong>${data.username}</strong> <span class="timestamp">${data.timestamp}</span><br>${data.message}`;
    chatBox.appendChild(el);
    chatBox.scrollTop = chatBox.scrollHeight;
});

// Sistem mesajları
socket.on('receive_system_message', data => {
    const el = document.createElement('div');
    el.classList.add('message', 'system');
    el.textContent = data.message;
    chatBox.appendChild(el);
    chatBox.scrollTop = chatBox.scrollHeight;
});

// Özel mesajları göster
socket.on('receive_private_message', data => {
    const el = document.createElement('div');
    el.classList.add('message');
    if (data.self) el.classList.add('self');
    el.style.border = "2px solid #f39c12";
    el.innerHTML = `<strong>Özel - ${data.username}</strong> <span class="timestamp">${data.timestamp}</span><br>${data.message}`;
    chatBox.appendChild(el);
    chatBox.scrollTop = chatBox.scrollHeight;
});
