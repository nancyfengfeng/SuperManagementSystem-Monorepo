import json
import requests
from pathlib import Path


class VtexCategoryParser:

    def __init__(
        self,
        api_url: str,
        output_file: str
    ):
        self.api_url = api_url
        self.output_file = Path(output_file)


    def fetch_categories(self):
        """
        获取VTEX分类树
        """

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            self.api_url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        return response.json()


    def parse_categories(
        self,
        categories,
        parent_id=None,
        level=1
    ):
        """
        递归转换分类结构
        """

        result = []

        for category in categories:

            item = {
                "id": category.get("id"),
                "name": category.get("name"),

                # URL最后一部分
                "url": category.get("url"),

                "parent_id": parent_id,

                "level": level,

                "has_children": category.get(
                    "hasChildren",
                    False
                ),

                "title": category.get(
                    "Title"
                ),

                "meta_description": category.get(
                    "MetaTagDescription"
                ),

                "children": []
            }


            children = category.get(
                "children",
                []
            )


            if children:
                item["children"] = self.parse_categories(
                    children,
                    parent_id=category["id"],
                    level=level+1
                )


            result.append(item)


        return result



    def save(self, data):

        self.output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            self.output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )



    def run(self):

        print(
            "Fetching VTEX categories..."
        )

        raw = self.fetch_categories()


        print(
            f"Root categories: {len(raw)}"
        )


        categories = self.parse_categories(
            raw
        )


        self.save(
            categories
        )


        print(
            f"Saved: {self.output_file}"
        )



if __name__ == "__main__":

    parser = VtexCategoryParser(

        api_url=
        "https://www.masxmenos.cr/api/catalog_system/pub/category/tree/3",

        output_file=
        "../data/categories/vtex_categories.json"
    )


    parser.run()