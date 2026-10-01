import requests

from crawler.configs.vtex import VTEX_STORES



def build_category_path(slug: str) -> str:

    parts = slug.strip("/").split("/")

    result = []

    for index, part in enumerate(parts, start=1):
        result.append(
            f"category-{index}/{part}"
        )

    return "/".join(result)



def get_products(store_code: str,category_slug: str,page: int = 1,page_size: int = 100):

    config = VTEX_STORES[store_code]

    category_path = build_category_path(category_slug)


    url = (
        f"https://{config['domain']}"
        "/api/intelligent-search/v1/product-search/"
        f"{category_path}"
    )


    params = {
        "page": page,
        "pageSize": page_size,
        "sc": config["sc"],
        "country": config["country"],
        "locale": config["locale"],
    }

    if config.get("region_id"):
        params["regionId"] = config["region_id"]


    response = requests.get(
        url,
        params=params,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )


    response.raise_for_status()


    data = response.json()


    return {
        "products": data.get("products",[]),
        "pagination": data.get("pagination",{})
    }



