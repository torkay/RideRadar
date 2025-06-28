from fastapi import APIRouter, Query
from ..models.listing import Listing
from typing import List, Optional
import json
from pathlib import Path

router = APIRouter(prefix="/listings", tags=["Listings"])

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "storage" / "vehicles_data.json"

@router.get("/", response_model=List[Listing])
async def get_listings(
    make: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
):
    try:
        with open(DATA_PATH, "r") as file:
            data = json.load(file)

        filtered_data = []
        for listing in data:
            listing_vendor = listing.get("vendor", "").lower()
            listing["auction"] = listing_vendor in ["manheim", "pickles"]

            if make and make.lower() not in listing["title"].lower():
                continue
            if model and model.lower() not in listing["title"].lower():
                continue
            if location and location.lower() not in listing.get("location", "").lower():
                continue
            if vendor and vendor.lower() not in listing["vendor"].lower():
                continue

            filtered_data.append(listing)

        return filtered_data

    except Exception as e:
        return {"error": f"Failed to load listings: {e}"}