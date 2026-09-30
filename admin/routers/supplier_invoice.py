from pathlib import Path
from fastapi import (APIRouter,File,UploadFile,Query)
from db import SessionLocal
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import desc


from shared.models.product import Product
from models.supplier import Supplier
from models.supplier_products import SupplierProduct
from models.invoices import Invoice
from models.supplier_price_history import SupplierPriceHistory

from shared.models.product import Product

from schemas.supplier_invoice import (ProductMatchRequest,SupplierProductSaveRequest,InvoiceImportRequest)

from services.xml_invoice_parser import (
    parse_invoice_info,
)


router = APIRouter(
    prefix="/supplier-invoices",
    tags=["Supplier Invoices"],
)


@router.post("/read-xml")
async def read_xml_files(
    files: list[UploadFile] = File(...)
):
    results = []

    for file in files:

        if not file.filename.lower().endswith(".xml"):
            continue

        try:
            xml_data = await file.read()

            info = parse_invoice_info(
                xml_data
            )

            results.append({
                "filename": Path(
                    file.filename
                ).name,

                "success": True,

                **info,
            })

        except Exception as exc:

            results.append({
                "filename": Path(
                    file.filename
                ).name,

                "success": False,

                "error": str(exc),
            })

    return {
        "success": True,
        "total": len(results),
        "files": results,
    }


def _is_invalid_barcode(code: str) -> bool:
    value = code.strip()

    if not value:
        return True

    # 例如 00000000000000
    if set(value) == {"0"}:
        return True

    return False


@router.post("/match-products")
def match_products(data: ProductMatchRequest):
    db = SessionLocal()

    try:
        results = []
        seen = set()

        for file in data.files:
            if not file.supplier_tax_id:
                continue

            supplier = (
                db.query(Supplier)
                .filter(Supplier.tax_id == file.supplier_tax_id)
                .first()
            )

            if not supplier:
                continue

            for item in file.products:
                supplier_code = item.supplier_product_code
                key = (supplier.id, supplier_code)

                if supplier_code and key in seen:
                    continue

                if supplier_code:
                    seen.add(key)

                # 1. 已经存在 SupplierProduct
                existing = None

                if supplier_code:
                    existing = (
                        db.query(SupplierProduct)
                        .filter(
                            SupplierProduct.supplier_id == supplier.id,
                            SupplierProduct.supplier_product_code == supplier_code
                        )
                        .first()
                    )

                if existing:
                    product = None

                    if existing.product_id:
                        product = (
                            db.query(Product)
                            .filter(Product.id == existing.product_id)
                            .first()
                        )

                    # 优先使用 SupplierProduct 已保存的 barcode
                    # 如果没有，但已经关联 Product，则使用 Product.barcode
                    barcode = (
                        existing.barcode
                        or (product.barcode if product else None)
                    )

                    results.append({
                        "supplier_id": supplier.id,
                        "supplier_name": supplier.name,
                        "description": item.description,
                        "supplier_product_code": supplier_code,
                        "commercial_codes": item.commercial_codes,
                        "barcode": barcode,
                        "product_id": existing.product_id,
                        "product_name": product.name if product else None,

                        # 只要已经有 barcode，就不需要再进手动 Dialog
                        "matched": bool(barcode),

                        "match_source": (
                            "supplier_product"
                            if barcode
                            else None
                        ),
                    })

                    continue

                # 2. SupplierProduct 不存在
                # 先尝试从 XML 找 barcode
                xml_barcode = _extract_barcode(
                    item.commercial_codes,
                    supplier_code
                )

                # 3. 再尝试用 XML 代码匹配系统 Product
                valid_codes = [
                    code
                    for code in item.commercial_codes
                    if not _is_invalid_barcode(code)
                ]

                matched_product = None

                if valid_codes:
                    matched_product = (
                        db.query(Product)
                        .filter(Product.barcode.in_(valid_codes))
                        .first()
                    )

                # Product 找到时使用系统 barcode
                # 找不到时，只要 XML 本身有 barcode 也可以
                barcode = (
                    matched_product.barcode
                    if matched_product
                    else xml_barcode
                )

                results.append({
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name,
                    "description": item.description,
                    "supplier_product_code": supplier_code,
                    "commercial_codes": item.commercial_codes,
                    "barcode": barcode,
                    "product_id": (
                        matched_product.id
                        if matched_product
                        else None
                    ),
                    "product_name": (
                        matched_product.name
                        if matched_product
                        else None
                    ),

                    # 有 barcode 就算完成，不要求一定有 product_id
                    "matched": bool(barcode),

                    "match_source": (
                        "barcode"
                        if matched_product
                        else "xml_barcode"
                        if xml_barcode
                        else None
                    ),
                })

        return {
            "code": 200,
            "total": len(results),
            "data": results,
        }

    finally:
        db.close()


