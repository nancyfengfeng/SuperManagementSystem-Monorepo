from fastapi import APIRouter, HTTPException,Query
from sqlalchemy import func,or_


from db import SessionLocal
from models.supplier import Supplier
from models.supplier_products import SupplierProduct
from models.invoices import Invoice
from models.supplier_price_history import SupplierPriceHistory
from schemas.supplier import (
    SupplierCreate,
    SupplierLink,
)

router = APIRouter(prefix="/supplier")


@router.post("")
def create_supplier(data: SupplierCreate):
    db = SessionLocal()

    try:
        name = data.name.strip()

        if not name:
            raise HTTPException(
                status_code=400,
                detail="name is required"
            )

        exist = (
            db.query(Supplier)
            .filter(Supplier.name == name)
            .first()
        )

        if exist:
            raise HTTPException(
                status_code=400,
                detail="supplier already exists"
            )

        supplier = Supplier(
            name=name
        )

        db.add(supplier)
        db.commit()
        db.refresh(supplier)

        return {
            "code": 200,
            "data": {
                "id": supplier.id,
                "name": supplier.name
            }
        }

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()


@router.get("")
def fetch_suppliers():
    db = SessionLocal()

    try:
        suppliers = db.query(
            Supplier
        ).all()

        return {
            "code": 200,
            "data": [
                {
                    "id": s.id,
                    "name": s.name,
                    "legal_name": s.legal_name,
                    "tax_id": s.tax_id,
                    "is_active": s.is_active,
                }
                for s in suppliers
            ]
        }

    finally:
        db.close()


@router.patch("/{supplier_id}/link")
def link_supplier(
    supplier_id: int,
    data: SupplierLink,
):
    db = SessionLocal()

    try:
        legal_name = data.legal_name.strip()
        tax_id = data.tax_id.strip()

        if not legal_name:
            raise HTTPException(
                status_code=400,
                detail="legal_name is required"
            )

        if not tax_id:
            raise HTTPException(
                status_code=400,
                detail="tax_id is required"
            )

        # 找到要关联的 Supplier
        supplier = (
            db.query(Supplier)
            .filter(
                Supplier.id == supplier_id
            )
            .first()
        )

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail="supplier not found"
            )

        # 这个 tax_id 是否已经被其他 Supplier 使用
        tax_id_exist = (
            db.query(Supplier)
            .filter(
                Supplier.tax_id == tax_id,
                Supplier.id != supplier_id
            )
            .first()
        )

        if tax_id_exist:
            raise HTTPException(
                status_code=409,
                detail=(
                    "tax_id is already linked "
                    "to another supplier"
                )
            )

        # 当前 Supplier 已经绑定了另外一个税号
        if (
            supplier.tax_id
            and supplier.tax_id != tax_id
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "supplier is already linked "
                    "to another tax_id"
                )
            )

        supplier.legal_name = legal_name
        supplier.tax_id = tax_id

        db.commit()
        db.refresh(supplier)

        return {
            "code": 200,
            "data": {
                "id": supplier.id,
                "name": supplier.name,
                "legal_name": supplier.legal_name,
                "tax_id": supplier.tax_id,
                "is_active": supplier.is_active,
            }
        }

    except Exception as e:
        db.rollback()
        raise e

    finally:
        db.close()


