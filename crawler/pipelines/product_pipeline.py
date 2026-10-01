from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from crawler.schemas.product import ProductItem

from crawler.services.category_service import get_category_id
from crawler.utils.logger import logger

from shared.models.product import Product
from shared.models.store_product import StoreProduct
from shared.models.store import Store




def save_product(session, item: ProductItem):

    if not item.barcode:
        return None


    now = datetime.now(timezone.utc)

    category_id = get_category_id(session,item.source_category_id)


    product_update = {
        "name": item.name,
        "category_id": category_id,
        "updated_at": now,
    }


    if item.image_url:
        product_update["image_url"] = item.image_url



    stmt = insert(Product).values(
        barcode=item.barcode,
        name=item.name,
        image_url=item.image_url,
        category_id=category_id,
    )


    stmt = stmt.on_conflict_do_update(
        index_elements=["barcode"],
        set_=product_update,
    )


    session.execute(stmt)

    session.flush()



    product = (
        session.query(Product)
        .filter(
            Product.barcode == item.barcode
        )
        .first()
    )



    store = (
        session.query(Store)
        .filter(
            Store.code == item.store_code
        )
        .first()
    )


    if not store:
        raise Exception(
            f"Store not found: {item.store_code}"
        )



    stmt = insert(StoreProduct).values(
        product_id=product.id,
        store_id=store.id,
        original_price=item.regular_price,
        selling_price=item.sale_price,
        in_stock=True,
        is_active=True,
        last_seen_at=now,
    )


    stmt = stmt.on_conflict_do_update(
        constraint="uq_store_product",
        set_={
            "original_price": item.regular_price,
            "selling_price": item.sale_price,
            "in_stock": True,
            "is_active": True,
            "last_seen_at": now,
            "updated_at": now,
        },
    )


    session.execute(stmt)

    session.flush()



    store_product = (
        session.query(StoreProduct)
        .filter(
            StoreProduct.product_id == product.id,
            StoreProduct.store_id == store.id,
        )
        .first()
    )


    return store_product