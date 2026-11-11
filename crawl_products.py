import csv
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from curl_cffi import requests
from pymongo import MongoClient

HOME = {
    "home",
    "homepage",
    "home page",
    "trang chủ",
    "trang chu",
    "startseite",
    "accueil",
    "inicio",
    "início",
    "начало",
    "startpagina",
    "hem",
    "hjem",
    "etusivu",
    "ana sayfa",
    "főoldal",
    "strona główna",
    "domů",
    "domov",
    "acasă",
    "početna",
    "pradžia",
    "sākums",
    "beranda",
    "หน้าแรก",
    "首页",
    "ホーム",
    "홈",
    "pagina iniziale",
    "pagina principală",
    "pagina principala",
    "página inicial",
    "pagina inicial",
    "página de inicio",
    "pagina de inicio",
    "página principal",
    "pagina principal",
    "principal",
    "page d'accueil",
    "forside",
    "startsida",
    "kezdőlap",
    "kezdolap",
    "početna stranica",
    "početna strana",
    "pocetna stranica",
    "pocetna strana",
    "uz sākumu",
    "uz sakumu",
    "pagrindinis puslapis",
    "pagrindinis",
    "avaleht",
    "головна",
    "ana səhifə",
    "ana sehife",
    "laman utama",
    "首頁",
    "الرئيسية",
    "الصفحة الرئيسية",
    "forsíða",
    "forsida",
    "anasayfa",
    "αρχική",
    "αρχική σελίδα",
}
CSV_PATH = Path("data/products.csv")
DOMAINS = [
    "www.glamira.com",
    "www.glamira.co.uk",
    "www.glamira.com.ph",
    "www.glamira.vn",
]
REMAINING_DOMAINS = [
    "www.glamira.com.au",
    "www.glamira.ca",
    "www.glamira.ie",
    "www.glamira.co.za",
    "www.glamira.co.nz",
    "www.glamira.sg",
    "www.glamira.in",
    "www.glamira.ae",
    "www.glamira.com.mt",
    "www.glamira.africa",
]
FOUR_DOMAIN_SWEEP_AFTER = "2026-11-06T17:02:00+00:00"


def good_category(category):
    return bool(category) and category.strip().lower() not in HOME


def is_home_link(link):
    classes = link.parent.get("class") or []
    path = urlsplit(link.get("href") or "").path.strip("/")
    text = link.get_text(strip=True)
    return "home" in classes or path in {"", "home"} or not good_category(text)


def catalog_url(domain, product_id):
    return f"https://{domain}/catalog/product/view/id/{product_id}"


def solve_challenge(session, response):
    match_i = re.search(r"var i = (\d+);", response.text)
    match_pow = re.search(r'Number\("(\d+)" \+ "(\d+)"\)', response.text)
    match_token = re.search(r'"bm-verify": "([^"]+)"', response.text)
    if not (match_i and match_pow and match_token):
        return response
    pow_value = int(match_i.group(1)) + int(match_pow.group(1) + match_pow.group(2))
    host = urlsplit(response.url).netloc
    session.post(
        f"https://{host}/_sec/verify?provider=interstitial",
        json={"bm-verify": match_token.group(1), "pow": pow_value},
        impersonate="chrome",
        timeout=30,
    )
    return session.get(response.url, impersonate="chrome", timeout=30)


def fetch(session, url):
    response = session.get(url, impersonate="chrome", timeout=30)
    if "bm-verify" in response.text:
        response = solve_challenge(session, response)
    return response


def read_product(product_id, response):
    soup = BeautifulSoup(response.text, "html.parser")
    name_node = soup.select_one("h1.page-title span.base")
    links = soup.select("div.breadcrumbs li.item a")
    crumbs = [
        item.get_text(strip=True)
        for index, item in enumerate(links)
        if index > 0 and not is_home_link(item)
    ]
    category = crumbs[-1] if crumbs else None
    price = soup.select_one('meta[property="product:price:amount"]')
    image = soup.select_one('meta[property="og:image"]')
    description = soup.select_one('meta[property="og:description"]')
    return {
        "product_id": product_id,
        "product_name": name_node.get_text(strip=True) if name_node else None,
        "category": category if good_category(category) else None,
        "price": price.get("content") if price else None,
        "description": description.get("content") if description else None,
        "image_url": image.get("content") if image else None,
        "source_url": response.url,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "status_code": response.status_code,
    }


def export_csv(products):
    fields = [
        "product_id",
        "product_name",
        "category",
        "price",
        "description",
        "image_url",
        "source_url",
        "crawled_at",
    ]
    with CSV_PATH.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for doc in products.find({}, {"_id": 0}).sort("product_id", 1):
            category = doc.get("category")
            if doc.get("product_name") and (category is None or good_category(category)):
                writer.writerow(doc)


