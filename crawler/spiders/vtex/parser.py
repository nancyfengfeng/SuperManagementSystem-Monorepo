from crawler.schemas.product import ProductItem
from crawler.schemas.promotion import PromotionItem

import re
from datetime import datetime


def parse_vtex_promo_dates(name):

    if not name:
        return None, None

    match = re.search(
        r"(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})",
        name
    )

    if not match:
        return None, None

    return (
        datetime.strptime(match.group(1), "%Y-%m-%d"),
        datetime.strptime(match.group(2), "%Y-%m-%d"),
    )


def parse_product(product: dict, store_code: str):
    items = product.get("items", [])

    if not items:
        return None, None

    item = items[0]

    images = item.get("images", [])
    image_url = images[0].get("imageUrl") if images else None

    regular_price = None
    sale_price = None
    promotion_item = None

    sellers = item.get("sellers", [])

    if sellers:
        offer = sellers[0].get("commertialOffer", {})

        regular_price = offer.get("ListPrice")
        sale_price = offer.get("Price")

        teasers = offer.get("teasers", [])

        for teaser in teasers:
            conditions = teaser.get("conditions", {})
            quantity = conditions.get("minimumQuantity")

            effects = teaser.get("effects", {})
            parameters = effects.get("parameters", [])

            promo_unit_price = None

            for parameter in parameters:
                if parameter.get("name") == "MaximumUnitPriceDiscount":
                    value = parameter.get("value")

                    if value is not None:
                        promo_unit_price = float(value) / 100

                    break

            if quantity and promo_unit_price is not None:
                total_price = round(promo_unit_price * quantity)

                start_time, end_time = parse_vtex_promo_dates(teaser.get("name"))

                promotion_item = PromotionItem(
                    quantity=quantity,
                    total_price=total_price,
                    start_time=start_time,
                    end_time=end_time,
                )

                break

    product_item = ProductItem(
        barcode=item.get("ean"),
        name=product.get("productName"),
        image_url=image_url,
        source_category_id=product.get("categoryId"),
        regular_price=regular_price,
        sale_price=sale_price,
        store_code=store_code,
        store_product_id=product.get("productId"),
    )

    return product_item, promotion_item