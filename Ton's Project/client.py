# client.py
import socket
import threading
import os
import hashlib
from media_preview import open_media

HOST = '117.5.210.143'
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

def clear_cache():
    for f in os.listdir(RECEIVED_FOLDER):
        try:
            os.remove(os.path.join(RECEIVED_FOLDER, f))
        except:
            pass
    print("[*] Cache cleared.")

def receiver(sock):
    while True:
        try:
            header = recv_line(sock)
            if not header:
                break

            if header.startswith("FILE_TRANSFER"):
                _, filename, filesize = header.strip().split('|')
                filesize = int(filesize)
                filepath = os.path.join(RECEIVED_FOLDER, filename)

                with open(filepath, 'wb') as f:
                    remaining = filesize
                    while remaining > 0:
                        chunk = sock.recv(min(1024, remaining))
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)

                print(f"\n[+] File '{filename}' downloaded to {filepath}")
                open_media(filepath)

            elif header.startswith("TEXT|"):
                print(f"\n{header[5:]}")
            elif header.startswith("NOTIFY|"):
                print(f"\n🔔 {header[7:]}")
            elif header.startswith("ERROR|"):
                print(f"\n[!] {header[6:]}")
            elif header.startswith("INFO|") or header.startswith("OK|"):
                print(f"\n{header[header.find('|') + 1:]}")
            else:
                print(f"\n[?] Unknown message: {header}")

            print("> ", end='')

        except Exception as e:
            print(f"\n[!] Receiver error: {e}")
            break

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    s.send(f"{username}|{password}\n".encode())
    print(recv_line(s))

    threading.Thread(target=receiver, args=(s,), daemon=True).start()

    while True:
        print("\n1. Send Text\n2. Send File\n3. Request File\n4. Clear Cache\n5. Exit")
        choice = input("> ").strip()

        if choice == '1':
            msg = input("Message: ")
            s.send(f"TEXT|{msg}\n".encode())

        elif choice == '2':
            filepath = input("Enter absolute file path: ").strip()
            if not os.path.isabs(filepath) or not os.path.isfile(filepath):
                print("Invalid file path.")
                continue
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath)
            filehash = sha256_checksum(filepath)
            s.send(f"FILE|{filename}|{filesize}|{filehash}\n".encode())
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    s.send(data)

        elif choice == '3':
            filename = input("Enter filename to request: ")
            s.send(f"GET_FILE|{filename}\n".encode())

        elif choice == '4':
            clear_cache()

        elif choice == '5':
            print("Exiting...")
            break

        else:
            print("Invalid choice.")
