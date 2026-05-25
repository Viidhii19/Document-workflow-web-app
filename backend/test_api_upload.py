import requests
import io
import os
import time
import subprocess
import threading
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

pdf_path = "large_test.pdf"
c = canvas.Canvas(pdf_path, pagesize=letter)
for i in range(200):
    c.drawString(100, 750, f"This is test page {i+1} with a lot of text. " * 20)
    c.showPage()
c.save()

print(f"Created {pdf_path} ({os.path.getsize(pdf_path)} bytes)")

# Start server on 8001
print("Starting backend server on port 8001...")
server_process = subprocess.Popen(
    [r"venv\Scripts\python.exe", "-m", "uvicorn", "app.main:app", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to start
time.sleep(5)

# Try to upload it via the API
print("Uploading via API...")
try:
    with open(pdf_path, "rb") as f:
        files = {"file": ("large_test.pdf", f, "application/pdf")}
        # Increase timeout just in case
        response = requests.post("http://localhost:8001/api/documents/upload", files=files, timeout=120)
        
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"API Request Failed: {e}")
finally:
    print("Terminating server...")
    server_process.terminate()
    stdout, stderr = server_process.communicate()
    if response.status_code != 200:
        print("Server Error Log:")
        print(stderr.decode())
