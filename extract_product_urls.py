from pymongo import MongoClient

EVENT_TYPES = [
    "view_product_detail",
    "select_product_option",
    "select_product_option_quality",
    "add_to_cart_action",
    "product_detail_recommendation_visible",
    "product_detail_recommendation_noticed",
    "back_to_product_action",
    "view_all_recommend",
    "product_view_all_recommend_clicked",
]


def main():
    database = MongoClient("mongodb://127.0.0.1:27017").countly
    database.product_urls.drop()

    print("Reading events that carry a product.", flush=True)
    pairs = database.summary.aggregate(
        [
            {"$match": {"collection": {"$in": EVENT_TYPES}}},
            {
                "$project": {
                    "product_id": {
                        "$convert": {
                            "input": {
                                "$cond": [
                                    {"$eq": ["$collection", "product_view_all_recommend_clicked"]},
                                    "$viewing_product_id",
                                    {"$ifNull": ["$product_id", "$viewing_product_id"]},
                                ]
                            },
                            "to": "string",
                            "onError": "",
                            "onNull": "",
                        }
                    },
                    "url": {
                        "$cond": [
                            {"$eq": ["$collection", "product_view_all_recommend_clicked"]},
                            "$referrer_url",
                            "$current_url",
                        ]
                    },
                }
            },
            {"$match": {"product_id": {"$nin": [None, ""]}, "url": {"$nin": [None, ""]}}},
            {"$group": {"_id": {"product_id": "$product_id", "url": "$url"}}},
        ],
        allowDiskUse=True,
    )

    batch = []
    total = 0
    for pair in pairs:
        batch.append(pair["_id"])
        if len(batch) >= 2000:
            database.product_urls.insert_many(batch, ordered=False)
            total += len(batch)
            batch = []
            if total % 100000 == 0:
                print(f"saved {total:,} pairs", flush=True)
    if batch:
        database.product_urls.insert_many(batch, ordered=False)
        total += len(batch)

    database.product_urls.create_index(
        [("product_id", 1), ("url", 1)],
        unique=True,
        name="product_id_1_url_1",
    )
    unique_products = database.product_urls.aggregate(
        [{"$group": {"_id": "$product_id"}}, {"$count": "n"}]
    ).next()["n"]
    print(f"product_id + url pairs: {total:,}", flush=True)
    print(f"distinct product_id: {unique_products:,}", flush=True)


if __name__ == "__main__":
    main()