from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, HTTPException
from db import SessionLocal
from sqlalchemy.orm import joinedload

from shared.models.product import Product
from shared.models.store_product import StoreProduct
from models.supplier import Supplier
from models.supplier_products import SupplierProduct
from models.invoices import Invoice
from models.supplier_price_history import SupplierPriceHistory

from services.product_serializer import serialize_promotions

router = APIRouter(prefix="/supplier-products", tags=["Supplier Products"])

@router.get("/{supplier_product_id}/price-history")
def get_supplier_product_price_history(supplier_product_id: int):
    db = SessionLocal()

    try:
        result = (
            db.query(SupplierProduct, Supplier)
            .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
            .filter(SupplierProduct.id == supplier_product_id)
            .first()
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="Supplier product not found"
            )

        supplier_product, supplier = result

        system_product = None

        if supplier_product.product_id:
            product = (
                db.query(Product)
                .options(
                    joinedload(Product.store_products)
                    .joinedload(StoreProduct.store),

                    joinedload(Product.store_products)
                    .joinedload(StoreProduct.promotions),

                    joinedload(Product.category)
                )
                .filter(
                    Product.id == supplier_product.product_id,
                    Product.is_active == True
                )
                .first()
            )

            if product:
                stores = []

                for sp in product.store_products:
                    if not sp.is_active:
                        continue

                    stores.append({
                        "store_id": sp.store_id,
                        "store_name": sp.store.name if sp.store else None,
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
                        "promotions": serialize_promotions(sp)
                    })

                system_product = {
                    "id": product.id,
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
                    "stores": stores
                }

        rows = (
            db.query(SupplierPriceHistory, Invoice)
            .join(Invoice, SupplierPriceHistory.invoice_id == Invoice.id)
            .filter(
                SupplierPriceHistory.supplier_product_id == supplier_product_id,
                Invoice.document_type == "invoice",
                SupplierPriceHistory.net_unit_price > 0
            )
            .order_by(
                Invoice.invoice_date.asc(),
                Invoice.id.asc(),
                SupplierPriceHistory.id.asc()
            )
            .all()
        )

        history = []

        for price, invoice in rows:
            value = price.net_unit_price.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            history.append({
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date.isoformat(),
                "price": str(value),
                "unit_price": str(price.unit_price),
                "discount_per_unit": str(price.discount_per_unit),
                "tax_rate": (
                    str(price.tax_rate)
                    if price.tax_rate is not None
                    else None
                ),
                "currency": price.currency
            })

        prices = [Decimal(item["price"]) for item in history]

        return {
            "code": 200,
            "data": {
                "supplier_product": {
                    "id": supplier_product.id,
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name,
                    "description": supplier_product.description,
                    "supplier_product_code": supplier_product.supplier_product_code,
                    "barcode": supplier_product.barcode,
                    "product_id": supplier_product.product_id
                },

                "system_product": system_product,

                "summary": {
                    "current_price": str(prices[-1]) if prices else None,
                    "min_price": str(min(prices)) if prices else None,
                    "max_price": str(max(prices)) if prices else None
                },

                "history": history
            }
        }

    finally:
        db.close()