from fastapi import APIRouter, Request
from sqlalchemy import func
from datetime import date, timedelta

from db import SessionLocal
from models.expense import Expense
from models.income import Income
from utils.time import cr_today

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/month-trend")

def month_trend(
    request: Request,
    month: str | None = None  # 格式：2026-06
):

    db = SessionLocal()
    try:
        user_id = request.state.user
        # ======================
        # 1. 计算起始日期
        # ======================

        if month:
            year, m = map(int, month.split("-"))
            start = date(year, m, 1)
        else:
            start = date.today().replace(day=1)

        # ======================
        # 2. 计算结束日期（当月最后一天）
        # ======================

        if start.month == 12:
            next_month = date(start.year + 1, 1, 1)
        else:
            next_month = date(start.year, start.month + 1, 1)
        end = next_month - timedelta(days=1)

        # ======================
        # 3. 查询每天支出
        # ======================

        expense_rows = (
            db.query(
                Expense.date,
                func.sum(Expense.total_amount).label("amount")
            )
            .filter(
                Expense.user_id == user_id,
                Expense.date >= start,
                Expense.date <= end
            )
            .group_by(Expense.date)
            .all()
        )

        # ======================
        # 4. 查询每天收入
        # ======================

        income_rows = (
            db.query(
                Income.date,
                func.sum(Income.total_amount).label("amount")
            )
            .filter(
                Income.user_id == user_id,
                Income.date >= start,
                Income.date <= end
            )
            .group_by(Income.date)
            .all()
        )

        # ======================
        # 5. 转 dict
        # ======================
        expense_map = {
            d.isoformat(): float(amount)
            for d, amount in expense_rows
        }
        income_map = {
            d.isoformat(): float(amount)
            for d, amount in income_rows
        }
        # ======================
        # 6. 数据库统计整个月收入
        # ======================
        total_income = (
            db.query(func.coalesce(func.sum(Income.total_amount), 0))
            .filter(
                Income.user_id == user_id,
                Income.date >= start,
                Income.date <= end
            )
            .scalar()
        )

        # ======================
        # 7. 数据库统计整个月支出
        # ======================
        total_expense = (
            db.query(func.coalesce(func.sum(Expense.total_amount), 0))
            .filter(
                Expense.user_id == user_id,
                Expense.date >= start,
                Expense.date <= end
            )
            .scalar()
        )

        total_income = float(total_income)
        total_expense = float(total_expense)
        gross_profit = total_income - total_expense
        gross_profit_rate = (
            round(gross_profit / total_income * 100, 2)
            if total_income > 0
            else 0
        )
        # 当月天数
        days_count = (end - start).days + 1

        # 日均收入
        avg_daily_income = round(total_income / days_count, 2)

        # 日均支出
        avg_daily_expense = round(total_expense / days_count, 2)

        # 日均利润
        avg_daily_profit = round(gross_profit / days_count, 2)

        # ======================
        # 8. 组织趋势数据
        # ======================
        all_dates = sorted(set(expense_map.keys()) | set(income_map.keys()))
        days = []
        income = []
        expense = []
        for date_str in all_dates:
            days.append(date.fromisoformat(date_str).strftime("%d"))
            income.append(income_map.get(date_str, 0))
            expense.append(expense_map.get(date_str, 0))

        # ======================
        # 9. 返回
        # ======================
        return {
            "code": 200,
            "data": {
                "days": days,
                "income": income,
                "expense": expense,

                "summary": {
                    "month_income": total_income,
                    "month_expense": total_expense,
                    "month_profit": gross_profit,
                    "month_profit_rate": gross_profit_rate,
                    "avg_daily_income": avg_daily_income,
                    "avg_daily_expense": avg_daily_expense,
                    "avg_daily_profit": avg_daily_profit
                },

                "month": month or start.strftime("%Y-%m")
            }
        }

    finally:

        db.close()