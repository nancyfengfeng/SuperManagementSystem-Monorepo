from datetime import datetime

from crawler.schemas.product import ProductItem
from crawler.schemas.promotion import PromotionItem


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_product(
    product: dict,
    store_code: str
):
    # barcode
    ean = product.get("ean", [])

    barcode = None

    if ean:
        barcode = ean[0]


    # image
    photos = product.get("photosUrl", [])

    image_url = None

    if photos:
        image_url = photos[0]


    # 默认价格
    price = product.get("price")

    regular_price = price
    sale_price = price


    promotion_item = None

    promotion = product.get("promotion")


    if promotion and promotion.get("isActive"):

        promotion_type = promotion.get("type")


        # 直接特价
        if promotion_type == "specialPrice":

            promo_price = product.get("promotionPricePerSubUnit")

            if promo_price is not None:
                sale_price = promo_price


        # 买 N 件优惠
        elif promotion_type == "nx$":

            conditions = promotion.get("conditions", [])

            if conditions:

                condition = conditions[0]

                quantity = condition.get("quantity")
                total_price = condition.get("price")

                if quantity and total_price is not None:

                    promotion_item = PromotionItem(
                        quantity=quantity,
                        total_price=total_price,
                        start_time=parse_datetime(
                            promotion.get("startDateTime")
                        ),
                        end_time=parse_datetime(
                            promotion.get("endDateTime")
                        ),
                    )


    product_item = ProductItem(
        barcode=barcode,
        name=product.get("name"),
        image_url=image_url,
        source_category_id=None,
        regular_price=regular_price,
        sale_price=sale_price,
        store_code=store_code,
        store_product_id=product.get("sku"),
    )


    return product_item, promotion_item