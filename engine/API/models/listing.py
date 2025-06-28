from pydantic import BaseModel
from typing import Optional

class Listing(BaseModel):
    title: str
    link: str
    img: str
    vendor: str

    # Optional fields based on some vendors
    price: Optional[str] = None
    location: Optional[str] = None
    date: Optional[str] = None
    subtitle: Optional[str] = None
    wovr: Optional[str] = None
    odometer: Optional[str] = None
    cylinder: Optional[str] = None
    gearbox: Optional[str] = None