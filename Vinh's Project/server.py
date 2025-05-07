import socket
import threading
import os
import hashlib
from cryptography.fernet import Fernet

HOST = '0.0.0.0'
PORT = 12345
MAX_CLIENTS = 20

# Đọc thông tin người dùng
def load_users(filename="users.txt"):
    users = {}
    with open(filename, "r") as f:
        for line in f:
            if "," in line:
                username, password = line.strip().split(",", 1)
                users[username] = password
    return users

user_credentials = load_users()
clients = {}
lock = threading.Lock()

# Tải khóa mã hóa
if not os.path.exists("fernet.key"):
    with open("fernet.key", "wb") as f:
        f.write(Fernet.generate_key())

with open("fernet.key", "rb") as kf:
    fernet = Fernet(kf.read())

def send_to_user(sender, recipient, message):
    with lock:
        if recipient in clients:
            try:
                clients[recipient].send(f"[{sender}] {message}".encode())
            except:
                clients[recipient].close()
                del clients[recipient]
        else:
            if sender in clients:
                clients[sender].send(f"[Server] User '{recipient}' not online.".encode())

def handle_client(conn, addr):
    username = None
    try:
        conn.send("Username: ".encode())
        username = conn.recv(1024).decode().strip()

        conn.send("Password: ".encode())
        password = conn.recv(1024).decode().strip()

        if username not in user_credentials or user_credentials[username] != password:
            conn.send("Login failed.".encode())
            conn.close()
            return

        with lock:
            if username in clients:
                conn.send("User already logged in.".encode())
                conn.close()
                return
            clients[username] = conn

        conn.send(f"Login successful! Welcome, {username}.".encode())
        print(f"[+] {username} logged in from {addr}")

        while True:
            data = conn.recv(4096)
            if not data:
                break
            msg = data.decode(errors="ignore").strip()

            if msg.startswith("FILE:"):
                try:
                    _, to_user, filename, checksum = msg.split(":", 3)

                    # Nhận toàn bộ file
                    file_data = b""
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        file_data += chunk
                        if len(chunk) < 4096:
                            break

                    # Mã hóa và lưu
                    os.makedirs("uploads", exist_ok=True)
                    enc_data = fernet.encrypt(file_data)
                    with open(os.path.join("uploads", filename + ".enc"), "wb") as f:
                        f.write(enc_data)

                    # Giải mã và lưu sang thư mục nhận
                    dec_data = fernet.decrypt(enc_data)
                    actual_sha = hashlib.sha256(dec_data).hexdigest()
                    match = "OK" if actual_sha == checksum else "MISMATCH"

                    folder = f"receive_to_{to_user}"
                    os.makedirs(folder, exist_ok=True)
                    save_path = os.path.join(folder, filename)
                    with open(save_path, "wb") as f:
                        f.write(dec_data)

                    if to_user in clients:
                        clients[to_user].send(
                            f"[File] You received '{filename}' from {username}\nSHA256: {actual_sha} ({match})".encode()
                        )

                    print(f"[Server] File from {username} to {to_user} saved to {save_path} ({match})")
                    conn.send(f"[Server] File '{filename}' sent to '{to_user}' ({match})".encode())

                except Exception as e:
                    print(f"[Error] Handling file: {e}")
                    conn.send(f"[Server] Error handling file: {e}".encode())

            elif msg.startswith("@"):
                try:
                    to_user, content = msg[1:].split(" ", 1)
                    send_to_user(username, to_user, content)
                except ValueError:
                    conn.send("[Server] Use: @username message".encode())

            else:
                conn.send("[Server] Invalid message format.".encode())

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