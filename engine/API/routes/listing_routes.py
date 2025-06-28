from fastapi import APIRouter
from ..models.listing import Listing
from typing import List
import json
from pathlib import Path

router = APIRouter(prefix="/listings", tags=["Listings"])

# Path to your cached JSON file
DATA_PATH = Path(__file__).resolve().parent.parent.parent / "storage" / "vehicles_data.json"

@router.get("/", response_model=List[Listing])
async def get_listings():
    try:
        with open(DATA_PATH, "r") as file:
            data = json.load(file)
        return data
    except Exception as e:
        return {"error": f"Failed to load listings: {e}"}