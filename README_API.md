# Flask API for Smart Book E-commerce

## Files expected in the same folder
- app.py
- requirements.txt
- item_similarity.pkl
- book_titles.pkl
- chatbot_vectorizer.pkl
- chatbot_tfidf_matrix.pkl
- books_chatbot_processed.pkl
- books_web_v2.csv (or books_web.csv)

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
python app.py
```

## Main endpoints
### Health
```bash
GET /health
```

### Popular books
```bash
GET /books/popular?top_n=10
```

### Similar recommendation by book_id
```bash
GET /recommend/similar?book_id=1&top_n=5
```

### Personalized recommendation from liked books
```bash
POST /recommend/user
Content-Type: application/json

{
  "liked_book_ids": [1, 2, 3],
  "top_n": 10
}
```

### Semantic chatbot search
```bash
GET /chatbot/search?q=beginner%20business%20books&top_n=5
```

### Similar books by title
```bash
GET /chatbot/similar?title=Harry%20Potter&top_n=5
```

### Books by the same author
```bash
GET /chatbot/author?author=Rowling&top_n=5
```

### Smart chatbot reply
```bash
POST /chatbot/reply
Content-Type: application/json

{
  "query": "books like Harry Potter",
  "top_n": 3
}
```

## Example chatbot queries
- `I want beginner-friendly business books`
- `books like Harry Potter`
- `books by Rowling`
- `author: Dale Carnegie`
- `similar: Atomic Habits`
