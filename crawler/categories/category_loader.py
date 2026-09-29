import json
from pathlib import Path
from urllib.parse import urlparse

CATEGORY_FILE = Path(
    "crawler/data/categories/vtex_categories.json"
)


def load_categories():

    with open(
        CATEGORY_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)




def extract_slug(url: str) -> str:
    path = urlparse(url).path
    return path.strip("/")


def get_leaf_categories(categories):

    result = []


    def walk(nodes):

        for node in nodes:

            children = node.get(
                "children",
                []
            )

            if children:
                walk(children)

            else:

                node["slug"] = extract_slug(
                    node["url"]
                )

                result.append(node)


    walk(categories)

    return result