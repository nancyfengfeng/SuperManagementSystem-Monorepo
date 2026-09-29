from fastapi import APIRouter

from routers.auth import router as auth_router
from routers.user import router as user_router
from routers.expense import router as expense_router
from routers.supplier import router as supplier_router
from routers.income import router as income_router
from routers.dashboard import router as dashboard_router
from routers.product import router as product_router
from routers.category import router as category_router
from routers.promotion import router as promotion_router
from routers.crawler_run import router as crawler_run_router
from routers.supplier_invoice import router as supplier_invoice_router
from routers.supplier_product import router as supplier_product_router

api_router = APIRouter()

api_router.include_router(auth_router,prefix="/api")
api_router.include_router(user_router,prefix="/api")
api_router.include_router(expense_router,prefix="/api")
api_router.include_router(supplier_router,prefix="/api")
api_router.include_router(income_router,prefix="/api")
api_router.include_router(dashboard_router,prefix="/api")
api_router.include_router(product_router,prefix="/api")
api_router.include_router(category_router,prefix="/api")
api_router.include_router(promotion_router,prefix="/api")
api_router.include_router(crawler_run_router,prefix="/api")
api_router.include_router(supplier_invoice_router,prefix="/api")
api_router.include_router(supplier_product_router,prefix="/api")