from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

from db import SessionLocal

from shared.models.product import Product
from shared.models.store_product import StoreProduct
from shared.models.category import Category
from shared.models.store_product_promotion import StoreProductPromotion

from services.product_serializer import serialize_promotions

router = APIRouter(prefix="/product")


def get_category_ids(db, category_id: int):

    ids = [category_id]

    children = (
        db.query(Category)
        .filter(
            Category.parent_id == category_id
        )
        .all()
    )

    for child in children:
        ids.extend(
            get_category_ids(
                db,
                child.id
            )
        )

    return ids



@router.get("/deals")
def get_deals(
    category_id: int | None = None,
    store_id: int | None = None,
    page: int = 1,
    limit: int = 50
):

    db = SessionLocal()

    try:

        query = (
            db.query(Product)
            .options(

                # store
                joinedload(Product.store_products)
                .joinedload(StoreProduct.store),

                # promotions
                joinedload(Product.store_products)
                .joinedload(StoreProduct.promotions),

                # category
                joinedload(Product.category),

            )
            .join(StoreProduct)
            .filter(
                Product.show_in_deals == True,
                Product.is_active == True,
                StoreProduct.is_active == True,

                or_(
                    # 情况 1：价格下降
                    StoreProduct.selling_price < StoreProduct.original_price,

                    # 情况 2：价格没有下降，但是有有效 promotion
                    StoreProduct.promotions.any(
                        StoreProductPromotion.is_active == True
                    )
                )
            )
            .distinct()
        )


        # =========================
        # Filter store
        # =========================

        if store_id:

            query = query.filter(
                StoreProduct.store_id == store_id
            )


        # =========================
        # Filter category
        # =========================

        if category_id:

            category_ids = get_category_ids(
                db,
                category_id
            )

            query = query.filter(
                Product.category_id.in_(
                    category_ids
                )
            )


        # =========================
        # Pagination
        # =========================

        total = query.count()

        products = (
            query
            .offset(
                (page - 1) * limit
            )
            .limit(limit)
            .all()
        )


        result = []


        # =========================
        # Products
        # =========================

        for product in products:

            stores = []

            prices = []


            for sp in product.store_products:

                if not sp.is_active:
                    continue


                selling_price = (
                    float(sp.selling_price)
                    if sp.selling_price is not None
                    else None
                )


                if selling_price is not None:

                    prices.append(
                        selling_price
                    )


                stores.append(
                    {
                        "store_id": sp.store_id,

                        "store_name": (
                            sp.store.name
                            if sp.store
                            else None
                        ),

                        "original_price": (
                            float(
                                sp.original_price
                            )
                            if sp.original_price
                            is not None
                            else None
                        ),

                        "selling_price":
                            selling_price,

                        "unit": sp.unit,

                        "in_stock":
                            sp.in_stock,

                        "promotions":
                            serialize_promotions(sp),
                    }
                )


            result.append(
                {
                    "barcode":
                        product.barcode,

                    "name":
                        product.name,

                    "image_url":
                        product.image_url,

                    "category": (
                        {
                            "id":
                                product.category.id,

                            "name":
                                product.category.name
                        }
                        if product.category
                        else None
                    ),

                    "lowest_price": (
                        min(prices)
                        if prices
                        else None
                    ),

                    "stores":
                        stores
                }
            )


        return {
            "page": page,
            "limit": limit,
            "total": total,
            "items": result
        }


    finally:

        db.close()


@router.get("/{barcode}")
def get_product_by_barcode(
    barcode: str
):

    db = SessionLocal()

    try:

        product = (
            db.query(Product)
            .options(

                # store
                joinedload(Product.store_products)
                .joinedload(StoreProduct.store),

                # promotions
                joinedload(Product.store_products)
                .joinedload(StoreProduct.promotions),

                # category
                joinedload(Product.category),

            )
            .filter(
                Product.barcode == barcode,
                Product.is_active == True
            )
            .first()
        )


        if not product:

            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )


        stores = []


        for sp in product.store_products:

            if not sp.is_active:
                continue


            stores.append(
                {
                    "store_id":
                        sp.store_id,

                    "store_name": (
                        sp.store.name
                        if sp.store
                        else None
                    ),

                    "original_price": (
                        float(
                            sp.original_price
                        )
                        if sp.original_price
                        is not None
                        else None
                    ),

                    "selling_price": (
                        float(
                            sp.selling_price
                        )
                        if sp.selling_price
                        is not None
                        else None
                    ),

                    "unit":
                        sp.unit,

                    "in_stock":
                        sp.in_stock,

                    "last_seen_at":
                        sp.last_seen_at,

                    "promotions":
                        serialize_promotions(sp),
                }
            )


        return {
            "id": product.id,
            "barcode":product.barcode,
            "name":product.name,
            "image_url":product.image_url,

            "category": (
                {
                    "id":
                        product.category.id,

                    "name":
                        product.category.name
                }
                if product.category
                else None
            ),

            "stores":
                stores
        }


    finally:

        db.close()


