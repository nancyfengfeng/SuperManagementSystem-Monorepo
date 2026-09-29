import json
import requests


MEGASUPER_API = "https://nextgentheadless.instaleap.io/api/v3/graphql"


QUERY = """
query GetProductsByCategory(
    $getProductsByCategoryInput: GetProductsByCategoryInput!
) {
  getProductsByCategory(
    getProductsByCategoryInput: $getProductsByCategoryInput
  ) {
    category {
      reference
      name

      products {
        name
        sku
        price
        previousPrice
        stock
        ean

        promotion {
          conditions {
            quantity
            price
          }
          type
          startDateTime
          isActive
          endDateTime
        }

        promotionPricePerSubUnit
        brand
        photosUrl

        categories {
          name
          reference
        }
      }
    }
  }
}
"""


def get_products(
    category_reference: str,
    store_reference: str = "M305",
    page: int = 1,
    page_size: int = 100
):
    payload = {
        "operationName": "GetProductsByCategory",
        "variables": {
            "getProductsByCategoryInput": {
                "clientId": "MEGASUPER",
                "storeReference": store_reference,
                "categoryReference": category_reference,
                "currentPage": page,
                "pageSize": page_size,
            }
        },
        "query": QUERY,
    }

    response = requests.post(
        MEGASUPER_API,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("errors"):
        raise RuntimeError(data["errors"])

    return (
        data
        .get("data", {})
        .get("getProductsByCategory", {})
        .get("category", {})
        .get("products", [])
    )


def load_root_categories():
    with open(
        "crawler/data/categories/megasuper_categories.json",
        "r",
        encoding="utf-8",
    ) as f:
        categories = json.load(f)

    return [
        category
        for category in categories
        if category["level"] == 1
    ]