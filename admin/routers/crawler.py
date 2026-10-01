from fastapi import APIRouter, HTTPException
import subprocess
from pathlib import Path
from db import SessionLocal

from crawler.categories.megasuper_category_repair import repair_categories
from shared.models.crawler_run import CrawlerRun

PROJECT_ROOT = Path("/www/wwwroot/SuperManagementSystem")
CRAWLER_SCRIPT = PROJECT_ROOT / "crawler" / "run_crawler.sh"
CRAWLER_LOG = PROJECT_ROOT / "crawler" / "logs" / "manual_run.log"

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



@router.post("/run")
def run_crawler():
    try:
        if not CRAWLER_SCRIPT.exists():
            raise HTTPException(
                status_code=404,
                detail="Crawler script not found"
            )

        CRAWLER_LOG.parent.mkdir(parents=True, exist_ok=True)

        with open(CRAWLER_LOG, "a") as log_file:
            subprocess.Popen(
                ["/bin/bash", str(CRAWLER_SCRIPT)],
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )

        return {
            "code": 200,
            "message": "Crawler started"
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/status")
def get_crawler_status():
    db = SessionLocal()

    try:
        runs = (
            db.query(CrawlerRun)
            .order_by(CrawlerRun.started_at.desc())
            .limit(50)
            .all()
        )

        latest_by_store = {}

        for run in runs:
            if run.store_id not in latest_by_store:
                latest_by_store[run.store_id] = run

        latest_runs = list(latest_by_store.values())

        if not latest_runs:
            return {
                "code": 200,
                "data": {
                    "status": "idle",
                    "stores": []
                }
            }

        statuses = [run.status for run in latest_runs]

        if "running" in statuses:
            overall_status = "running"
        elif "failed" in statuses:
            overall_status = "failed"
        else:
            overall_status = "success"

        return {
            "code": 200,
            "data": {
                "status": overall_status,
                "stores": [
                    {
                        "store_id": run.store_id,
                        "status": run.status,
                        "started_at": run.started_at,
                        "finished_at": run.finished_at,
                        "error_message": run.error_message
                    }
                    for run in latest_runs
                ]
            }
        }

    finally:
        db.close()