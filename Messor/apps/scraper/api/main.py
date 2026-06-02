# File: api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import scrape

app = FastAPI()

# Configure CORS - allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include the router without an additional prefix
app.include_router(scrape.router)

@app.get("/")
async def root():
    return {"message": "Hola Mundo"}

@app.get('/shutdown')
def shutdown():
    return {"message": "Server shutting down..."}

@app.on_event('shutdown')
def on_shutdown():
    print('Server shutting down...')