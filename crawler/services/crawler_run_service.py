from datetime import datetime, timezone

from shared.models.crawler_run import CrawlerRun


def start_crawler_run(session, store_id):

    run = CrawlerRun(
        store_id=store_id,
        started_at=datetime.now(timezone.utc),
        status="running",
    )

    session.add(run)

    session.commit()

    return run



def finish_crawler_run(session, run, status="success", error_message=None):

    run.finished_at = datetime.now(timezone.utc)

    run.status = status

    run.error_message = error_message

    session.commit()