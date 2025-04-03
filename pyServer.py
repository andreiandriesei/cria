import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser
import threading
import time

PORT = 54322
SCRIPTS_FOLDER = "scripts"
WEB_FOLDER = "web"

class PowerShellWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/':
                self.serve_script_list()
            elif self.path.startswith('/run/'):
                self.handle_script_execution()
            elif self.path.startswith('/stream/'):
                self.handle_real_time_stream()
            elif self.path.startswith('/static/'):
                self.serve_static_file()
            else:
                self.send_error(404, "File Not Found")
        except Exception as e:
            self.send_error(500, f"Server Error: {str(e)}")

    def handle_script_execution(self):
        script_name = self.path[5:]  # Remove '/run/' from path
        script_path = os.path.join(SCRIPTS_FOLDER, script_name)
        
        if not os.path.exists(script_path):
            self.send_error(404, f"Script not found at: {script_path}")
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Executing {script_name}</title>
            <style>
                body {{ font-family: monospace; margin: 20px; background: #000; color: #0f0; }}
                #output {{ white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            <h2>Executing: {script_name}</h2>
            <div id="output"></div>
            <script>
                const output = document.getElementById('output');
                const eventSource = new EventSource('/stream/{script_name}');
                
                eventSource.onmessage = function(e) {{
                    output.innerHTML += e.data + '<br>';
                    window.scrollTo(0, document.body.scrollHeight);
                }};
                
                eventSource.onerror = function() {{
                    output.innerHTML += '\\n[Connection closed]';
                    eventSource.close();
                }};
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

    def handle_real_time_stream(self):
        script_name = self.path[8:]  # Remove '/stream/' from path
        script_path = os.path.join(SCRIPTS_FOLDER, script_name)
        
        if not os.path.exists(script_path):
            self.send_error(404, f"Script not found at: {script_path}")
            return
        
        self.send_response(200)
        self.send_header('Content-type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        
        try:
            process = subprocess.Popen(
                ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1,
                universal_newlines=True
            )
            
            def read_output(stream, prefix=''):
                for line in iter(stream.readline, ''):
                    self.wfile.write(f"data: {prefix}{line}\n\n".encode('utf-8'))
                    self.wfile.flush()
            
            # Start threads to read stdout and stderr
            stdout_thread = threading.Thread(target=read_output, args=(process.stdout,))
            stderr_thread = threading.Thread(target=read_output, args=(process.stderr, '[ERROR] '))
            
            stdout_thread.start()
            stderr_thread.start()
            
            while process.poll() is None:
                time.sleep(0.1)
                if not stdout_thread.is_alive() and not stderr_thread.is_alive():
                    break
            
            stdout_thread.join()
            stderr_thread.join()
            
            self.wfile.write("event: close\ndata: \n\n".encode('utf-8'))
        except Exception as e:
            self.wfile.write(f"data: [SERVER ERROR] {str(e)}\n\n".encode('utf-8'))
        finally:
            time.sleep(1)  # Ensure all data is sent before closing

    def serve_script_list(self):
        if not os.path.exists(SCRIPTS_FOLDER):
            os.makedirs(SCRIPTS_FOLDER)

        scripts = [f for f in os.listdir(SCRIPTS_FOLDER) if f.lower().endswith('.ps1')]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PowerShell Script Runner</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #0066cc; }}
                .script-list {{ margin: 20px 0; }}
                .script {{ padding: 10px; margin: 5px 0; background: #f5f5f5; border-radius: 4px; }}
                .run-btn {{ background: #0066cc; color: white; border: none; padding: 5px 10px; 
                          border-radius: 3px; cursor: pointer; margin-right: 10px; }}
                .run-realtime {{ background: #009900; }}
            </style>
        </head>
        <body>
            <h1>PowerShell Script Runner</h1>
            <div class="script-list">
                <h2>Available Scripts</h2>
                {''.join([self.create_script_card(script) for script in scripts])}
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def create_script_card(self, script_name):
        return f"""
        <div class="script">
            <h3>{script_name}</h3>
            <button class="run-btn run-realtime" onclick="window.location='/run/{script_name}'">
                Run with Realtime Output
            </button>
        </div>
        """

    def serve_static_file(self):
        file_path = os.path.join(WEB_FOLDER, self.path[8:])
        if os.path.exists(file_path):
            self.send_response(200)
            if file_path.endswith('.css'):
                self.send_header('Content-type', 'text/css')
            elif file_path.endswith('.js'):
                self.send_header('Content-type', 'application/javascript')
            else:
                self.send_header('Content-type', 'application/octet-stream')
            self.end_headers()
            with open(file_path, 'rb') as file:
                self.wfile.write(file.read())
        else:
            self.send_error(404, f"Static file not found at: {file_path}")

def run_server():
    # Create folders if they don't exist
    if not os.path.exists(SCRIPTS_FOLDER):
        os.makedirs(SCRIPTS_FOLDER)
    if not os.path.exists(WEB_FOLDER):
        os.makedirs(WEB_FOLDER)

    server_address = ('', PORT)
    httpd = HTTPServer(server_address, PowerShellWebHandler)
    
    print(f"Server started on port {PORT}")
    print(f"Access at: http://localhost:{PORT}")
    print(f"Put your PowerShell scripts in the '{SCRIPTS_FOLDER}' folder")
    print("Press Ctrl+C to stop the server")
    
    webbrowser.open(f'http://localhost:{PORT}')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == '__main__':
    run_server()