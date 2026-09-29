from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.orm import Session


# =========================================================
# Path
# =========================================================

# /www/wwwroot/SuperManagementSystem
BASE_DIR = Path(__file__).resolve().parents[2]

# /www/wwwroot/SuperManagementSystem/crawler
CRAWLER_DIR = BASE_DIR / "crawler"


# 让 Python 可以找到：
#
# crawler/database
# shared/
#
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if str(CRAWLER_DIR) not in sys.path:
    sys.path.insert(0, str(CRAWLER_DIR))


from database.session import SessionLocal
from shared.models.category import Category


# =========================================================
# Category JSON
# =========================================================

CATEGORY_FILE = (
    CRAWLER_DIR
    / "data"
    / "categories"
    / "vtex_categories.json"
)


# =========================================================
# Helpers
# =========================================================

def generate_slug(url: str | None) -> str:
    """
    https://www.walmart.co.cr/jugos-y-bebidas/agua
    ->
    jugos-y-bebidas/agua
    """

    if not url:
        return ""

    return urlparse(url).path.strip("/")


# =========================================================
# Import / Update Category
# =========================================================

def import_category(
    db: Session,
    node: dict,
    parent_id: int | None = None,
):
    """
    递归同步分类

    VTEX id:
        node["id"]

    保存到数据库:
        Category.external_id

    数据库 Category.id:
        保持自己的自增 id
    """

    external_id = str(node["id"])

    # -----------------------------------------------------
    # 查找数据库是否已经存在
    # -----------------------------------------------------

    category = (
        db.query(Category)
        .filter(
            Category.external_id == external_id
        )
        .first()
    )


    # -----------------------------------------------------
    # 判断是否叶子分类
    # -----------------------------------------------------

    children = node.get("children") or []

    # 不建议只使用 has_children
    #
    # 因为 VTEX 某些分类可能：
    #
    # has_children = true
    # children = []
    #
    # 所以这里按照实际 children 判断
    #
    is_leaf = len(children) == 0


    # -----------------------------------------------------
    # 已存在 → UPDATE
    # -----------------------------------------------------

    if category:

        category.name = node["name"]

        category.slug = generate_slug(
            node.get("url")
        )

        category.parent_id = parent_id

        category.level = node["level"]

        category.is_leaf = is_leaf

        category.active = True


        print(
            f"Updated: "
            f"{category.name} "
            f"(external_id={external_id})"
        )


    # -----------------------------------------------------
    # 不存在 → INSERT
    # -----------------------------------------------------

    else:

        category = Category(
            external_id=external_id,

            name=node["name"],

            slug=generate_slug(
                node.get("url")
            ),

            parent_id=parent_id,

            level=node["level"],

            is_leaf=is_leaf,

            active=True,
        )

        db.add(category)

        # 必须 flush
        #
        # 因为下面的 child 需要：
        #
        # category.id
        #
        db.flush()


        print(
            f"Inserted: "
            f"{category.name} "
            f"(external_id={external_id})"
        )


    # -----------------------------------------------------
    # 确保 UPDATE 后也同步到 session
    # -----------------------------------------------------

    db.flush()


    # -----------------------------------------------------
    # 递归导入 children
    # -----------------------------------------------------

    for child in children:

        import_category(
            db=db,

            node=child,

            # 注意：
            # 这里是数据库自己的 id
            #
            # 不是 VTEX external_id
            parent_id=category.id,
        )


# =========================================================
# Main
# =========================================================

def main():

    print("=" * 60)

    print("Category sync started")

    print(
        f"Category file: {CATEGORY_FILE}"
    )

    print("=" * 60)


    # -----------------------------------------------------
    # 检查 JSON 文件
    # -----------------------------------------------------

    if not CATEGORY_FILE.exists():

        raise FileNotFoundError(
            f"Category file not found: "
            f"{CATEGORY_FILE}"
        )


    # -----------------------------------------------------
    # Load JSON
    # -----------------------------------------------------

    with open(
        CATEGORY_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        categories = json.load(f)


    if not isinstance(categories, list):

        raise ValueError(
            "Category JSON root must be a list"
        )


    print(
        f"Root categories: {len(categories)}"
    )


    # -----------------------------------------------------
    # Database
    # -----------------------------------------------------

    db = SessionLocal()


    try:

        # -------------------------------------------------
        # 遍历所有一级分类
        # -------------------------------------------------

        for category in categories:

            import_category(
                db=db,
                node=category,
                parent_id=None,
            )


        # -------------------------------------------------
        # Commit
        # -------------------------------------------------

        db.commit()


        print("=" * 60)

        print(
            "Category sync completed!"
        )

        print("=" * 60)


    except Exception as error:

        db.rollback()

        print("=" * 60)

        print(
            "Category sync failed!"
        )

        print(
            f"Error: {error}"
        )

        print("=" * 60)

        raise


    finally:

        db.close()


# =========================================================
# Entry
# =========================================================

if __name__ == "__main__":
    main()