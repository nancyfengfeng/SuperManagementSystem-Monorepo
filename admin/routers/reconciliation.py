from collections import defaultdict
from datetime import date
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font

from db import SessionLocal
from models.income import Income, IncomeType
from models.expense import Expense, ExpensePayment
from models.supplier import Supplier


router = APIRouter(
    prefix="/reconciliation",
    tags=["Reconciliation"]
)


@router.get("/preview")
def get_reconciliation_preview(
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be after end_date"
        )

    db = SessionLocal()

    try:
        income_rows = (
            db.query(
                Income.date,
                Income.id.label("income_id"),
                IncomeType.income_type,
                IncomeType.amount
            )
            .join(
                IncomeType,
                IncomeType.income_id == Income.id
            )
            .filter(
                Income.date.between(start_date, end_date),
                IncomeType.income_type.in_(["card", "sinpe"])
            )
            .order_by(
                Income.date.asc(),
                Income.id.asc()
            )
            .all()
        )

        expense_rows = (
            db.query(
                Expense.payment_date,
                Expense.date.label("expense_date"),
                Expense.id.label("expense_id"),
                Supplier.name.label("supplier_name"),
                Supplier.legal_name.label("supplier_legal_name"),
                Expense.total_amount,
                Expense.payment_status,
                ExpensePayment.amount.label("card_amount")
            )
            .join(
                ExpensePayment,
                ExpensePayment.expense_id == Expense.id
            )
            .outerjoin(
                Supplier,
                Supplier.id == Expense.supplier_id
            )
            .filter(
                Expense.payment_date.between(start_date, end_date),
                ExpensePayment.method == "card"
            )
            .order_by(
                Expense.payment_date.asc(),
                Expense.id.asc()
            )
            .all()
        )

        daily = defaultdict(
            lambda: {
                "card_income": 0.0,
                "sinpe_income": 0.0,
                "card_expense": 0.0
            }
        )

        income_details = []

        for row in income_rows:
            amount = float(row.amount or 0)

            if row.income_type == "card":
                daily[row.date]["card_income"] += amount
            elif row.income_type == "sinpe":
                daily[row.date]["sinpe_income"] += amount

            income_details.append({
                "date": row.date,
                "income_id": row.income_id,
                "type": row.income_type,
                "amount": amount
            })

        card_expenses = []

        for row in expense_rows:
            amount = float(row.card_amount or 0)

            daily[row.payment_date]["card_expense"] += amount

            card_expenses.append({
                "payment_date": row.payment_date,
                "expense_date": row.expense_date,
                "expense_id": row.expense_id,
                "supplier_name": row.supplier_name,
                "supplier_legal_name": row.supplier_legal_name,
                "card_amount": amount,
                "total_amount": float(row.total_amount or 0),
                "payment_status": row.payment_status
            })

        daily_summary = []

        for day in sorted(daily):
            values = daily[day]

            card_income = round(values["card_income"], 2)
            sinpe_income = round(values["sinpe_income"], 2)
            card_expense = round(values["card_expense"], 2)

            daily_summary.append({
                "date": day,
                "card_income": card_income,
                "sinpe_income": sinpe_income,
                "total_income": round(
                    card_income + sinpe_income,
                    2
                ),
                "card_expense": card_expense,
                "net_amount": round(
                    card_income + sinpe_income - card_expense,
                    2
                )
            })

        return {
            "code": 200,
            "data": {
                "start_date": start_date,
                "end_date": end_date,
                "daily_summary": daily_summary,
                "income_details": income_details,
                "card_expenses": card_expenses
            }
        }

    finally:
        db.close()


