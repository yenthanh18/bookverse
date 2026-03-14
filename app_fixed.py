from __future__ import annotations

import os
import pickle
import re
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from rapidfuzz import fuzz, process
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(os.getenv('BOOK_API_BASE_DIR', '.')).resolve()
HTML_FILENAME = os.getenv('BOOK_DEMO_HTML', 'book_demo_simple_fixed.html')

# ---------- Helpers ----------

def clean_text(text: Any) -> str:
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_author(text: Any) -> str:
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def shorten_text(text: Any, max_len: int = 220) -> str:
    text = str(text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def safe_float(x: Any, digits: int = 4) -> float | None:
    try:
        return round(float(x), digits)
    except Exception:
        return None


def series_to_book_payload(row: pd.Series, include_description: bool = True) -> dict[str, Any]:
    payload = {
        "book_id": int(row.get("book_id")) if pd.notna(row.get("book_id")) else None,
        "title": row.get("title", ""),
        "authors": row.get("authors", ""),
        "genre": row.get("genre", ""),
        "image_url": row.get("image_url", row.get("small_image_url", "")),
        "average_rating": safe_float(row.get("average_rating", row.get("chat_rating"))),
        "ratings_count": int(row.get("ratings_count")) if pd.notna(row.get("ratings_count")) else None,
    }
    if include_description:
        payload["description"] = row.get("description", "")
        payload["short_description"] = shorten_text(row.get("description", ""))
    return payload


# ---------- Artifact loading ----------

def _load_pickle(name: str):
    path = BASE_DIR / name
    if not path.exists():
        return None
    with open(path, 'rb') as f:
        return pickle.load(f)


item_similarity = _load_pickle('item_similarity.pkl')
book_titles = _load_pickle('book_titles.pkl') or {}
chatbot_vectorizer = _load_pickle('chatbot_vectorizer.pkl')
chatbot_tfidf_matrix = _load_pickle('chatbot_tfidf_matrix.pkl')
books_chatbot = _load_pickle('books_chatbot_processed.pkl')

books_web = None
for candidate in ['books_web_v2.csv', 'books_web.csv']:
    path = BASE_DIR / candidate
    if path.exists():
        books_web = pd.read_csv(path)
        break

if books_web is None:
    books_web = pd.DataFrame(columns=[
        'book_id', 'title', 'authors', 'genre', 'description',
        'average_rating', 'ratings_count', 'image_url', 'small_image_url'
    ])

if books_chatbot is None:
    books_chatbot = pd.DataFrame(columns=[
        'book_id', 'title', 'authors', 'genre', 'description',
        'title_clean', 'authors_clean', 'combined_text'
    ])

# Normalize a few optional columns for safe usage
for col in ['title', 'authors', 'genre', 'description']:
    if col not in books_chatbot.columns:
        books_chatbot[col] = ''
for col in ['title_clean', 'authors_clean']:
    if col not in books_chatbot.columns:
        source = 'title' if 'title' in col else 'authors'
        fn = clean_text if source == 'title' else clean_author
        books_chatbot[col] = books_chatbot[source].fillna('').apply(fn)

if 'title_clean' not in books_web.columns and 'title' in books_web.columns:
    books_web['title_clean'] = books_web['title'].fillna('').apply(clean_text)
if 'authors_clean' not in books_web.columns and 'authors' in books_web.columns:
    books_web['authors_clean'] = books_web['authors'].fillna('').apply(clean_author)

books_web_by_id = books_web.drop_duplicates('book_id').set_index('book_id', drop=False) if not books_web.empty else pd.DataFrame()
books_chatbot_by_id = books_chatbot.drop_duplicates('book_id').set_index('book_id', drop=False) if not books_chatbot.empty else pd.DataFrame()


# ---------- Data lookup ----------

def get_book_record(book_id: int | str) -> pd.Series | None:
    try:
        bid = int(book_id)
    except Exception:
        return None

    if not books_web_by_id.empty and bid in books_web_by_id.index:
        return books_web_by_id.loc[bid]
    if not books_chatbot_by_id.empty and bid in books_chatbot_by_id.index:
        return books_chatbot_by_id.loc[bid]
    return None


def popular_books(top_n: int = 10) -> list[dict[str, Any]]:
    if books_web.empty:
        return []
    df = books_web.copy()
    sort_cols = []
    ascending = []
    if 'average_rating' in df.columns:
        sort_cols.append('average_rating')
        ascending.append(False)
    if 'ratings_count' in df.columns:
        sort_cols.append('ratings_count')
        ascending.append(False)
    if sort_cols:
        df = df.sort_values(sort_cols, ascending=ascending)
    else:
        df = df.sort_values('title')
    return [series_to_book_payload(row, include_description=False) for _, row in df.head(top_n).iterrows()]


# ---------- Recommendation ----------

def recommend_similar_books(book_id: int, top_n: int = 5) -> list[dict[str, Any]]:
    if item_similarity is None or getattr(item_similarity, 'index', None) is None:
        return []
    if book_id not in item_similarity.index:
        return []

    scores = item_similarity.loc[book_id].sort_values(ascending=False)[1: top_n + 1]
    results = []
    for sim_bid, score in scores.items():
        row = get_book_record(sim_bid)
        payload = series_to_book_payload(row, include_description=False) if row is not None else {
            'book_id': int(sim_bid),
            'title': book_titles.get(sim_bid, ''),
            'authors': '',
            'genre': '',
            'image_url': '',
            'average_rating': None,
            'ratings_count': None,
        }
        payload['score'] = safe_float(score)
        results.append(payload)
    return results


def recommend_for_liked_books(liked_book_ids: list[int], top_n: int = 10, top_similar_per_book: int = 20) -> list[dict[str, Any]]:
    if item_similarity is None or getattr(item_similarity, 'index', None) is None:
        return []

    liked_set = set()
    for bid in liked_book_ids:
        try:
            bid = int(bid)
        except Exception:
            continue
        if bid in item_similarity.index:
            liked_set.add(bid)

    if not liked_set:
        return popular_books(top_n)

    scores: dict[int, float] = {}
    for bid in liked_set:
        similar_series = item_similarity.loc[bid].sort_values(ascending=False).iloc[1: top_similar_per_book + 1]
        for sim_bid, sim_score in similar_series.items():
            if sim_bid in liked_set:
                continue
            scores[int(sim_bid)] = scores.get(int(sim_bid), 0.0) + float(sim_score)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    if not ranked:
        return popular_books(top_n)

    results = []
    for sim_bid, score in ranked:
        row = get_book_record(sim_bid)
        payload = series_to_book_payload(row, include_description=False) if row is not None else {
            'book_id': int(sim_bid),
            'title': book_titles.get(sim_bid, ''),
            'authors': '',
            'genre': '',
            'image_url': '',
            'average_rating': None,
            'ratings_count': None,
        }
        payload['score'] = safe_float(score)
        results.append(payload)
    return results


# ---------- Chatbot search ----------

def semantic_search(query: str, top_n: int = 5) -> pd.DataFrame:
    if chatbot_vectorizer is None or chatbot_tfidf_matrix is None or books_chatbot.empty:
        return pd.DataFrame(columns=['book_id', 'title', 'authors', 'genre', 'score', 'description'])

    query_clean = clean_text(query)
    if not query_clean:
        return pd.DataFrame(columns=['book_id', 'title', 'authors', 'genre', 'score', 'description'])

    query_vec = chatbot_vectorizer.transform([query_clean])
    scores = cosine_similarity(query_vec, chatbot_tfidf_matrix).flatten()
    top_indices = scores.argsort()[::-1][:top_n]

    results = books_chatbot.iloc[top_indices][['book_id', 'title', 'authors', 'genre', 'description']].copy()
    results['score'] = scores[top_indices]
    results.reset_index(drop=True, inplace=True)
    return results


def similar_books_by_title(book_title: str, top_n: int = 5) -> pd.DataFrame:
    if chatbot_tfidf_matrix is None or books_chatbot.empty:
        return pd.DataFrame(columns=['book_id', 'title', 'authors', 'genre', 'score', 'description'])

    title_clean = clean_text(book_title)
    if not title_clean:
        return pd.DataFrame(columns=['book_id', 'title', 'authors', 'genre', 'score', 'description'])

    exact_matches = books_chatbot[books_chatbot['title_clean'] == title_clean]
    if not exact_matches.empty:
        idx = exact_matches.index[0]
    else:
        choices = books_chatbot['title_clean'].tolist()
        match = process.extractOne(title_clean, choices, scorer=fuzz.token_sort_ratio, score_cutoff=75)
        if not match:
            return pd.DataFrame(columns=['book_id', 'title', 'authors', 'genre', 'score', 'description'])
        matched_title = match[0]
        idx = books_chatbot[books_chatbot['title_clean'] == matched_title].index[0]

    book_vec = chatbot_tfidf_matrix[idx]
    scores = cosine_similarity(book_vec, chatbot_tfidf_matrix).flatten()
    top_indices = scores.argsort()[::-1][1: top_n + 1]

    results = books_chatbot.iloc[top_indices][['book_id', 'title', 'authors', 'genre', 'description']].copy()
    results['score'] = scores[top_indices]
    results.reset_index(drop=True, inplace=True)
    return results


def books_by_author(author_query: str, top_n: int = 5) -> pd.DataFrame:
    if books_chatbot.empty:
        return pd.DataFrame(columns=['book_id', 'title', 'authors', 'genre', 'description'])

    author_query_clean = clean_author(author_query)
    if not author_query_clean:
        return pd.DataFrame(columns=['book_id', 'title', 'authors', 'genre', 'description'])

    matches = books_chatbot[books_chatbot['authors_clean'].str.contains(author_query_clean, na=False)].copy()
    if matches.empty:
        return pd.DataFrame(columns=['book_id', 'title', 'authors', 'genre', 'description'])

    sort_cols = []
    ascending_vals = []
    if 'average_rating' in matches.columns:
        sort_cols.append('average_rating')
        ascending_vals.append(False)
    if 'ratings_count' in matches.columns:
        sort_cols.append('ratings_count')
        ascending_vals.append(False)
    if sort_cols:
        matches = matches.sort_values(sort_cols, ascending=ascending_vals)
    else:
        matches = matches.sort_values('title')

    return matches[['book_id', 'title', 'authors', 'genre', 'description']].head(top_n).reset_index(drop=True)


# ---------- Chatbot replies ----------

def _format_books_df(results: pd.DataFrame, include_score: bool = False) -> list[dict[str, Any]]:
    payloads = []
    for _, row in results.iterrows():
        item = {
            'book_id': int(row['book_id']) if pd.notna(row.get('book_id')) else None,
            'title': row.get('title', ''),
            'authors': row.get('authors', ''),
            'genre': row.get('genre', ''),
            'description': row.get('description', ''),
            'short_description': shorten_text(row.get('description', '')),
        }
        if include_score:
            item['score'] = safe_float(row.get('score'))
        payloads.append(item)
    return payloads


def semantic_reply(query: str, top_n: int = 3) -> dict[str, Any]:
    results = semantic_search(query, top_n=top_n)
    if results.empty:
        return {
            'mode': 'semantic',
            'message': (
                "I couldn't find a strong match for your request just yet. "
                "Try describing the theme, genre, or reading style you have in mind."
            ),
            'results': []
        }
    return {
        'mode': 'semantic',
        'message': f"You may enjoy these {len(results)} books:",
        'results': _format_books_df(results, include_score=True)
    }


def similar_reply(book_title: str, top_n: int = 3) -> dict[str, Any]:
    results = similar_books_by_title(book_title, top_n=top_n)
    if results.empty:
        return {
            'mode': 'similar',
            'message': f"I couldn't find enough similar titles for '{book_title}'. Please try another book title.",
            'results': []
        }
    return {
        'mode': 'similar',
        'message': f"If you liked '{book_title}', you might also enjoy these {len(results)} books:",
        'results': _format_books_df(results, include_score=True)
    }


def author_reply(author_name: str, top_n: int = 3) -> dict[str, Any]:
    results = books_by_author(author_name, top_n=top_n)
    if results.empty:
        return {
            'mode': 'author',
            'message': f"I couldn't find books by '{author_name}' in the current catalog. Try another author name.",
            'results': []
        }
    return {
        'mode': 'author',
        'message': f"Here are {len(results)} books by '{author_name}' that you may want to explore:",
        'results': _format_books_df(results, include_score=False)
    }


def detect_intent(query: str) -> str:
    q = query.lower().strip()
    if 'same author' in q or 'books by' in q or q.startswith('author:'):
        return 'author'
    if 'similar to' in q or 'books like' in q or q.startswith('similar:'):
        return 'similar'
    return 'semantic'


def extract_author_query(query: str) -> str:
    q = query.strip()
    if q.lower().startswith('author:'):
        return q.split(':', 1)[1].strip()
    if 'books by' in q.lower():
        idx = q.lower().find('books by')
        return q[idx + len('books by'):].strip()
    if 'same author' in q.lower():
        return q.lower().replace('same author', '').strip()
    return q


def extract_similar_title_query(query: str) -> str:
    q = query.strip()
    if q.lower().startswith('similar:'):
        return q.split(':', 1)[1].strip()
    if 'similar to' in q.lower():
        idx = q.lower().find('similar to')
        return q[idx + len('similar to'):].strip()
    if 'books like' in q.lower():
        idx = q.lower().find('books like')
        return q[idx + len('books like'):].strip()
    return q


def chatbot_reply(query: str, top_n: int = 3) -> dict[str, Any]:
    intent = detect_intent(query)
    if intent == 'author':
        return author_reply(extract_author_query(query), top_n=top_n)
    if intent == 'similar':
        return similar_reply(extract_similar_title_query(query), top_n=top_n)
    return semantic_reply(query, top_n=top_n)


# ---------- Flask app ----------
app = Flask(__name__)
CORS(app)


@app.get("/")
def home():
    html_name = "book_demo_simple.html"
    html_path = BASE_DIR / html_name

    if html_path.exists():
        return send_from_directory(str(BASE_DIR), html_name)

    return jsonify({
        "error": "HTML file not found",
        "expected_file": html_name,
        "base_dir": str(BASE_DIR),
        "cwd": os.getcwd(),
        "html_exists": html_path.exists()
    }), 404


@app.get("/__whoami")
def whoami():
    html_name = "book_demo_simple.html"
    html_path = BASE_DIR / html_name
    return jsonify({
        "file": __file__,
        "base_dir": str(BASE_DIR),
        "cwd": os.getcwd(),
        "html_name": html_name,
        "html_exists": html_path.exists()
    })


@app.get('/health')
def health() -> Any:
    return jsonify({
        'status': 'ok',
        'artifacts': {
            'item_similarity': item_similarity is not None,
            'book_titles': bool(book_titles),
            'chatbot_vectorizer': chatbot_vectorizer is not None,
            'chatbot_tfidf_matrix': chatbot_tfidf_matrix is not None,
            'books_chatbot_rows': int(len(books_chatbot)),
            'books_web_rows': int(len(books_web)),
            'html_file': HTML_FILENAME,
            'base_dir': str(BASE_DIR),
        }
    })


@app.get('/books/popular')
def books_popular() -> Any:
    top_n = int(request.args.get('top_n', 10))
    return jsonify({
        'message': f'Here are {top_n} popular books from the catalog.',
        'results': popular_books(top_n)
    })


@app.get('/recommend/similar')
def recommend_similar_api() -> Any:
    book_id = request.args.get('book_id', type=int)
    top_n = request.args.get('top_n', default=5, type=int)
    if book_id is None:
        return jsonify({'error': 'book_id is required'}), 400
    results = recommend_similar_books(book_id, top_n=top_n)
    book = get_book_record(book_id)
    title = book.get('title', '') if book is not None else ''
    return jsonify({
        'message': f"Here are {len(results)} books similar to '{title or book_id}'.",
        'results': results
    })


@app.post('/recommend/user')
def recommend_user_api() -> Any:
    payload = request.get_json(silent=True) or {}
    liked_book_ids = payload.get('liked_book_ids', [])
    top_n = int(payload.get('top_n', 10))
    if not isinstance(liked_book_ids, list):
        return jsonify({'error': 'liked_book_ids must be a list of book IDs'}), 400
    results = recommend_for_liked_books(liked_book_ids, top_n=top_n)
    return jsonify({
        'message': f'Here are {len(results)} personalized recommendations based on the selected books.',
        'input_liked_book_ids': liked_book_ids,
        'results': results
    })


@app.get('/chatbot/search')
def chatbot_search_api() -> Any:
    query = request.args.get('q', '', type=str)
    top_n = request.args.get('top_n', default=5, type=int)
    if not query.strip():
        return jsonify({'error': 'q is required'}), 400
    results = semantic_search(query, top_n=top_n)
    return jsonify({
        'message': f"Here are {len(results)} books that match your request.",
        'query': query,
        'results': _format_books_df(results, include_score=True)
    })


@app.get('/chatbot/similar')
def chatbot_similar_api() -> Any:
    title = request.args.get('title', '', type=str)
    top_n = request.args.get('top_n', default=5, type=int)
    if not title.strip():
        return jsonify({'error': 'title is required'}), 400
    return jsonify(similar_reply(title, top_n=top_n))


@app.get('/chatbot/author')
def chatbot_author_api() -> Any:
    author = request.args.get('author', '', type=str)
    top_n = request.args.get('top_n', default=5, type=int)
    if not author.strip():
        return jsonify({'error': 'author is required'}), 400
    return jsonify(author_reply(author, top_n=top_n))


@app.post('/chatbot/reply')
def chatbot_reply_api() -> Any:
    payload = request.get_json(silent=True) or {}
    query = str(payload.get('query', '')).strip()
    top_n = int(payload.get('top_n', 3))
    if not query:
        return jsonify({'error': 'query is required'}), 400
    return jsonify(chatbot_reply(query, top_n=top_n))


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
