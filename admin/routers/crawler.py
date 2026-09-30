from fastapi import APIRouter, HTTPException
from crawler.categories.megasuper_category_repair import repair_categories

router = APIRouter(prefix="/crawler", tags=["Crawler"])

@router.post("/megasuper/category-repair")
def repair_megasuper_categories():
    try:
        result = repair_categories(dry_run=False)

        return {
            "code": 200,
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )