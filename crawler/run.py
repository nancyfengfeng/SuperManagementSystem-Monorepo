from concurrent.futures import ThreadPoolExecutor, as_completed

from crawler.categories.category_loader import load_categories, get_leaf_categories

from crawler.spiders.vtex.products import get_products as get_vtex_products
from crawler.spiders.vtex.parser import parse_product as parse_vtex_product

from crawler.spiders.megasuper.products import get_products as get_megasuper_products, load_root_categories
from crawler.spiders.megasuper.parser import parse_product as parse_megasuper_product

from crawler.pipelines.product_pipeline import save_product
from crawler.pipelines.promotion_pipeline import save_promotion, deactivate_promotions

from crawler.database.session import SessionLocal

from crawler.services.store_service import get_store_id
from crawler.services.crawler_run_service import start_crawler_run, finish_crawler_run

from crawler.utils.logger import logger

from models.supplier_products import SupplierProduct


VTEX_MAX_WORKERS = 3
MEGASUPER_MAX_WORKERS = 3


def crawl_vtex_category(store_code: str, category: dict):
    session = SessionLocal()

    try:
        page = 1

        while True:
            result = get_vtex_products(store_code=store_code, category_slug=category["slug"], page=page)

            products = result["products"]
            pagination = result["pagination"]
            total_pages = pagination.get("count", 1)

            logger.info("%s | %s | page:%s | products:%s | total_pages:%s", store_code, category["name"], page, len(products), total_pages)

            for product in products:
                item, promotion = parse_vtex_product(product, store_code)

                if item is None:
                    continue

                store_product = save_product(session, item)

                if store_product is None:
                    continue

                deactivate_promotions(session, store_product)

                if promotion:
                    save_promotion(session, store_product, promotion)

            if page >= total_pages:
                break

            page += 1

        session.commit()

        logger.info("%s | %s | saved", store_code, category["name"])

    except Exception:
        session.rollback()
        logger.exception("%s | category failed: %s", store_code, category["name"])
        raise

    finally:
        session.close()


def crawl_vtex_store(store_code: str):
    session = SessionLocal()
    run = None

    try:
        store_id = get_store_id(session, store_code)
        run = start_crawler_run(session, store_id)

        categories = load_categories()
        leaf_categories = get_leaf_categories(categories)

        logger.info("===== START %s =====", store_code)
        logger.info("%s | categories:%s | workers:%s", store_code, len(leaf_categories), VTEX_MAX_WORKERS)

        with ThreadPoolExecutor(max_workers=VTEX_MAX_WORKERS, thread_name_prefix=f"{store_code}-worker") as executor:
            futures = [executor.submit(crawl_vtex_category, store_code, category) for category in leaf_categories]

            for future in as_completed(futures):
                future.result()

        finish_crawler_run(session, run, "success")

        logger.info("===== DONE %s =====", store_code)

    except Exception as e:
        if run:
            finish_crawler_run(session, run, "failed", str(e))

        logger.exception("%s crawler failed", store_code)
        raise

    finally:
        session.close()


def crawl_megasuper_category(category: dict):
    session = SessionLocal()

    try:
        category_id = category["external_id"]
        page = 1
        page_size = 100

        while True:
            products = get_megasuper_products(category_reference=category_id, page=page, page_size=page_size)

            logger.info("megasuper | %s | page:%s | products:%s", category["name"], page, len(products))

            if not products:
                break

            for product in products:
                item, promotion = parse_megasuper_product(product, "megasuper")

                if item is None:
                    continue

                store_product = save_product(session, item)

                if store_product is None:
                    continue

                deactivate_promotions(session, store_product)

                if promotion:
                    save_promotion(session, store_product, promotion)

            if len(products) < page_size:
                break

            page += 1

        session.commit()

        logger.info("megasuper | %s | saved", category["name"])

    except Exception:
        session.rollback()
        logger.exception("megasuper | category failed: %s", category["name"])
        raise

    finally:
        session.close()


def crawl_megasuper():
    session = SessionLocal()
    run = None

    try:
        store_id = get_store_id(session, "megasuper")
        run = start_crawler_run(session, store_id)

        categories = load_root_categories()

        logger.info("===== START megasuper =====")
        logger.info("megasuper | root_categories:%s | workers:%s", len(categories), MEGASUPER_MAX_WORKERS)

        with ThreadPoolExecutor(max_workers=MEGASUPER_MAX_WORKERS, thread_name_prefix="megasuper-worker") as executor:
            futures = [executor.submit(crawl_megasuper_category, category) for category in categories]

            for future in as_completed(futures):
                future.result()

        finish_crawler_run(session, run, "success")

        logger.info("===== DONE megasuper =====")

    except Exception as e:
        if run:
            finish_crawler_run(session, run, "failed", str(e))

        logger.exception("megasuper crawler failed")
        raise

    finally:
        session.close()


def main():
    stores = [
        ("walmart", crawl_vtex_store),
        ("maxipali", crawl_vtex_store),
        ("masxmenos", crawl_vtex_store),
        ("megasuper", crawl_megasuper),
    ]

    for name, crawler in stores:
        try:
            if name == "megasuper":
                crawler()
            else:
                crawler(name)

        except Exception:
            logger.error("===== %s FAILED - CONTINUE NEXT STORE =====", name)
            continue

    logger.info("===== ALL CRAWLERS FINISHED =====")


if __name__ == "__main__":
    main()