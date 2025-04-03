import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

PORT = 54321
SCRIPTS_FOLDER = "scripts"
WEB_FOLDER = "web"

class PowerShellWebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/':
                # Serve main page with script list
                self.serve_script_list()
            elif self.path.startswith('/run/'):
                # Handle script execution
                script_name = self.path[5:]
                self.execute_script(script_name)
            elif self.path.startswith('/static/'):
                # Serve static files (CSS, JS, etc.)
                self.serve_static_file()
            else:
                self.send_error(404, "File Not Found")
        except Exception as e:
            self.send_error(500, f"Server Error: {str(e)}")

    def serve_script_list(self):
        # Ensure scripts folder exists
        if not os.path.exists(SCRIPTS_FOLDER):
            os.makedirs(SCRIPTS_FOLDER)

        # List all .ps1 files
        scripts = [f for f in os.listdir(SCRIPTS_FOLDER) if f.lower().endswith('.ps1')]
        
        # Generate HTML
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
                .run-btn {{ background: #0066cc; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer; }}
                .output {{ background: #333; color: #0f0; padding: 10px; margin-top: 10px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; }}
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
            <button class="run-btn" onclick="runScript('{script_name}')">Run Script</button>
            <div id="output-{script_name}" class="output" style="display:none;"></div>
        </div>
        <script>
            function runScript(scriptName) {{
                const outputDiv = document.getElementById('output-' + scriptName);
                outputDiv.style.display = 'block';
                outputDiv.textContent = 'Executing...';
                
                fetch('/run/' + scriptName)
                    .then(response => response.text())
                    .then(data => {{
                        outputDiv.textContent = data;
                    }})
                    .catch(error => {{
                        outputDiv.textContent = 'Error: ' + error;
                    }});
            }}
        </script>
        """

    def execute_script(self, script_name):
        script_path = os.path.join(SCRIPTS_FOLDER, script_name)
        
        if not os.path.exists(script_path):
            self.send_error(404, "Script not found")
            return
        
        try:
            # Execute the PowerShell script
            result = subprocess.run(
                ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_path],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            output = f"Exit Code: {result.returncode}\n\n"
            output += "=== STDOUT ===\n"
            output += result.stdout + "\n\n"
            output += "=== STDERR ===\n"
            output += result.stderr
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(output.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error executing script: {str(e)}")

    def serve_static_file(self):
        file_path = os.path.join(WEB_FOLDER, self.path[8:])
        
        if os.path.exists(file_path):
            self.send_response(200)
            
            # Set content type based on file extension
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
            self.send_error(404, "File not found")

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
    
    # Open browser automatically
    webbrowser.open(f'http://localhost:{PORT}')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")

if __name__ == '__main__':
    run_server()