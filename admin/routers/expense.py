from fastapi import APIRouter, Request,Query,HTTPException,Depends
from db import SessionLocal
from datetime import datetime, date, timedelta

from utils.db_utils import apply_if_changed

from models.expense import Expense, ExpensePayment
from schemas.expense import ExpenseCreate

from sqlalchemy import func

from utils.time import cr_today

router = APIRouter(prefix="/expense", tags=["Expense"])

def calculate_payment(total_amount: float, payments: list):
    """
    return:
        payment_status, paid_amount, payment_date
    """
    paid_amount = sum(p.amount or 0 for p in payments)
    # 防止负数
    if paid_amount < 0:
        raise ValueError("invalid payment amount")
    # pending
    if paid_amount <= 0:
        return "pending", paid_amount, None
    # paid
    if abs(paid_amount - total_amount) < 0.0001:
        return "paid", paid_amount, date.today()
    # partial
    return "partial", paid_amount, None


@router.post("/")
def create_expense(request: Request, data: ExpenseCreate):
    db = SessionLocal()

    try:
        user_id = request.state.user

        # 1️⃣ 校验付款数据
        for p in data.payments:
            if p.amount <= 0:
                return {"code": 400, "msg": "payment amount must > 0"}

        # 2️⃣ 防止超付 + 计算状态
        payment_status, paid_amount, payment_date = calculate_payment(
            data.total_amount,
            data.payments
        )

        if paid_amount > data.total_amount:
            return {"code": 400, "msg": "payments total cannot exceed total_amount"}

        # 3️⃣ 创建主表
        expense = Expense(
            user_id=user_id,
            supplier_id=data.supplier_id,
            total_amount=data.total_amount,
            date=data.date,
            payment_status=payment_status,
            payment_date=payment_date
        )

        # 4️⃣ 创建子表
        expense.payments = [
            ExpensePayment(
                method=p.method,
                amount=p.amount
            )
            for p in data.payments
        ]

        # 5️⃣ 保存
        db.add(expense)
        db.commit()
        db.refresh(expense)

        return {
            "code": 200,
            "msg": "expense created successfully",
            "expense_id": expense.id,
            "payment_status": payment_status
        }

    except Exception as e:
        db.rollback()
        return {"code": 500, "msg": str(e)}

    finally:
        db.close()


@router.get("/")
def get_expenses(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    expense_date: date | None = Query(None, alias="date"),
    supplier_id: int | None = Query(None),
    payment_status: str | None = Query(None)
):
    db = SessionLocal()

    try:
        user = request.state.user

        query = (
            db.query(Expense)
            .filter(Expense.user_id == user)
        )

        # 日期筛选
        if expense_date:
            query = query.filter(Expense.date == expense_date)

        # ⭐ 供应商筛选
        if supplier_id:
            query = query.filter(Expense.supplier_id == supplier_id)

        # ⭐ 状态筛选
        if payment_status:
            query = query.filter(Expense.payment_status == payment_status)

        total = query.count()

        expenses = (
            query
            .order_by(Expense.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        result = [
            {
                "id": e.id,
                "supplier_id": e.supplier_id,
                "total_amount": e.total_amount,
                "date": e.date,
                "payment_date": e.payment_date,
                "payment_status": e.payment_status,
                "payments": [
                    {
                        "method": p.method,
                        "amount": p.amount
                    }
                    for p in e.payments
                ]
            }
            for e in expenses
        ]

        return {
            "code": 200,
            "data": result,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }

    finally:
        db.close()


@router.put("/{expense_id}")
def update_expense(request: Request, expense_id: int, data: ExpenseCreate):
    db = SessionLocal()

    try:
        user_id = request.state.user

        expense = (
            db.query(Expense)
            .filter(
                Expense.id == expense_id,
                Expense.user_id == user_id
            )
            .first()
        )

        if not expense:
            return {"code": 404, "msg": "not found"}

        # 1️⃣ 校验付款
        for p in data.payments:
            if p.amount <= 0:
                return {"code": 400, "msg": "payment amount must > 0"}

        # 2️⃣ 统一计算状态
        payment_status, paid_amount, payment_date = calculate_payment(
            data.total_amount,
            data.payments
        )

        if paid_amount > data.total_amount:
            return {"code": 400, "msg": "payments total cannot exceed total_amount"}

        # 3️⃣ 更新主表
        expense.supplier_id = data.supplier_id
        expense.total_amount = data.total_amount
        expense.date = data.date

        expense.payment_status = payment_status
        expense.payment_date = payment_date

        # 4️⃣ 更新子表（先清空再重建）
        expense.payments = [
            ExpensePayment(
                method=p.method,
                amount=p.amount
            )
            for p in data.payments
        ]

        # 5️⃣ 提交
        db.commit()

        return {
            "code": 200,
            "msg": "updated successfully",
            "payment_status": payment_status
        }

    except Exception as e:
        db.rollback()
        return {"code": 500, "msg": str(e)}

    finally:
        db.close()


@router.delete("/{expense_id}")
def delete_expense(request: Request, expense_id: int):
    db = SessionLocal()

    try:
        user = request.state.user

        expense = (
            db.query(Expense)
            .filter(
                Expense.id == expense_id,
                Expense.user_id == user
            )
            .first()
        )

        if not expense:
            return {"code": 404, "msg": "not found"}

        db.delete(expense)
        db.commit()

        return {
            "code": 200,
            "msg": "deleted successfully"
        }

    except Exception as e:
        db.rollback()
        return {"code": 500, "msg": str(e)}

    finally:
        db.close()


@router.get("/stats")
def get_expense_stats(request: Request):
    db = SessionLocal()
    try:
        user_id = request.state.user
        today = cr_today()
        yesterday = today - timedelta(days=1)
        month_start = today.replace(day=1)
        today_total = db.query(
            func.coalesce(func.sum(Expense.total_amount), 0)
        ).filter(
            Expense.user_id == user_id,
            Expense.date == today
        ).scalar()
        yesterday_total = db.query(
            func.coalesce(func.sum(Expense.total_amount), 0)
        ).filter(
            Expense.user_id == user_id,
            Expense.date == yesterday
        ).scalar()
        month_total = db.query(
            func.coalesce(func.sum(Expense.total_amount), 0)
        ).filter(
            Expense.user_id == user_id,
            Expense.date >= month_start,
            Expense.date <= today
        ).scalar()
        return {
            "code": 200,
            "data": {
                "today": today_total,
                "yesterday": yesterday_total,
                "month": month_total
            }
        }
    finally:
        db.close()



@router.get("/caja-total/{target_date}")
def get_caja_total(
    target_date: date,
):
    db = SessionLocal()
    total = (
        db.query(
            func.coalesce(func.sum(ExpensePayment.amount), 0)
        )
        .join(
            Expense,
            Expense.id == ExpensePayment.expense_id
        )
        .filter(
            ExpensePayment.method == "caja",
            Expense.date == target_date
        )
        .scalar()
    )
    return {
        "code": 200,
        "date": target_date,
        "total_amount": float(total)
    }