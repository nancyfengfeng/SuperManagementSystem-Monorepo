from shared.models.store import Store


def get_store_id(session, store_code):

    store = (
        session.query(Store)
        .filter(
            Store.code == store_code
        )
        .first()
    )

    if not store:
        raise Exception(
            f"Store not found: {store_code}"
        )

    return store.id