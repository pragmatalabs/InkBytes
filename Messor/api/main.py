from fastapi import FastAPI, APIRouter
from api.routers import scrape
app = FastAPI()

app.include_router(scrape.router)
@app.get("/")
async def root():
    return {"message": "Hola Mundo"}