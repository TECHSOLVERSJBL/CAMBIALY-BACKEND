from fastapi import FastAPI

app = FastAPI(title="AhorraVE API")

@app.get("/")
async def root():
    return {"message": "API is working fine now!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}