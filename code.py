import wifi
import socket
import _thread
import time
import board
import os

# === CONFIG ===
SSID = "Free Halloween WiFi"
PASSWORD = ""  # leave empty for open AP

# === START ACCESS POINT ===
print("Starting Access Point...")
ap = wifi.radio.start_ap(SSID, password=PASSWORD if PASSWORD else None)
ap_ip = str(ap.ipv4_address)
print("AP IP:", ap_ip)

# === LOAD HTML FILE ===
HTML_FILE = "index.html"

def load_html():
    try:
        with open(HTML_FILE, "rb") as f:
            html = f.read()
        # Replace placeholder {ip} in file with AP IP
        html = html.replace(b"{ip}", ap_ip.encode())
        return html
    except Exception as e:
        print(f"Error loading {HTML_FILE}: {e}")
        return b"<html><body><h1>Error loading page</h1></body></html>"

# === DNS SERVER ===
def dns_worker():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind(('0.0.0.0', 53))
    print("DNS server running on port 53")

    while True:
        try:
            data, addr = udp.recvfrom(512)
            if not data:
                continue
            tid = data[0:2]
            flags = b'\x81\x80'
            qdcount = data[4:6]
            ancount = b'\x00\x01'
            nscount = b'\x00\x00'
            arcount = b'\x00\x00'

            i = 12
            while data[i] != 0:
                i += 1
            qname = data[12:i+1]
            qtype_qclass = data[i+1:i+5]

            # Answer pointing to AP IP
            name_ptr = b'\xc0\x0c'
            type_a = b'\x00\x01'
            class_in = b'\x00\x01'
            ttl = b'\x00\x00\x00\x3c'
            rdlength = b'\x00\x04'
            rdata = bytes([int(x) for x in ap_ip.split('.')])

            response = bytearray()
            response += tid
            response += flags
            response += qdcount
            response += ancount
            response += nscount
            response += arcount
            response += data[12:i+5]
            response += name_ptr
            response += type_a
            response += class_in
            response += ttl
            response += rdlength
            response += rdata

            udp.sendto(response, addr)
        except Exception as e:
            print("DNS error:", e)
            time.sleep(0.01)

_thread.start_new_thread(dns_worker, ())

# === HTTP SERVER ===
def http_handler(conn, addr):
    try:
        req = conn.recv(1024)
        if not req:
            conn.close()
            return
        page = load_html()
        headers = [
            "HTTP/1.1 200 OK",
            "Content-Type: text/html; charset=utf-8",
            "Content-Length: {}".format(len(page)),
            "Connection: close",
            "",
            ""
        ]
        resp = "\r\n".join(headers).encode() + page
        conn.send(resp)
    except Exception as e:
        print("HTTP handler error:", e)
    finally:
        try:
            conn.close()
        except:
            pass

def http_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(5)
    print("HTTP server running on port 80")
    while True:
        try:
            conn, addr = s.accept()
            http_handler(conn, addr)
        except Exception as e:
            print("HTTP accept error:", e)
            time.sleep(0.05)

http_server()
