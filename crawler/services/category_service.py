from shared.models.category import Category


def get_category_id(
    session,
    external_id: str | None
):

    if not external_id:
        return None


    category = (
        session.query(Category)
        .filter(
            Category.external_id == external_id
        )
        .first()
    )


    if not category:
        return None


    return category.id