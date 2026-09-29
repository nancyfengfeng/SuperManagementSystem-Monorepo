from crawler.schemas.promotion import PromotionItem

from shared.models.store_product_promotion import StoreProductPromotion

from shared.models.store_product_promotion import StoreProductPromotion


def deactivate_promotions(session, store_product):
    session.query(StoreProductPromotion).filter(
        StoreProductPromotion.store_product_id == store_product.id,
        StoreProductPromotion.is_active == True
    ).update(
        {
            "is_active": False
        }
    )


def save_promotion(session, store_product, promotion: PromotionItem):
    if not store_product or not promotion:
        return None

    existing = (
        session.query(StoreProductPromotion)
        .filter(
            StoreProductPromotion.store_product_id == store_product.id,
            StoreProductPromotion.quantity == promotion.quantity,
        )
        .first()
    )

    if not existing:
        existing = StoreProductPromotion(
            store_product_id=store_product.id,
            quantity=promotion.quantity,
            total_price=promotion.total_price,
            start_time=promotion.start_time,
            end_time=promotion.end_time,
            is_active=True,
        )

        session.add(existing)
        session.flush()

    else:
        existing.total_price = promotion.total_price
        existing.start_time = promotion.start_time
        existing.end_time = promotion.end_time
        existing.is_active = True

    return existing