import socket
import hashlib
import threading
import os

SERVER_IP = '127.0.0.1'
PORT = 12345

def sha256_of_file(path):
    try:
        with open(path, 'rb') as f:
            h = hashlib.sha256()
            while chunk := f.read(4096):
                h.update(chunk)
            return h.hexdigest()
    except FileNotFoundError:
        return None

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("\n[System] Server disconnected.")
                os._exit(0)
            print("\n" + data.decode() + "\n> ", end="")
        except:
            break

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((SERVER_IP, PORT))
print("Connecting to server...")

# Đăng nhập
print(s.recv(1024).decode(), end="")  # Username
username = input()
s.send(username.encode())

print(s.recv(1024).decode(), end="")  # Password
password = input()
s.send(password.encode())

response = s.recv(1024).decode()
print(response)

if not response.startswith("Login successful"):
    s.close()
    exit()

threading.Thread(target=receive_messages, args=(s,), daemon=True).start()

chat_with = None

while True:
    msg = input("> ").strip()
    if msg.lower() == 'exit':
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

            filename = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                file_data = f.read()

            sha256 = hashlib.sha256(file_data).hexdigest()
            header = f"FILE:{recipient}:{filename}:{sha256}"
            s.send(header.encode())
            s.sendall(file_data)

            # Nhận phản hồi từ server
            server_response = s.recv(4096).decode()
            print(f"[Server Response] {server_response}")

        except Exception as e:
            print(f"[Error] {e}")

    elif os.path.isabs(msg) and os.path.isfile(msg):
        print("[System] To send file, use: /send <username> <file_path>")
    elif chat_with:
        s.send(f"@{chat_with} {msg}".encode())
    else:
        print("[System] Invalid format. Use @user, /chat user, or /send user /path/to/file")

s.close()