def _extract_barcode(
    commercial_codes: list[str],
    supplier_product_code: str | None
):
    for code in commercial_codes:
        value = code.strip()

        if not value:
            continue

        if (
            supplier_product_code
            and value == supplier_product_code
        ):
            continue

        if set(value) == {"0"}:
            continue

        return value

    return None


@router.post("/save-products")
def save_supplier_products(data: SupplierProductSaveRequest):
    db = SessionLocal()

    try:
        saved = 0
        updated = 0

        for item in data.products:
            supplier_code = item.supplier_product_code
            if not supplier_code:
                continue

            # 先从 XML 找 barcode
            xml_barcode = _extract_barcode(
                item.commercial_codes,
                supplier_code
            )

            # 优先使用用户扫描得到的 barcode
            barcode = item.product_barcode or xml_barcode

            # 如果已经关联 Product，但还没有 barcode，
            # 直接从 Product 表补 barcode
            if not barcode and item.product_id is not None:
                product = (
                    db.query(Product)
                    .filter(Product.id == item.product_id)
                    .first()
                )

                if product:
                    barcode = product.barcode

            existing = (
                db.query(SupplierProduct)
                .filter(
                    SupplierProduct.supplier_id == item.supplier_id,
                    SupplierProduct.supplier_product_code == supplier_code
                )
                .first()
            )

            if existing:
                existing.description = item.description

                if barcode:
                    existing.barcode = barcode

                if item.product_id is not None:
                    existing.product_id = item.product_id

                updated += 1

            else:
                supplier_product = SupplierProduct(
                    supplier_id=item.supplier_id,
                    supplier_product_code=supplier_code,
                    description=item.description,
                    barcode=barcode,
                    product_id=item.product_id,
                    is_active=True
                )

                db.add(supplier_product)
                saved += 1

        db.commit()

        return {
            "code": 200,
            "saved": saved,
            "updated": updated
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def _parse_invoice_date(
    value: str
) -> datetime:

    dt = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00"
        )
    )

    # 当前 Invoice.invoice_date 是 DateTime，
    # 没有 timezone=True
    if dt.tzinfo is not None:
        dt = dt.replace(
            tzinfo=None
        )

    return dt

