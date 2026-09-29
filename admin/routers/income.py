from fastapi import APIRouter, Request, Query,Depends
from db import SessionLocal
from models.income import Income, IncomeType
from schemas.income import IncomeCreate
from sqlalchemy import func
from datetime import date, timedelta
from sqlalchemy import func
from calendar import monthrange

from utils.time import cr_today

router = APIRouter(prefix="/income", tags=["Income"])


@router.post("/")
def create_income(request: Request, data: IncomeCreate):
    db = SessionLocal()

    try:
        user_id = request.state.user

        # ✅ 自动过滤掉 amount <= 0 的类型（核心修复）
        valid_types = [t for t in data.types if t.amount > 0]

        # 如果一个有效的都没有，报错
        if len(valid_types) == 0:
            return {"code": 400, "msg": "至少填写一种收入金额"}

        # 重新计算正确的 total
        total = sum(t.amount for t in valid_types)

        # 创建主表
        income = Income(
            user_id=user_id,
            date=data.date,
            total_amount=total
        )

        # 只保存有效的类型
        income.types = [
            IncomeType(
                income_type=t.income_type,
                amount=t.amount
            )
            for t in valid_types
        ]

        db.add(income)
        db.commit()
        db.refresh(income)

        return {
            "code": 200,
            "income_id": income.id
        }

    except Exception as e:
        db.rollback()
        return {"code": 500, "msg": str(e)}

    finally:
        db.close()

@router.get("/stats")
def get_income_stats(request: Request):
    db = SessionLocal()

    try:
        user_id = request.state.user

        today = cr_today()
        yesterday = today - timedelta(days=1)
        month_start = today.replace(day=1)

        today_total = db.query(
            func.coalesce(func.sum(Income.total_amount), 0)
        ).filter(
            Income.user_id == user_id,
            Income.date == today
        ).scalar()

        yesterday_total = db.query(
            func.coalesce(func.sum(Income.total_amount), 0)
        ).filter(
            Income.user_id == user_id,
            Income.date == yesterday
        ).scalar()

        month_total = db.query(
            func.coalesce(func.sum(Income.total_amount), 0)
        ).filter(
            Income.user_id == user_id,
            Income.date >= month_start,
            Income.date <= today
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


@router.get("/month-trend")
def month_trend(
    request: Request,
    month: str | None = Query(None)
):
    db = SessionLocal()

    try:
        user_id = request.state.user

        # 计算月份范围
        if month:
            year, month_num = map(int, month.split("-"))
        else:
            today = date.today()
            year = today.year
            month_num = today.month

        month_start = date(year, month_num, 1)
        last_day = monthrange(year, month_num)[1]
        month_end = date(year, month_num, last_day)

        # 查询每日各收入方式
        rows = (
            db.query(
                Income.date,
                IncomeType.income_type,
                func.sum(IncomeType.amount)
            )
            .join(IncomeType, Income.id == IncomeType.income_id)
            .filter(
                Income.user_id == user_id,
                Income.date >= month_start,
                Income.date <= month_end
            )
            .group_by(Income.date, IncomeType.income_type)
            .all()
        )

        cash_map = {}
        card_map = {}
        sinpe_map = {}

        for income_date, income_type, amount in rows:
            key = income_date.isoformat()
            if income_type == "cash":
                cash_map[key] = float(amount)
            elif income_type == "card":
                card_map[key] = float(amount)
            elif income_type == "sinpe":
                sinpe_map[key] = float(amount)

        # ======================
        # 只返回有数据的日期 ✅
        # ======================
        data_list = []
        day_id = 1

        # 获取所有有数据的日期（去重）
        all_dates = set(cash_map.keys()) | set(card_map.keys()) | set(sinpe_map.keys())

        for date_str in sorted(all_dates):
            cash_amount = cash_map.get(date_str, 0)
            card_amount = card_map.get(date_str, 0)
            sinpe_amount = sinpe_map.get(date_str, 0)
            total_amount = cash_amount + card_amount + sinpe_amount

            # 转成日期对象（用于格式化输出）
            current = date.fromisoformat(date_str)

            data_list.append({
                "id": day_id,
                "date": current.strftime("%Y-%m-%d"),
                "day": current.strftime("%d"),
                "total": total_amount,
                "cash": cash_amount,
                "card": card_amount,
                "sinpe": sinpe_amount
            })
            day_id += 1

        return {
            "code": 200,
            "data": data_list
        }

    finally:
        db.close()


@router.get("/month-income-list")
def income_list(
    request: Request,
    month: str | None = Query(None)
):
    db = SessionLocal()
    try:
        user_id = request.state.user

        if month:
            year, month_num = map(int, month.split("-"))
            start = date(year, month_num, 1)
            last_day = monthrange(year, month_num)[1]
            end = date(year, month_num, last_day)
        else:
            start = date(date.today().year, date.today().month, 1)
            end = date.today()

        # 查询原始每一笔数据
        rows = db.query(Income).filter(
            Income.user_id == user_id,
            Income.date >= start,
            Income.date <= end
        ).order_by(Income.date.desc()).all()

        data = []
        for income in rows:
            cash = 0.0
            card = 0.0
            sinpe = 0.0

            # ✅ 修复：这里必须是 .types 不是 .items
            for item in income.types:
                if item.income_type == "cash":
                    cash = float(item.amount)
                elif item.income_type == "card":
                    card = float(item.amount)
                elif item.income_type == "sinpe":
                    sinpe = float(item.amount)

            data.append({
                "id": income.id,
                "date": income.date.strftime("%Y-%m-%d"),
                "cash": cash,
                "card": card,
                "sinpe": sinpe,
                "total": cash + card + sinpe
            })

        return {"code": 200, "data": data}
    finally:
        db.close()


@router.delete("/{income_id}")
def delete_income(
    income_id: int,
    request: Request
):
    db = SessionLocal()
    # 1. 先找到这条收入（只能删自己的，防止别人删你的数据）
    income = db.query(Income).filter(
        Income.id == income_id,
        Income.user_id == request.state.user  # 只能删当前登录用户的数据
    ).first()

    # 2. 如果不存在，报错
    if not income:
        raise HTTPException(status_code=404, detail="收入记录不存在")

    # 3. 删除（会自动级联删除 income_types 里的数据！）
    db.delete(income)
    db.commit()

    return {"code": 200, "message": "删除成功"}