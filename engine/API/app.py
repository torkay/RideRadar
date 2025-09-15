from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import listing_routes
import os

app = FastAPI(title="RideRadar API")

# Allow frontend
origins = ["http://localhost:5173"]
prod_origin = os.getenv("PROD_ORIGIN")
if prod_origin:
    origins.append(prod_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Register routes
app.include_router(listing_routes.router)

@app.get("/")
def read_root():
    return {"message": "RideRadar API is running"}
