from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import listing_routes

app = FastAPI(title="RideRadar API")

# Allow frontend
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(listing_routes.router)

@app.get("/")
def read_root():
    return {"message": "RideRadar API is running"}