"""
Start the FastAPI app using Waitress (works better on Windows than uvicorn)
"""
from waitress import serve
from app.main import app

if __name__ == "__main__":
    print("Starting Pyramid RAG Backend with Waitress on http://127.0.0.1:18000")
    serve(app, host='127.0.0.1', port=18000)