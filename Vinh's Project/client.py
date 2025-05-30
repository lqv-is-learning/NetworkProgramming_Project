import socket
import threading
import os
import webbrowser
from pathlib import Path

SERVER_IP = '127.0.0.1'
PORT = 12345

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("\n[System] Server disconnected.")
                os._exit(0)
            msg = data.decode(errors="ignore")

            print("\n" + msg + "\n> ", end="")

            if "PREVIEW:" in msg:
                filename = msg.split("PREVIEW:")[1].strip()
                preview_path = Path(filename)
                if preview_path.exists():
                    ext = preview_path.suffix.lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf']:
                        webbrowser.open(preview_path.absolute().as_uri())
        except Exception as e:
            print(f"[Error] {e}")
            break

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((SERVER_IP, PORT))
print(s.recv(1024).decode(), end="")
s.send(input().strip().encode())

print(s.recv(1024).decode(), end="")
s.send(input().strip().encode())

response = s.recv(1024).decode()
print(response)
if not response.startswith("Login successful"):
    s.close()
    exit()

threading.Thread(target=receive_messages, args=(s,), daemon=True).start()

chat_with = None

while True:
    msg = input("> ").strip()
    if msg.lower() == "exit":
        break
    elif msg.startswith("/chat "):
        chat_with = msg.split(" ", 1)[1]
        print(f"[System] Now chatting with {chat_with}")
    elif msg.lower() == "/exitchat":
        chat_with = None
        print("[System] Exited chat session.")
    elif msg.startswith("@"):
        s.send(msg.encode())
    elif msg.startswith("/send "):
        try:
            parts = msg.split(" ", 2)
            recipient = parts[1]
            filepath = parts[2]

            if not os.path.isfile(filepath):
                print("[System] File not found.")
                continue

            filesize = os.path.getsize(filepath)
            if filesize > 5 * 1024 * 1024:
                print("[System] File too large. Max 5MB.")
                continue

            filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                file_data = f.read()

            header = f"FILE:{recipient}:{filename}:{len(file_data)}"
            s.send(header.encode())
            s.sendall(file_data)

            response = s.recv(4096).decode()
            print(f"[Server Response] {response}")
        except Exception as e:
            print(f"[Error] {e}")
    elif chat_with:
        s.send(f"@{chat_with} {msg}".encode())
    else:
        print("[System] Invalid format. Use @user, /chat user, or /send user /path/to/file")

s.close()