from pydantic import BaseModel
from typing import Optional

class Listing(BaseModel):
    title: str
    subtitle: Optional[str]
    link: str
    img: Optional[str]
    location: Optional[str]
    odometer: Optional[str]
    vendor: str

    # Optional fields for salvage/auction listings
    cylinder: Optional[str]
    gearbox: Optional[str]
    wovr: Optional[str]
    date: Optional[str]