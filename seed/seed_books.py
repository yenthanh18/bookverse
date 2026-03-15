import os
import sys
import pandas as pd
import re
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.models import db, User, Author, Publisher, Category, Book

def slugify(text: str) -> str:
    slug = text.lower().replace(' ', '-').replace('&', 'and')
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    return slug

def seed_database():
    app = create_app()
    with app.app_context():
        print("Checking tables and loading data from books_store_ready.csv...")
        csv_path = os.path.join(app.config.get('AI_MODELS_DIR', '.'), 'books_store_ready.csv')
        try:
            df = pd.read_csv(csv_path)
            # Fill NaNs
            df['authors'] = df['authors'].fillna('Unknown')
            df['genre'] = df['genre'].fillna('Uncategorized')
            df['publisher'] = df['publisher'].fillna('Unknown Publisher')
            df['description'] = df['description'].fillna('')
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return

        print("Seeding Authors...")
        unique_authors = set()
        for authors_str in df['authors'].dropna():
            for author in authors_str.split(','):
                unique_authors.add(author.strip())
        
        author_map = {}
        for author_name in unique_authors:
            if not author_name:
                continue
            author = Author(name=author_name)
            db.session.add(author)
            author_map[author_name] = author
        
        print("Seeding Publishers...")
        unique_publishers = set(df['publisher'].dropna().unique())
        publisher_map = {}
        for pub_name in unique_publishers:
            if not pub_name:
                continue
            pub = Publisher(name=pub_name)
            db.session.add(pub)
            publisher_map[pub_name] = pub

        print("Seeding Categories...")
        unique_categories = set()
        for genres_str in df['genre'].dropna():
            for genre in genres_str.split(','):
                cat_name = genre.strip()
                if cat_name:
                    unique_categories.add(cat_name)
        
        category_map = {}
        seen_slugs = set()
        for cat_name in unique_categories:
            slug = slugify(cat_name)
            if not slug or slug in seen_slugs:
                slug = slug + f"-{len(seen_slugs)}"
            seen_slugs.add(slug)
            
            cat = Category(name=cat_name, slug=slug)
            db.session.add(cat)
            category_map[cat_name] = cat
        
        db.session.commit()
        
        print("Seeding Books...")
        count = 0
        seen_book_slugs = set()
        seen_book_skus = set()
        seen_book_ids = set()
        
        books_batch = []
        for _, row in df.iterrows():
            book_id = int(row['book_id']) if pd.notna(row['book_id']) else None
            title = str(row['title']).strip()
            
            if book_id is None or book_id in seen_book_ids:
                # generate a pseudo id if missing or dup
                book_id = max(seen_book_ids or [0]) + 1
            seen_book_ids.add(book_id)

            slug = slugify(title)
            if not slug or slug in seen_book_slugs:
                slug = f"{slug}-{book_id}"
            seen_book_slugs.add(slug)
            
            sku = str(row['sku']).strip() if pd.notna(row.get('sku')) else f"SKU-{book_id}"
            if not sku or sku in seen_book_skus:
                sku = f"{sku}-{book_id}"
            seen_book_skus.add(sku)

            book = Book(
                id=book_id,
                title=title,
                slug=slug,
                publication_year=int(row['original_publication_year']) if pd.notna(row.get('original_publication_year')) else None,
                average_rating=float(row['average_rating']) if pd.notna(row.get('average_rating')) else None,
                ratings_count=int(row['ratings_count']) if pd.notna(row.get('ratings_count')) else None,
                image_url=str(row['image_url']) if pd.notna(row.get('image_url')) else None,
                small_image_url=str(row['small_image_url']) if pd.notna(row.get('small_image_url')) else None,
                description=str(row['description']) if pd.notna(row.get('description')) else None,
                sku=sku,
                price=float(row['price']) if pd.notna(row.get('price')) else 20.0,
                discount_price=float(row['discount_price']) if pd.notna(row.get('discount_price')) else None,
                stock_quantity=int(row['stock_quantity']) if pd.notna(row.get('stock_quantity')) else 100,
                format=str(row['format']) if pd.notna(row.get('format')) else None,
                language=str(row['language']) if pd.notna(row.get('language')) else None,
                isbn=str(row['isbn']) if pd.notna(row.get('isbn')) else None,
                is_active=bool(row['is_active']) if pd.notna(row.get('is_active')) else True,
            )

            # Assign Publisher
            pub_name = str(row['publisher']).strip()
            if pub_name in publisher_map:
                book.publisher = publisher_map[pub_name]

            # Assign Authors (Deduplicate per book)
            book_authors = set()
            for author_name in str(row['authors']).split(','):
                a_name = author_name.strip()
                if a_name in author_map and a_name not in book_authors:
                    book.authors.append(author_map[a_name])
                    book_authors.add(a_name)
            
            # Assign Categories (Deduplicate per book)
            book_categories = set()
            for cat_name in str(row['genre']).split(','):
                c_name = cat_name.strip()
                if c_name in category_map and c_name not in book_categories:
                    book.categories.append(category_map[c_name])
                    book_categories.add(c_name)

            db.session.add(book)
            count += 1
            if count % 1000 == 0:
                print(f"Processed {count} books...")
                try:
                    db.session.commit()
                except IntegrityError as e:
                    db.session.rollback()
                    print(f"IntegrityError encountered at batch {count}. Details:")
                    print(e.orig)
                    return
                except Exception as e:
                    db.session.rollback()
                    print(f"General exception encountered at batch {count}. Details:")
                    print(e)
                    return

        # final commit
        try:
            db.session.commit()
            print(f"Successfully committed {count} books.")
        except IntegrityError as e:
            db.session.rollback()
            print(f"IntegrityError encountered on final commit. Details:")
            print(e.orig)
            return

        # Create an admin user for testing
        print("Creating admin user...")
        from werkzeug.security import generate_password_hash
        admin = User.query.filter_by(email='admin@bookverse.com').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@bookverse.com',
                full_name='Admin User',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