@router.get("/overview")
def fetch_supplier_overview(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None)
):
    db = SessionLocal()

    try:
        filters = [Supplier.is_active == True]

        if keyword:
            keyword = keyword.strip()
            if keyword:
                search = f"%{keyword}%"
                filters.append(
                    or_(
                        Supplier.name.ilike(search),
                        Supplier.legal_name.ilike(search),
                        Supplier.tax_id.ilike(search)
                    )
                )

        total = (
            db.query(func.count(Supplier.id))
            .filter(*filters)
            .scalar()
        ) or 0

        product_stats = (
            db.query(
                SupplierProduct.supplier_id.label("supplier_id"),
                func.count(SupplierProduct.id).label("product_count")
            )
            .filter(SupplierProduct.is_active == True)
            .group_by(SupplierProduct.supplier_id)
            .subquery()
        )

        invoice_stats = (
            db.query(
                Invoice.supplier_id.label("supplier_id"),
                func.count(Invoice.id).label("invoice_count"),
                func.max(Invoice.invoice_date).label("last_invoice_date")
            )
            .filter(Invoice.document_type == "invoice")
            .group_by(Invoice.supplier_id)
            .subquery()
        )

        rows = (
            db.query(
                Supplier,
                product_stats.c.product_count,
                invoice_stats.c.invoice_count,
                invoice_stats.c.last_invoice_date
            )
            .outerjoin(
                product_stats,
                product_stats.c.supplier_id == Supplier.id
            )
            .outerjoin(
                invoice_stats,
                invoice_stats.c.supplier_id == Supplier.id
            )
            .filter(*filters)
            .order_by(Supplier.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "code": 200,
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": [
                {
                    "id": supplier.id,
                    "name": supplier.name,
                    "legal_name": supplier.legal_name,
                    "tax_id": supplier.tax_id,
                    "product_count": product_count or 0,
                    "invoice_count": invoice_count or 0,
                    "last_invoice_date": (
                        last_invoice_date.isoformat()
                        if last_invoice_date else None
                    )
                }
                for supplier, product_count, invoice_count, last_invoice_date in rows
            ]
        }

    finally:
        db.close()


        

@router.get("/{supplier_id}/detail")
def get_supplier_detail(supplier_id: int):
    db = SessionLocal()
    try:
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        product_count = (
            db.query(func.count(SupplierProduct.id))
            .filter(
                SupplierProduct.supplier_id == supplier_id,
                SupplierProduct.is_active == True
            )
            .scalar()
        ) or 0

        invoice_stats = (
            db.query(
                func.count(Invoice.id),
                func.max(Invoice.invoice_date)
            )
            .filter(
                Invoice.supplier_id == supplier_id,
                Invoice.document_type == "invoice"
            )
            .first()
        )

        return {
            "code": 200,
            "data": {
                "id": supplier.id,
                "name": supplier.name,
                "legal_name": supplier.legal_name,
                "tax_id": supplier.tax_id,
                "is_active": supplier.is_active,
                "product_count": product_count,
                "invoice_count": invoice_stats[0] or 0,
                "last_invoice_date": invoice_stats[1].isoformat() if invoice_stats[1] else None
            }
        }
    finally:
        db.close()

@router.get("/{supplier_id}/invoices")
def get_supplier_invoices(
    supplier_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    db = SessionLocal()
    try:
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        total = (
            db.query(func.count(Invoice.id))
            .filter(
                Invoice.supplier_id == supplier_id,
                Invoice.document_type == "invoice"
            )
            .scalar()
        ) or 0

        product_stats = (
            db.query(
                SupplierPriceHistory.invoice_id.label("invoice_id"),
                func.count(SupplierPriceHistory.id).label("product_count")
            )
            .group_by(SupplierPriceHistory.invoice_id)
            .subquery()
        )

        rows = (
            db.query(Invoice, product_stats.c.product_count)
            .outerjoin(
                product_stats,
                product_stats.c.invoice_id == Invoice.id
            )
            .filter(
                Invoice.supplier_id == supplier_id,
                Invoice.document_type == "invoice"
            )
            .order_by(
                Invoice.invoice_date.desc(),
                Invoice.id.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "code": 200,
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": [
                {
                    "id": invoice.id,
                    "invoice_key": invoice.invoice_key,
                    "invoice_number": invoice.invoice_number,
                    "document_type": invoice.document_type,
                    "invoice_date": invoice.invoice_date.isoformat(),
                    "product_count": product_count or 0
                }
                for invoice, product_count in rows
            ]
        }
    finally:
        db.close()