@router.get("/export")
def export_reconciliation(start_date: date = Query(...), end_date: date = Query(...)):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    db = SessionLocal()

    try:
        # =========================
        # 收入：Card + SINPE
        # =========================
        income_rows = (
            db.query(
                Income.date,
                IncomeType.income_type,
                IncomeType.amount
            )
            .join(IncomeType, IncomeType.income_id == Income.id)
            .filter(
                Income.date.between(start_date, end_date),
                IncomeType.income_type.in_(["card", "sinpe"])
            )
            .order_by(Income.date.asc(), Income.id.asc())
            .all()
        )

        # =========================
        # 支出：Card + SINPE
        # 按 payment_date 对实际流水
        # =========================
        expense_rows = (
            db.query(
                Expense.payment_date,
                Expense.date.label("expense_date"),
                Supplier.name.label("supplier_name"),
                Supplier.legal_name.label("supplier_legal_name"),
                Expense.total_amount,
                ExpensePayment.method,
                ExpensePayment.amount.label("payment_amount")
            )
            .join(ExpensePayment, ExpensePayment.expense_id == Expense.id)
            .outerjoin(Supplier, Supplier.id == Expense.supplier_id)
            .filter(
                Expense.payment_date.between(start_date, end_date),
                ExpensePayment.method.in_(["card", "sinpe"])
            )
            .order_by(
                Expense.payment_date.asc(),
                Expense.id.asc(),
                ExpensePayment.id.asc()
            )
            .all()
        )

        # =========================
        # 每日流水汇总
        # =========================
        daily = defaultdict(
            lambda: {
                "card_income": 0.0,
                "sinpe_income": 0.0,
                "card_expense": 0.0,
                "sinpe_expense": 0.0
            }
        )

        for row in income_rows:
            amount = float(row.amount or 0)

            if row.income_type == "card":
                daily[row.date]["card_income"] += amount
            elif row.income_type == "sinpe":
                daily[row.date]["sinpe_income"] += amount

        for row in expense_rows:
            amount = float(row.payment_amount or 0)

            if row.method == "card":
                daily[row.payment_date]["card_expense"] += amount
            elif row.method == "sinpe":
                daily[row.payment_date]["sinpe_expense"] += amount

        wb = Workbook()

        # ==================================================
        # Sheet 1：每日流水汇总
        # ==================================================
        ws_summary = wb.active
        ws_summary.title = "每日流水汇总"

        ws_summary.append([
            "日期",
            "Card收入",
            "SINPE收入",
            "收入合计",
            "Card支出",
            "SINPE支出",
            "支出合计",
            "净额"
        ])

        for day in sorted(daily):
            values = daily[day]

            card_income = round(values["card_income"], 2)
            sinpe_income = round(values["sinpe_income"], 2)
            card_expense = round(values["card_expense"], 2)
            sinpe_expense = round(values["sinpe_expense"], 2)

            total_income = round(card_income + sinpe_income, 2)
            total_expense = round(card_expense + sinpe_expense, 2)
            net_amount = round(total_income - total_expense, 2)

            ws_summary.append([
                day,
                card_income,
                sinpe_income,
                total_income,
                card_expense,
                sinpe_expense,
                total_expense,
                net_amount
            ])

        summary_total_row = ws_summary.max_row + 1
        ws_summary.cell(summary_total_row, 1, "总计")

        for col in range(2, 9):
            letter = ws_summary.cell(1, col).column_letter

            if summary_total_row > 2:
                formula = f"=SUM({letter}2:{letter}{summary_total_row - 1})"
            else:
                formula = "=0"

            ws_summary.cell(summary_total_row, col, formula)

        # ==================================================
        # Sheet 2：收入明细
        # Card / SINPE 分列
        # ==================================================
        ws_income = wb.create_sheet("收入明细")

        ws_income.append([
            "日期",
            "Card",
            "SINPE",
            "合计"
        ])

        income_daily = defaultdict(
            lambda: {
                "card": 0.0,
                "sinpe": 0.0
            }
        )

        for row in income_rows:
            amount = float(row.amount or 0)

            if row.income_type == "card":
                income_daily[row.date]["card"] += amount
            elif row.income_type == "sinpe":
                income_daily[row.date]["sinpe"] += amount

        for day in sorted(income_daily):
            card_amount = round(income_daily[day]["card"], 2)
            sinpe_amount = round(income_daily[day]["sinpe"], 2)
            total_amount = round(card_amount + sinpe_amount, 2)

            ws_income.append([
                day,
                card_amount,
                sinpe_amount,
                total_amount
            ])

        income_total_row = ws_income.max_row + 1
        ws_income.cell(income_total_row, 1, "总计")

        for col in range(2, 5):
            letter = ws_income.cell(1, col).column_letter

            if income_total_row > 2:
                ws_income.cell(
                    income_total_row,
                    col,
                    f"=SUM({letter}2:{letter}{income_total_row - 1})"
                )
            else:
                ws_income.cell(income_total_row, col, "=0")

        # ==================================================
        # Sheet 3：支出流水明细
        # ==================================================
        ws_expense = wb.create_sheet("支出流水明细")

        ws_expense.append([
            "付款日期",
            "支出日期",
            "支付方式",
            "供应商",
            "正式名称",
            "支付金额",
            "支出总额"
        ])

        for row in expense_rows:
            supplier_name = row.supplier_name or ""
            legal_name = row.supplier_legal_name or supplier_name

            ws_expense.append([
                row.payment_date,
                row.expense_date,
                row.method,
                supplier_name,
                legal_name,
                float(row.payment_amount or 0),
                float(row.total_amount or 0)
            ])

        expense_total_row = ws_expense.max_row + 1
        ws_expense.cell(expense_total_row, 1, "总计")

        # 只统计实际支付金额。
        # total_amount 不能直接 SUM：
        # 如果同一 Expense 同时使用 card + sinpe，
        # 支出总额会在多行重复出现。
        if expense_total_row > 2:
            ws_expense.cell(
                expense_total_row,
                6,
                f"=SUM(F2:F{expense_total_row - 1})"
            )
        else:
            ws_expense.cell(expense_total_row, 6, "=0")

        # ==================================================
        # 表头 / 总计格式
        # ==================================================
        for ws in wb.worksheets:
            for cell in ws[1]:
                cell.font = Font(bold=True)

            ws.freeze_panes = "A2"

        for cell in ws_summary[summary_total_row]:
            cell.font = Font(bold=True)

        for cell in ws_income[income_total_row]:
            cell.font = Font(bold=True)

        for cell in ws_expense[expense_total_row]:
            cell.font = Font(bold=True)

        # ==================================================
        # 自动筛选
        # 不包含最后的总计行
        # ==================================================
        if summary_total_row > 2:
            ws_summary.auto_filter.ref = f"A1:H{summary_total_row - 1}"

        if income_total_row > 2:
            ws_income.auto_filter.ref = f"A1:D{income_total_row - 1}"

        if expense_total_row > 2:
            ws_expense.auto_filter.ref = f"A1:G{expense_total_row - 1}"

        # ==================================================
        # 列宽
        # ==================================================
        ws_summary.column_dimensions["A"].width = 14
        ws_summary.column_dimensions["B"].width = 15
        ws_summary.column_dimensions["C"].width = 15
        ws_summary.column_dimensions["D"].width = 15
        ws_summary.column_dimensions["E"].width = 15
        ws_summary.column_dimensions["F"].width = 15
        ws_summary.column_dimensions["G"].width = 15
        ws_summary.column_dimensions["H"].width = 15

        ws_income.column_dimensions["A"].width = 14
        ws_income.column_dimensions["B"].width = 16
        ws_income.column_dimensions["C"].width = 16
        ws_income.column_dimensions["D"].width = 16

        ws_expense.column_dimensions["A"].width = 14
        ws_expense.column_dimensions["B"].width = 14
        ws_expense.column_dimensions["C"].width = 12
        ws_expense.column_dimensions["D"].width = 24
        ws_expense.column_dimensions["E"].width = 48
        ws_expense.column_dimensions["F"].width = 16
        ws_expense.column_dimensions["G"].width = 16

        # ==================================================
        # 日期格式
        # ==================================================
        if summary_total_row > 2:
            for row in ws_summary.iter_rows(
                min_row=2,
                max_row=summary_total_row - 1,
                min_col=1,
                max_col=1
            ):
                row[0].number_format = "yyyy-mm-dd"

        if income_total_row > 2:
            for row in ws_income.iter_rows(
                min_row=2,
                max_row=income_total_row - 1,
                min_col=1,
                max_col=1
            ):
                row[0].number_format = "yyyy-mm-dd"

        if expense_total_row > 2:
            for row in ws_expense.iter_rows(
                min_row=2,
                max_row=expense_total_row - 1,
                min_col=1,
                max_col=2
            ):
                for cell in row:
                    cell.number_format = "yyyy-mm-dd"

        # ==================================================
        # 金额格式
        # ==================================================
        for row in ws_summary.iter_rows(
            min_row=2,
            max_row=summary_total_row,
            min_col=2,
            max_col=8
        ):
            for cell in row:
                cell.number_format = "#,##0"

        for row in ws_income.iter_rows(
            min_row=2,
            max_row=income_total_row,
            min_col=2,
            max_col=4
        ):
            for cell in row:
                cell.number_format = "#,##0"

        if expense_total_row > 2:
            for row in ws_expense.iter_rows(
                min_row=2,
                max_row=expense_total_row - 1,
                min_col=6,
                max_col=7
            ):
                for cell in row:
                    cell.number_format = "#,##0"

        ws_expense.cell(expense_total_row, 6).number_format = "#,##0"

        # ==================================================
        # 输出 Excel
        # ==================================================
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = (
            f"reconciliation_"
            f"{start_date.isoformat()}_"
            f"{end_date.isoformat()}.xlsx"
        )

        return StreamingResponse(
            output,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                )
            }
        )

    finally:
        db.close()