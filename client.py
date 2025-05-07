# ==============================
# client.py
# ==============================
import socket
import threading
import os
import hashlib
import mimetypes
from media_preview import open_media

HOST = '127.0.0.1'
PORT = 5000
RECEIVED_FOLDER = 'client_downloads'
os.makedirs(RECEIVED_FOLDER, exist_ok=True)

def sha256_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def recv_line(sock):
    line = b""
    while True:
        char = sock.recv(1)
        if not char or char == b'\n':
            break
        line += char
    return line.decode()

def receiver(sock):
    while True:
        try:
            header = recv_line(sock)  # safely read the header
            if not header:
                break

            if header.startswith("FILE_TRANSFER"):
                _, filename, filesize = header.strip().split('|')
                filesize = int(filesize)
                filepath = os.path.join(RECEIVED_FOLDER, filename)

                with open(filepath, 'wb') as f:  # 'wb' to write binary!
                    remaining = filesize
                    while remaining > 0:
                        chunk = sock.recv(min(1024, remaining))
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)

                print(f"\n[+] File '{filename}' downloaded to {filepath}\n> ", end='')
                open_media(filepath)

            else:
                print(f"\n{header}\n> ", end='')

        except Exception as e:
            print(f"\n[!] Receiver error: {e}")
            break

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    s.send(f"{username}|{password}".encode())
    print(s.recv(1024).decode())

    threading.Thread(target=receiver, args=(s,), daemon=True).start()

    while True:
        print("\n1. Send Text\n2. Send File\n3. Request File\n4. Exit")
        choice = input("> ").strip()

        if choice == '1':
            msg = input("Message: ")
            s.send(f"TEXT|{msg}".encode())

        elif choice == '2':
            filepath = input("Enter absolute file path: ")
            if not os.path.isabs(filepath) or not os.path.isfile(filepath):
                print("Invalid file path.")
                continue
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            filehash = sha256_checksum(filepath)
            s.send(f"FILE|{filename}|{filesize}|{filehash}".encode())
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    s.send(data)

        elif choice == '3':
            filename = input("Enter filename to request: ")
            s.send(f"GET_FILE|{filename}".encode())

        elif choice == '4':
            print("Exiting...")
            break

        else:
            print("Invalid choice.")
