from fastapi import APIRouter
from db import SessionLocal

from shared.models.category import Category


router = APIRouter(prefix="/category")


def build_category_tree(categories, parent_id=None):

    tree = []

    for category in categories:

        if category.parent_id == parent_id:

            children = build_category_tree(
                categories,
                category.id
            )

            tree.append(
                {
                    "id": category.id,
                    "external_id": category.external_id,
                    "name": category.name,
                    "slug": category.slug,
                    "level": category.level,
                    "is_leaf": category.is_leaf,
                    "children": children
                }
            )

    return tree



@router.get("/")
def get_categories():

    db = SessionLocal()

    try:

        categories = (
            db.query(Category)
            .filter(
                Category.active == True
            )
            .order_by(
                Category.level,
                Category.id
            )
            .all()
        )


        return build_category_tree(
            categories
        )


    finally:
        db.close()