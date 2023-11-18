import json
import mimetypes
import os
import pathlib
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from datetime import datetime
import threading

HTTP_SERVER_HOST = ''
HTTP_SERVER_PORT = 3000

UDP_SERVER_HOST = ''
UDP_SERVER_PORT = 5000

STORAGE_FOLDER = 'storage'
DATA_FILE = 'data.json'


class HttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)

        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static(pr_url.path[1:])
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        with open(filename, 'r') as f:
            self.wfile.write(f.read().encode('utf-8'))

    def send_static(self, path):
        self.send_response(200)
        mt = mimetypes.guess_type(path)

        if mt:
            self.send_header('Content-type', mt[0])
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()

        with open(f'{path}', 'rb') as file:
            self.wfile.write(file.read())

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        self.send_data_udp(data)

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    # Sockets UDP functions
    def send_data_udp(self, data):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            # data_json = json.dumps(data)
            udp_socket.sendto(data, (UDP_SERVER_HOST, UDP_SERVER_PORT))


def run_http(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = (HTTP_SERVER_HOST, HTTP_SERVER_PORT)
    http = server_class(server_address, handler_class)

    try:
        print(f'Starting http on {HTTP_SERVER_HOST}:{HTTP_SERVER_PORT}...')
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


def formatted_data(data):
    data_parse = urllib.parse.unquote_plus(data.decode())
    data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}

    current_date = datetime.now()
    return {str(current_date): data_dict}


def run_udp():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind((UDP_SERVER_HOST, UDP_SERVER_PORT))
        print(f"UDP server listening on {UDP_SERVER_HOST}:{UDP_SERVER_PORT}")

        while True:
            data, address = udp_socket.recvfrom(1024)
            data_json = formatted_data(data)
            save_data_to_json(data_json)


def save_data_to_json(data):
    pathlib.Path(STORAGE_FOLDER).mkdir(parents=True, exist_ok=True)
    file_path = os.path.join(STORAGE_FOLDER, DATA_FILE)

    data_dict = {}
    if os.path.exists(file_path):
        with open(file_path, 'r') as existing_file:
            try:
                data_dict = json.load(existing_file)
            except json.JSONDecodeError:
                pass

    data_dict.update(data)

    with open(file_path, 'w') as json_file:
        json.dump(data_dict, json_file, indent=2)
        json_file.write('\n')


if __name__ == '__main__':
    thread_http = threading.Thread(target=run_http)
    thread_udp = threading.Thread(target=run_udp)

    thread_http.start()
    thread_udp.start()

    try:
        thread_http.join()
        thread_udp.join()
    except KeyboardInterrupt:
        print('Exiting...')
