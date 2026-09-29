from fastapi import APIRouter
from sqlalchemy.orm import joinedload

from db import SessionLocal

from shared.models.product import Product
from shared.models.store_product import StoreProduct
from shared.models.store_product_promotion import StoreProductPromotion
from shared.models.category import Category


router = APIRouter(prefix="/promotions")


# ============================================
# 获取当前分类以及所有子分类 ID
# ============================================

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


# ============================================
# Serialize promotions
# ============================================

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


# ============================================
# GET Promotions
# ============================================

@router.get("/")
def get_promotions(
    category_id: int | None = None,
    store_id: int | None = None,
    page: int = 1,
    limit: int = 50
):

    db = SessionLocal()

    try:

        # ====================================
        # Base Query
        # ====================================

        query = (
            db.query(Product)

            .options(

                # Store
                joinedload(Product.store_products)
                .joinedload(StoreProduct.store),

                # Promotions
                joinedload(Product.store_products)
                .joinedload(StoreProduct.promotions),

                # Category
                joinedload(Product.category),
            )

            # Product -> StoreProduct
            .join(
                StoreProduct,
                StoreProduct.product_id == Product.id
            )

            # StoreProduct -> Promotion
            .join(
                StoreProductPromotion,
                StoreProductPromotion.store_product_id
                == StoreProduct.id
            )

            .filter(

                # 商品必须 active
                Product.is_active == True,

                # StoreProduct 必须 active
                StoreProduct.is_active == True,

                # Promotion 必须 active
                StoreProductPromotion.is_active == True,
            )

            .distinct()
        )


        # ====================================
        # Store Filter
        # ====================================

        if store_id:

            query = query.filter(
                StoreProduct.store_id == store_id
            )


        # ====================================
        # Category Filter
        # 包含当前分类下面所有子分类
        # ====================================

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


        # ====================================
        # Total
        # ====================================

        total = query.count()


        # ====================================
        # Pagination
        # ====================================

        products = (
            query

            .offset(
                (page - 1) * limit
            )

            .limit(limit)

            .all()
        )


        # ====================================
        # Serialize Products
        # ====================================

        result = []


        for product in products:

            stores = []


            for sp in product.store_products:

                # StoreProduct inactive 不返回
                if not sp.is_active:
                    continue


                # 如果指定 store_id
                # 返回结果也只保留该 store
                if (
                    store_id is not None
                    and sp.store_id != store_id
                ):
                    continue


                promotions = serialize_promotions(sp)


                # 这个 store 没有 active promotion
                # 不返回
                if not promotions:
                    continue


                stores.append(
                    {
                        "store_id": sp.store_id,

                        "store_name": (
                            sp.store.name
                            if sp.store
                            else None
                        ),

                        "original_price": (
                            float(sp.original_price)
                            if sp.original_price is not None
                            else None
                        ),

                        "selling_price": (
                            float(sp.selling_price)
                            if sp.selling_price is not None
                            else None
                        ),

                        "unit": sp.unit,

                        "in_stock": sp.in_stock,

                        "last_seen_at": sp.last_seen_at,

                        "promotions": promotions,
                    }
                )


            # 理论上 query 已经保证存在 promotion
            # 这里再保护一次
            if not stores:
                continue


            result.append(
                {
                    "barcode": product.barcode,

                    "name": product.name,

                    "image_url": product.image_url,

                    "category": (
                        {
                            "id": product.category.id,
                            "name": product.category.name
                        }
                        if product.category
                        else None
                    ),

                    "stores": stores,
                }
            )


        # ====================================
        # Response
        # ====================================

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "items": result
        }


    finally:

        db.close()