@router.post("/import")
def import_invoices(
    data: InvoiceImportRequest
):
    db = SessionLocal()

    try:
        imported_invoices = 0
        skipped_invoices = 0
        saved_prices = 0

        price_changes = []

        # 按日期从旧到新导入
        files = sorted(
            data.files,
            key=lambda file:
                _parse_invoice_date(
                    file.invoice_date
                )
        )

        for file in files:

            # ----------------------------
            # 1. 防止重复导入
            # ----------------------------

            existing_invoice = (
                db.query(Invoice)
                .filter(
                    Invoice.invoice_key ==
                    file.invoice_key
                )
                .first()
            )

            if existing_invoice:
                skipped_invoices += 1
                continue

            # ----------------------------
            # 2. 根据 tax_id 找 Supplier
            # ----------------------------

            supplier = (
                db.query(Supplier)
                .filter(
                    Supplier.tax_id ==
                    file.supplier_tax_id
                )
                .first()
            )

            if not supplier:
                continue

            invoice_date = (
                _parse_invoice_date(
                    file.invoice_date
                )
            )

            # ----------------------------
            # 3. 保存 Invoice
            # ----------------------------

            invoice = Invoice(
                supplier_id=
                    supplier.id,

                invoice_key=
                    file.invoice_key,

                invoice_number=
                    file.invoice_number,

                document_type=
                    file.type,

                invoice_date=
                    invoice_date,
            )

            db.add(invoice)

            # 取得 invoice.id
            db.flush()

            imported_invoices += 1

            # ----------------------------
            # 4. credit note / debit note
            #    暂时不作为新价格
            # ----------------------------

            if file.type != "invoice":
                continue

            # ----------------------------
            # 5. 正常发票商品
            # ----------------------------

            for item in file.products:

                if not item.supplier_product_code:
                    continue

                supplier_product = (
                    db.query(
                        SupplierProduct
                    )
                    .filter(
                        SupplierProduct.supplier_id
                        == supplier.id,

                        SupplierProduct.supplier_product_code
                        ==
                        item.supplier_product_code
                    )
                    .first()
                )

                if not supplier_product:
                    continue

                new_price = Decimal(
                    item.net_unit_price
                )

                # ------------------------
                # 找这张发票之前的最近价格
                # ------------------------

                previous = (
                    db.query(
                        SupplierPriceHistory
                    )
                    .join(
                        Invoice,
                        SupplierPriceHistory.invoice_id
                        == Invoice.id
                    )
                    .filter(
                        SupplierPriceHistory.supplier_product_id
                        == supplier_product.id,

                        Invoice.invoice_date
                        < invoice_date,

                        Invoice.document_type
                        == "invoice",
                    )
                    .order_by(
                        desc(
                            Invoice.invoice_date
                        ),
                        desc(
                            SupplierPriceHistory.id
                        )
                    )
                    .first()
                )

                old_price = (
                    previous.net_unit_price
                    if previous
                    else None
                )

                # ------------------------
                # 保存这次价格
                # ------------------------

                history = (
                    SupplierPriceHistory(
                        supplier_product_id=
                            supplier_product.id,

                        invoice_id=
                            invoice.id,

                        unit_price=
                            Decimal(
                                item.unit_price
                            ),

                        discount_per_unit=
                            Decimal(
                                item.discount_per_unit
                            ),

                        net_unit_price=
                            new_price,

                        tax_rate=(
                            Decimal(
                                item.tax_rate
                            )
                            if item.tax_rate
                            is not None
                            else None
                        ),

                        currency=
                            file.currency,
                    )
                )

                db.add(history)

                # flush，后面的发票可以看到
                # 本次刚保存的历史记录
                db.flush()

                saved_prices += 1

                # ------------------------
                # 6. 计算涨跌
                # ------------------------

                if old_price is None:
                    status = "new"
                    difference = None
                    percent = None

                else:
                    difference = (
                        new_price -
                        old_price
                    )

                    if difference > 0:
                        status = "increase"

                    elif difference < 0:
                        status = "decrease"

                    else:
                        status = "same"

                    if old_price != 0:
                        percent = (
                            difference /
                            old_price *
                            Decimal("100")
                        )
                    else:
                        percent = None

                price_changes.append({
                    "supplier_id":
                        supplier.id,

                    "supplier_name":
                        supplier.name,

                    "supplier_product_id":
                        supplier_product.id,

                    "supplier_product_code":
                        supplier_product.supplier_product_code,

                    "description":
                        supplier_product.description,

                    "product_id":
                        supplier_product.product_id,

                    "old_price": (
                        str(old_price)
                        if old_price
                        is not None
                        else None
                    ),

                    "new_price":
                        str(new_price),

                    "difference": (
                        str(difference)
                        if difference
                        is not None
                        else None
                    ),

                    "percent": (
                        str(percent)
                        if percent
                        is not None
                        else None
                    ),

                    "currency":
                        file.currency,

                    "status":
                        status,

                    "invoice_date":
                        file.invoice_date,
                })

        db.commit()

        return {
            "code": 200,

            "imported_invoices":
                imported_invoices,

            "skipped_invoices":
                skipped_invoices,

            "saved_prices":
                saved_prices,

            "price_changes":
                price_changes,
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def _build_price_history(db):
    rows = (
        db.query(SupplierPriceHistory, Invoice, SupplierProduct, Supplier)
        .join(Invoice, SupplierPriceHistory.invoice_id == Invoice.id)
        .join(SupplierProduct, SupplierPriceHistory.supplier_product_id == SupplierProduct.id)
        .join(Supplier, SupplierProduct.supplier_id == Supplier.id)
        .filter(Invoice.document_type == "invoice")
        .order_by(
            SupplierPriceHistory.supplier_product_id.asc(),
            Invoice.invoice_date.asc(),
            Invoice.id.asc(),
            SupplierPriceHistory.id.asc(),
        )
        .all()
    )

    results = []
    previous_prices = {}

    for history, invoice, supplier_product, supplier in rows:
        key = supplier_product.id
        new_price = history.net_unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        old_price = previous_prices.get(key)

        # 0 或负数不作为有效进货价格
        if new_price is None or new_price <= 0:
            continue


        if old_price is None:
            status = "new"
            difference = percent = None
        else:
            difference = new_price - old_price
            status = "increase" if difference > 0 else "decrease" if difference < 0 else "same"
            percent = difference / old_price * Decimal("100") if difference != 0 and old_price != 0 else Decimal("0")

        results.append({
            "supplier_id": supplier.id,
            "supplier_name": supplier.name,
            "supplier_product_id": supplier_product.id,
            "supplier_product_code": supplier_product.supplier_product_code,
            "description": supplier_product.description,
            "product_id": supplier_product.product_id,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat(),
            "old_price": str(old_price) if old_price is not None else None,
            "new_price": str(new_price),
            "difference": str(difference) if difference is not None else None,
            "percent": str(percent) if percent is not None else None,
            "currency": history.currency,
            "status": status,
        })

        previous_prices[key] = new_price

    return results

@router.get("/price-summary")
def get_price_summary():
    db = SessionLocal()

    try:
        results = _build_price_history(db)

        return {
            "code": 200,
            "data": {
                "increase": sum(1 for item in results if item["status"] == "increase"),
                "decrease": sum(1 for item in results if item["status"] == "decrease"),
                "new": sum(1 for item in results if item["status"] == "new"),
            }
        }
    finally:
        db.close()


@router.get("/price-history")
def get_price_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
):
    db = SessionLocal()

    try:
        results = _build_price_history(db)

        if status:
            results = [item for item in results if item["status"] == status]

        results.sort(key=lambda item: item["invoice_date"], reverse=True)

        total = len(results)
        start = (page - 1) * page_size

        return {
            "code": 200,
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": results[start:start + page_size],
        }
    finally:
        db.close()


@router.get("/{invoice_id}/products")
def get_invoice_products(invoice_id: int):
    db = SessionLocal()
    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        rows = (
            db.query(SupplierPriceHistory, SupplierProduct)
            .join(
                SupplierProduct,
                SupplierPriceHistory.supplier_product_id == SupplierProduct.id
            )
            .filter(SupplierPriceHistory.invoice_id == invoice_id)
            .order_by(SupplierProduct.description.asc())
            .all()
        )

        return {
            "code": 200,
            "data": [
                {
                    "supplier_product_id": product.id,
                    "product_id": product.product_id,
                    "supplier_product_code": product.supplier_product_code,
                    "barcode": product.barcode,
                    "description": product.description,
                    "unit_price": str(history.unit_price),
                    "discount_per_unit": str(history.discount_per_unit),
                    "net_unit_price": str(history.net_unit_price),
                    "tax_rate": str(history.tax_rate) if history.tax_rate is not None else None,
                    "currency": history.currency
                }
                for history, product in rows
            ]
        }
    finally:
        db.close()