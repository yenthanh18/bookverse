import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# ===== CONFIG =====
INPUT_FILE = "books_web_v2.csv"
OUTPUT_FILE = "books_store_ready.csv"

publishers = [
    "Penguin Books",
    "HarperCollins",
    "Bloomsbury",
    "Random House",
    "Vintage",
    "Oxford Press"
]

formats = ["Paperback", "Hardcover", "Ebook"]

def generate_isbn():
    prefix = "978"
    body = "".join([str(random.randint(0, 9)) for _ in range(9)])
    return prefix + body

def generate_price(rating, ratings_count):
    base = 60000
    popularity_factor = np.log1p(ratings_count) * 8000
    rating_factor = rating * 4000
    noise = random.randint(-15000, 25000)
    price = base + popularity_factor + rating_factor + noise
    price = max(45000, min(int(price), 320000))
    return price

def generate_stock(ratings_count):
    if ratings_count > 20000:
        return random.randint(40, 120)
    elif ratings_count > 5000:
        return random.randint(20, 80)
    else:
        return random.randint(0, 40)

def main():
    df = pd.read_csv(INPUT_FILE)

    df["sku"] = ["BOOK" + str(i).zfill(6) for i in range(1, len(df)+1)]

    prices = []
    discount_prices = []
    stocks = []
    publishers_list = []
    isbns = []
    formats_list = []

    for _, row in df.iterrows():
        price = generate_price(row["average_rating"], row["ratings_count"])
        prices.append(price)

        if random.random() < 0.4:
            discount = random.uniform(0.05, 0.25)
            discount_prices.append(int(price * (1 - discount)))
        else:
            discount_prices.append(None)

        stocks.append(generate_stock(row["ratings_count"]))
        publishers_list.append(random.choice(publishers))
        isbns.append(generate_isbn())
        formats_list.append(random.choice(formats))

    df["price"] = prices
    df["discount_price"] = discount_prices
    df["stock_quantity"] = stocks
    df["publisher"] = publishers_list
    df["isbn"] = isbns
    df["format"] = formats_list
    df["language"] = "English"
    df["is_active"] = 1

    now = datetime.now()
    df["created_at"] = [now - timedelta(days=random.randint(30, 900)) for _ in range(len(df))]
    df["updated_at"] = now

    df.to_csv(OUTPUT_FILE, index=False)
    print("✅ DONE — Created:", OUTPUT_FILE)

if __name__ == "__main__":
    main()