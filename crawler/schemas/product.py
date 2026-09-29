from dataclasses import dataclass


@dataclass
class ProductItem:
    barcode: str | None
    name: str
    image_url: str | None

    source_category_id: str | None #商品来源网站自己的分类 ID

    regular_price: float | None
    sale_price: float | None

    store_code: str
    store_product_id: str | None