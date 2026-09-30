from decimal import Decimal, ROUND_HALF_UP
from fastapi import APIRouter, HTTPException
from db import SessionLocal
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func

from shared.models.product import Product
from shared.models.store_product import StoreProduct
from models.supplier import Supplier
from models.supplier_products import SupplierProduct
from models.invoices import Invoice
from models.supplier_price_history import SupplierPriceHistory

from schemas.supplier_product import BarcodeUpdate

from services.product_serializer import serialize_promotions

router = APIRouter(prefix="/supplier-products", tags=["Supplier Products"])



@router.get("/barcode-review")
def get_barcode_review(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    supplier_id: int | None = None
):
    db = SessionLocal()

    try:
        query = (
            db.query(SupplierProduct, Supplier)
            .join(
                Supplier,
                Supplier.id == SupplierProduct.supplier_id
            )
            .filter(
                SupplierProduct.is_active.is_(True),
                or_(
                    SupplierProduct.barcode.is_(None),
                    func.trim(SupplierProduct.barcode) == ""
                )
            )
        )

        if supplier_id:
            query = query.filter(
                SupplierProduct.supplier_id == supplier_id
            )

        if keyword:
            keyword = keyword.strip()

            if keyword:
                pattern = f"%{keyword}%"

                query = query.filter(
                    or_(
                        SupplierProduct.description.ilike(pattern),
                        SupplierProduct.supplier_product_code.ilike(pattern),
                        Supplier.name.ilike(pattern),
                        Supplier.legal_name.ilike(pattern)
                    )
                )

        total = query.count()

        rows = (
            query
            .order_by(SupplierProduct.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        data = [
            {
                "id": item.id,
                "supplier_id": item.supplier_id,
                "supplier_name": supplier.name,
                "supplier_legal_name": supplier.legal_name,
                "supplier_product_code": item.supplier_product_code,
                "description": item.description,
                "barcode": item.barcode,
                "product_id": item.product_id
            }
            for item, supplier in rows
        ]

        return {
            "code": 200,
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": data
        }

    finally:
        db.close()


@router.post("/sync-missing-barcodes")
def sync_missing_barcodes():
    db = SessionLocal()

    try:
        rows = (
            db.query(SupplierProduct, Product)
            .join(
                Product,
                Product.id == SupplierProduct.product_id
            )
            .filter(
                SupplierProduct.product_id.is_not(None),
                SupplierProduct.barcode.is_(None),
                Product.barcode.is_not(None)
            )
            .all()
        )

        updated = 0

        for supplier_product, product in rows:
            barcode = str(product.barcode or "").strip()

            if not barcode:
                continue

            supplier_product.barcode = barcode
            updated += 1

        db.commit()

        return {
            "code": 200,
            "data": {
                "updated": updated
            }
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()       


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

@router.get("/by-product/{product_id}")
def get_supplier_products_by_product(product_id: int):
    db = SessionLocal()
    try:
        supplier_products = (
            db.query(SupplierProduct)
            .filter(
                SupplierProduct.product_id == product_id,
                SupplierProduct.is_active.is_(True)
            )
            .all()
        )

        result = []

        for item in supplier_products:
            supplier = (
                db.query(Supplier)
                .filter(Supplier.id == item.supplier_id)
                .first()
            )

            latest_price = (
                db.query(SupplierPriceHistory)
                .join(
                    Invoice,
                    Invoice.id == SupplierPriceHistory.invoice_id
                )
                .filter(
                    SupplierPriceHistory.supplier_product_id == item.id,
                    Invoice.document_type == "invoice",
                    SupplierPriceHistory.net_unit_price > 0
                )
                .order_by(
                    Invoice.invoice_date.desc(),
                    SupplierPriceHistory.id.desc()
                )
                .first()
            )

            result.append({
                "id": item.id,
                "supplier_id": item.supplier_id,
                "supplier_name": supplier.name if supplier else None,
                "supplier_legal_name": supplier.legal_name if supplier else None,
                "supplier_product_code": item.supplier_product_code,
                "barcode": item.barcode,
                "description": item.description,
                "current_price": (
                    str(latest_price.net_unit_price)
                    if latest_price else None
                )
            })

        return {
            "code": 200,
            "data": result
        }

    finally:
        db.close()


@router.put("/{supplier_product_id}/barcode")
def update_supplier_product_barcode(
    supplier_product_id: int,
    data: BarcodeUpdate
):
    db = SessionLocal()

    try:
        item = (
            db.query(SupplierProduct)
            .filter(SupplierProduct.id == supplier_product_id)
            .first()
        )

        if not item:
            raise HTTPException(
                status_code=404,
                detail="Supplier product not found"
            )

        barcode = data.barcode.strip()

        if not barcode:
            raise HTTPException(
                status_code=400,
                detail="Barcode is required"
            )

        product = (
            db.query(Product)
            .filter(Product.barcode == barcode)
            .first()
        )

        item.barcode = barcode

        if product:
            item.product_id = product.id
        else:
            item.product_id = None

        db.commit()
        db.refresh(item)

        return {
            "code": 200,
            "data": {
                "id": item.id,
                "barcode": item.barcode,
                "product_id": item.product_id,
                "product_name": product.name if product else None,
                "matched": product is not None
            }
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

