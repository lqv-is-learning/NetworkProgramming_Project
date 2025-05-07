import socket
import threading
import os
from datetime import datetime

HOST = '0.0.0.0'
PORT = 12345
MAX_CLIENTS = 20
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def log_message(sender, recipient, message):
    os.makedirs("history", exist_ok=True)
    filename = f"history/chat_{sender}_{recipient}.txt"
    with open(filename, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {sender} -> {recipient}: {message}\n")

def load_users(filename="users.txt"):
    users = {}
    if not os.path.exists(filename):
        return users
    with open(filename, "r") as f:
        for line in f:
            if "," in line:
                username, password = line.strip().split(",", 1)
                users[username] = password
    return users

clients = {}
user_credentials = load_users()
lock = threading.Lock()

def send_to_user(sender, recipient, message):
    with lock:
        if recipient in clients:
            clients[recipient].send(f"[{sender}] {message}".encode())
        else:
            clients[sender].send(f"[Server] User '{recipient}' not online.".encode())

def handle_client(conn, addr):
    username = None
    try:
        conn.send(b"Username: ")
        username = conn.recv(1024).decode().strip()
        conn.send(b"Password: ")
        password = conn.recv(1024).decode().strip()

        if username not in user_credentials or user_credentials[username] != password:
            conn.send(b"Login failed.")
            conn.close()
            return

        with lock:
            if username in clients:
                conn.send(b"User already logged in.")
                conn.close()
                return
            clients[username] = conn

        conn.send(f"Login successful! Welcome, {username}".encode())
        print(f"[+] {username} connected from {addr}")

        while True:
            data = conn.recv(4096)
            if not data:
                break
            msg = data.decode(errors="ignore").strip()

            if msg.startswith("FILE:"):
                _, to_user, filename, filesize = msg.split(":", 3)
                filesize = int(filesize)
                file_data = b""
                while len(file_data) < filesize:
                    chunk = conn.recv(min(4096, filesize - len(file_data)))
                    if not chunk:
                        break
                    file_data += chunk

                with open(filename, "wb") as f:
                    f.write(file_data)

                if to_user in clients:
                    clients[to_user].send(f"[File] {username} sent '{filename}'\nPREVIEW:{filename}".encode())

                print(f"[Server] {username} sent file '{filename}' to {to_user}")
                conn.send(f"[Server] File '{filename}' sent to '{to_user}'.".encode())

            elif msg.startswith("@"):
                try:
                    to_user, content = msg[1:].split(" ", 1)
                    send_to_user(username, to_user, content)
                    log_message(username, to_user, content)
                except:
                    conn.send(b"[Server] Use: @username message")
            else:
                conn.send(b"[Server] Invalid message format.")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        with lock:
            if username in clients:
                del clients[username]
        conn.close()
        print(f"[-] {username} disconnected")

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(MAX_CLIENTS)
    print(f"[Server] Listening on port {PORT}...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
