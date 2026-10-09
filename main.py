from fastapi import FastAPI

app = FastAPI(title="Task Management API")

@app.get("/health")
async def health():
    return {"status": "ok"}