def load_done(database):
    return {
        doc["product_id"]
        for doc in database.products.find({}, {"product_id": 1, "product_name": 1, "category": 1})
        if doc.get("product_name") and (doc.get("category") is None or good_category(doc.get("category")))
    }


def crawl_ids(database, session, product_ids, domains, done, miss_reason):
    tried = 0
    for product_id in product_ids:
        tried += 1
        found = False
        for domain in domains:
            url = catalog_url(domain, product_id)
            try:
                response = fetch(session, url)
                if response.status_code == 404:
                    time.sleep(random.uniform(0.4, 1.0))
                    continue
                if response.status_code != 200:
                    with open("data/crawl_errors.log", "a") as log:
                        log.write(f"{product_id}\t{url}\tHTTP {response.status_code}\n")
                    time.sleep(random.uniform(1.5, 4.2))
                    continue
                row = read_product(product_id, response)
                if row["product_name"]:
                    database.products.update_one({"product_id": product_id}, {"$set": row}, upsert=True)
                    done.add(product_id)
                    found = True
                    print(
                        f"{len(done)} {product_id} | {row['product_name']} | {row['category'] or 'null'} | {domain}",
                        flush=True,
                    )
                    database.product_catalog_misses.delete_one({"product_id": product_id})
                    time.sleep(random.uniform(1.5, 4.2))
                    break
            except Exception as error:
                with open("data/crawl_errors.log", "a") as log:
                    log.write(f"{product_id}\t{url}\t{error}\n")
            time.sleep(random.uniform(0.4, 1.0))
        if not found:
            database.product_catalog_misses.update_one(
                {"product_id": product_id},
                {"$set": {
                    "product_id": product_id,
                    "reason": miss_reason,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )
            if tried % 50 == 0:
                print(f"saved {len(done)} | tried {tried} | not found {product_id}", flush=True)


def main():
    database = MongoClient("mongodb://127.0.0.1:27017").countly
    database.products.create_index("product_id", unique=True, name="product_id_1")
    database.product_catalog_misses.create_index("product_id", unique=True, name="product_id_1")
    removed = database.products.delete_many(
        {"$expr": {"$in": [{"$toLower": {"$ifNull": ["$category", ""]}}, list(HOME)]}}
    ).deleted_count
    print(f"removed {removed} products whose category was a homepage label", flush=True)
    done = load_done(database)
    session = requests.Session()

    if "--remaining-domains" in sys.argv:
        database.product_catalog_misses.update_many(
            {"checked_at": {"$lt": FOUR_DOMAIN_SWEEP_AFTER}},
            {"$set": {"reason": "not_found_all_domains"}},
        )
        pending = [
            doc["product_id"]
            for doc in database.product_catalog_misses.find(
                {"reason": {"$ne": "not_found_all_domains"}},
                {"product_id": 1},
            )
        ]
        print(
            f"{len(pending)} ids were only checked on 4 domains. "
            f"Trying {len(REMAINING_DOMAINS)} other stores.",
            flush=True,
        )
        crawl_ids(database, session, pending, REMAINING_DOMAINS, done, "not_found_all_domains")
        export_csv(database.products)
        print(f"with a product name: {len(done)}", flush=True)
        print(
            f"category null: {database.products.count_documents({'product_name': {'$nin': [None, '']}, 'category': None})}",
            flush=True,
        )
        print(f"not found: {database.product_catalog_misses.count_documents({})}", flush=True)
        print(f"CSV: {CSV_PATH.resolve()}", flush=True)
        return

    exhausted = {
        doc["product_id"]
        for doc in database.product_catalog_misses.find({}, {"product_id": 1})
    }
    print(f"{len(done)} products already saved. Loading the missing ids.", flush=True)
    missing = []
    for doc in database.product_urls.aggregate(
        [{"$group": {"_id": "$product_id"}}],
        allowDiskUse=True,
    ):
        product_id = doc["_id"]
        if product_id not in done and product_id not in exhausted:
            missing.append(product_id)
    print(f"{len(missing)} ids left. Trying .com, .co.uk, .com.ph, then .vn.", flush=True)
    crawl_ids(database, session, missing, DOMAINS, done, "not_found")
    export_csv(database.products)
    print(f"with a product name: {len(done)}", flush=True)
    print(
        f"category null: {database.products.count_documents({'product_name': {'$nin': [None, '']}, 'category': None})}",
        flush=True,
    )
    print(f"not found: {database.product_catalog_misses.count_documents({})}", flush=True)
    print(f"CSV: {CSV_PATH.resolve()}", flush=True)


if __name__ == "__main__":
    main()
