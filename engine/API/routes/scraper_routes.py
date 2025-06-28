from fastapi import APIRouter

router = APIRouter(prefix="/scraper", tags=["Scraper"])

@router.get("/test")
async def test_scraper():
    return {"message": "Scraper route is working"}