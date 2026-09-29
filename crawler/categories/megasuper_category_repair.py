from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests
from sqlalchemy import select

from crawler.database.session import SessionLocal
from shared.models.product import Product


MEGASUPER_API = "https://nextgentheadless.instaleap.io/api/v3/graphql"

CLIENT_ID = "MEGASUPER"
STORE_REFERENCE = "M305"

BATCH_SIZE = 100

BASE_DIR = Path(__file__).resolve().parents[1]

MAPPING_FILE = (
    BASE_DIR
    / "data"
    / "categories"
    / "megasuper_category_mapping.json"
)


QUERY = """
query GetProductsBySKU(
$getProductsBySKUInput: GetProductsBySKUInput!
) {
    getProductsBySKU(
        getProductsBySKUInput: $getProductsBySKUInput
    ) {
        sku
        categoriesData {
            reference
        }
    }
}
"""


def load_mapping():
    with open(
        MAPPING_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)



def chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]



def get_products_by_skus(skus: list[str]):

    payload = [
        {
            "operationName": "GetProductsBySKU",
            "variables": {
                "getProductsBySKUInput": {
                    "clientId": CLIENT_ID,
                    "storeReference": STORE_REFERENCE,
                    "skus": skus
                }
            },
            "query": QUERY
        }
    ]

    response = requests.post(
        MEGASUPER_API,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if isinstance(data, list):
        data = data[0]

    if data.get("errors"):
        raise RuntimeError(
            json.dumps(
                data["errors"],
                ensure_ascii=False
            )
        )

    return (
        data
        .get("data", {})
        .get("getProductsBySKU", [])
    )



def get_external_category_id(product):

    categories = product.get(
        "categoriesData",
        []
    )

    for c in categories:
        ref = c.get("reference")

        if ref and len(ref) == 7:
            return ref

    return None



def repair_categories(dry_run=True):

    """
    dry_run=True:
        只显示，不修改数据库

    dry_run=False:
        更新products.category_id
    """

    mapping = load_mapping()

    with SessionLocal() as session:

        stmt = (
            select(Product)
            .where(
                Product.category_id.is_(None),
                Product.barcode.is_not(None)
            )
        )

        products = (
            session.execute(stmt)
            .scalars()
            .all()
        )


        print(
            f"发现 {len(products)} 个商品没有分类"
        )


        updated = 0
        skipped = 0

        skip_reason = {
            "API找不到": 0,
            "没有分类": 0,
            "没有mapping": 0,
        }


        for index, batch in enumerate(
            chunks(products, BATCH_SIZE),
            start=1
        ):

            print(
                f"\n处理第 {index} 批，共 {len(batch)} 个"
            )


            barcodes = [
                p.barcode
                for p in batch
            ]


            try:

                mega_products = (
                    get_products_by_skus(barcodes)
                )

            except Exception as e:

                print(
                    "API错误:",
                    e
                )

                continue



            mega_map = {
                p.get("sku"): p
                for p in mega_products
            }



            for product in batch:

                mega_product = mega_map.get(
                    product.barcode
                )


                if not mega_product:
                    skip_reason["API找不到"] += 1
                    skipped += 1
                    continue



                external_id = (
                    get_external_category_id(
                        mega_product
                    )
                )


                if not external_id:
                    skip_reason["没有分类"] += 1
                    skipped += 1
                    continue



                category_id = mapping.get(
                    external_id
                )


                if not category_id:
                    skip_reason["没有mapping"] += 1
                    skipped += 1
                    continue


                if not dry_run:

                    product.category_id = category_id


                updated += 1



            if not dry_run:

                session.commit()


            time.sleep(1)



        print("\n==========")
        print("匹配成功:", updated)
        print("跳过:", skipped)
        print("跳过原因:", skip_reason)
        print("数据库更新:","是" if not dry_run else "否")



if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--update",
        action="store_true",
        help="写入数据库"
    )

    args = parser.parse_args()

    print(
        "运行模式:",
        "写入数据库" if args.update else "测试模式"
    )

    repair_categories(
        dry_run=not args.update
    )