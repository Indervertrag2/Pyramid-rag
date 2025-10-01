from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Minimal backend running"}

if __name__ == "__main__":
    print("Starting minimal backend on port 18000...")
    uvicorn.run(app, host="127.0.0.1", port=18000)