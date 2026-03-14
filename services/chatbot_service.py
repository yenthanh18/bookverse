import os
import re
import pickle
import pandas as pd
from typing import Any, List, Dict
from flask import current_app
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz, process
from models.models import db, Book, Author

class ChatbotService:
    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.books_chatbot = pd.DataFrame()
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            base_dir = os.environ.get('AI_MODELS_DIR', '.')
            
            vectorizer_path = os.path.join(base_dir, 'chatbot_vectorizer.pkl')
            if os.path.exists(vectorizer_path):
                with open(vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                    
            tfidf_path = os.path.join(base_dir, 'chatbot_tfidf_matrix.pkl')
            if os.path.exists(tfidf_path):
                with open(tfidf_path, 'rb') as f:
                    self.tfidf_matrix = pickle.load(f)
                    
            chatbot_books_path = os.path.join(base_dir, 'books_chatbot_processed.pkl')
            if os.path.exists(chatbot_books_path):
                with open(chatbot_books_path, 'rb') as f:
                    self.books_chatbot = pickle.load(f)
                    if self.books_chatbot is None:
                         self.books_chatbot = pd.DataFrame()
        except Exception as e:
            print(f"Error loading chatbot artifacts: {e}")

    def _clean_text(self, text: Any) -> str:
        if pd.isna(text) or not text:
            return ""
        text = str(text).lower()
        text = re.sub(r"<.*?>", " ", text)
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def semantic_search(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        if self.vectorizer is None or self.tfidf_matrix is None or self.books_chatbot.empty:
            return []

        query_clean = self._clean_text(query)
        if not query_clean:
            return []

        query_vec = self.vectorizer.transform([query_clean])
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = scores.argsort()[::-1][:top_n]

        results = []
        for idx in top_indices:
            row = self.books_chatbot.iloc[idx]
            book_id = int(row.get('book_id')) if pd.notna(row.get('book_id')) else None
            if book_id:
                book = Book.query.get(book_id)
                if book:
                    formatted = self._format_book(book)
                    formatted['similarity_score'] = round(float(scores[idx]), 4)
                    results.append(formatted)
        return results

    def similar_books_by_title(self, book_title: str, top_n: int = 5) -> List[Dict[str, Any]]:
        if self.tfidf_matrix is None or self.books_chatbot.empty:
               return []

        title_clean = self._clean_text(book_title)
        if not title_clean:
               return []

        # Find the best matching book title
        exact_matches = self.books_chatbot[self.books_chatbot['title_clean'] == title_clean]
        if not exact_matches.empty:
            idx = exact_matches.index[0]
        else:
            choices = self.books_chatbot['title_clean'].tolist()
            match = process.extractOne(title_clean, choices, scorer=fuzz.token_sort_ratio, score_cutoff=75)
            if not match:
                return []
            matched_title = match[0]
            idx = self.books_chatbot[self.books_chatbot['title_clean'] == matched_title].index[0]

        book_vec = self.tfidf_matrix[idx]
        scores = cosine_similarity(book_vec, self.tfidf_matrix).flatten()
        top_indices = scores.argsort()[::-1][1: top_n + 1]

        results = []
        for match_idx in top_indices:
            row = self.books_chatbot.iloc[match_idx]
            book_id = int(row.get('book_id')) if pd.notna(row.get('book_id')) else None
            if book_id:
                  book = Book.query.get(book_id)
                  if book:
                       formatted = self._format_book(book)
                       formatted['similarity_score'] = round(float(scores[match_idx]), 4)
                       results.append(formatted)
        return results

    def books_by_author(self, author_name: str, top_n: int = 5) -> List[Dict[str, Any]]:
          author_clean = self._clean_text(author_name)
          if not author_clean:
               return []
          
          # Query by relationship
          books = Book.query.join(Book.authors).filter(db.func.lower(db.cast(Author.name, db.String)).contains(author_clean)).order_by(Book.ratings_count.desc().nulls_last()).limit(top_n).all()
          return [self._format_book(b) for b in books]

    def _format_book(self, book: Book) -> Dict[str, Any]:
        return {
            'book_id': book.id,
            'title': book.title,
            'slug': book.slug,
            'authors': ', '.join([a.name for a in book.authors]),
            'price': book.price,
            'discount_price': book.discount_price,
            'image_url': book.image_url or book.small_image_url,
            'average_rating': book.average_rating,
            'short_description': (book.description[:150] + '...') if book.description and len(book.description) > 150 else book.description
        }

    def process_query(self, query: str, top_n: int = 5) -> Dict[str, Any]:
        q = query.lower().strip()
        
        # 1. Synonym Normalization
        synonyms = {
            "scifi": "science fiction",
            "sci-fi": "science fiction",
            "ya": "young adult",
            "rom-com": "romance",
            "thrillers": "thriller",
            "mysteries": "mystery",
            "biographies": "biography",
            "suggest me": "recommend",
            "looking for": "recommend"
        }
        for syn, canonical in synonyms.items():
            q = re.sub(r'\b' + re.escape(syn) + r'\b', canonical, q)
        
        # 2. Predefined Explicit Intents
        if 'similar to' in q or 'books like' in q or q.startswith('similar:'):
             title_query = q.replace('similar to', '').replace('books like', '').replace('similar:', '').strip()
             results = self.similar_books_by_title(title_query, top_n=top_n)
             if results:
                  return {'message': f"If you liked '{title_query}', you might also enjoy:", 'results': results}
             else:
                  return {'message': f"I couldn't find enough similar titles for '{title_query}'. Please try another book title.", 'results': []}

        if 'same author' in q or 'books by' in q or 'author:' in q:
             author_query = q.replace('same author', '').replace('books by', '').replace('author:', '').strip()
             results = self.books_by_author(author_query, top_n=top_n)
             if results:
                  return {'message': f"Here are some books by '{author_query}':", 'results': results}
             else:
                  return {'message': f"I couldn't find books by '{author_query}'. Please try another author.", 'results': []}

        # 3. Fuzzy Matching for Genres
        genres = ["science fiction", "fantasy", "romance", "thriller", "mystery", "horror", "historical", "young adult", "non-fiction", "biography", "classics", "poetry", "business"]
        genre_match = process.extractOne(q, genres, scorer=fuzz.partial_token_sort_ratio, score_cutoff=85)
        if genre_match:
             matched_genre = genre_match[0]
             results = self.semantic_search(f"{matched_genre} book", top_n=top_n)
             if results:
                 return {'message': f"Here are some excellent {matched_genre} recommendations:", 'results': results}
                 
        # 4. Fuzzy Matching for Authors (Fallback)
        try:
             # Fast check if query matches an author name
             author_match_db = Author.query.filter(db.func.lower(Author.name).contains(q)).first()
             if author_match_db and len(q) > 3:
                 results = self.books_by_author(author_match_db.name, top_n=top_n)
                 if results:
                     return {'message': f"I found some books by {author_match_db.name}:", 'results': results}
        except Exception:
             pass

        # 5. Semantic Search Fallback
        results = self.semantic_search(q, top_n=top_n)
        if not results:
             return {'message': "I couldn't find a strong match for your request. Try describing the genre or theme you're looking for.", 'results': []}
             
        return {'message': "Based on your request, you may enjoy these books:", 'results': results}

chatbot_service = ChatbotService()
