def serialize_promotions(store_product):

    promotions = []

    for promotion in store_product.promotions:

        if not promotion.is_active:
            continue

        promotions.append(
            {
                "id": promotion.id,
                "quantity": promotion.quantity,
                "total_price": (
                    float(promotion.total_price)
                    if promotion.total_price is not None
                    else None
                ),
                "start_time": promotion.start_time,
                "end_time": promotion.end_time,
                "is_active": promotion.is_active,
            }
        )

    return promotions