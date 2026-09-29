from shared.models.store import Store
from shared.models.crawler_run import CrawlerRun
from db import SessionLocal
from datetime import timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter

router = APIRouter(
    prefix="/crawler"
)

COSTA_RICA_TZ = ZoneInfo("America/Costa_Rica")

@router.get("/last-success")
def get_last_success_crawler():

    db = SessionLocal()

    try:

        stores = (
            db.query(Store)
            .all()
        )


        result = []


        for store in stores:

            run = (
                db.query(CrawlerRun)
                .filter(
                    CrawlerRun.store_id == store.id,
                    CrawlerRun.status == "success"
                )
                .order_by(
                    CrawlerRun.finished_at.desc()
                )
                .first()
            )


            result.append(
                {
                    "store": store.name,
                    "store_id": store.id,
                    "last_crawled_at": (
                        run.finished_at
                        .astimezone(COSTA_RICA_TZ)
                        .isoformat()
                        if run and run.finished_at
                        else None
                    )
                }
            )


        return result


    finally:
        db.close()