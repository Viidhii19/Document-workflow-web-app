import requests
import io
import time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

pdf_path = "live_large_test.pdf"
c = canvas.Canvas(pdf_path, pagesize=letter)
for i in range(200):
    c.drawString(100, 750, f"This is test page {i+1} with a lot of text. " * 20)
    c.showPage()
c.save()

print("Uploading to user's live server...")
start = time.time()
try:
    with open(pdf_path, "rb") as f:
        files = {"file": ("live_large_test.pdf", f, "application/pdf")}
        response = requests.post("http://localhost:8000/api/documents/upload", files=files, timeout=300)
    
    print(f"Time taken: {time.time() - start:.2f} seconds")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Failed to communicate with live server: {e}")
