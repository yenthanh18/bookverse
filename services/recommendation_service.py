import os
import pickle
import pandas as pd
from typing import Any, List, Dict
from flask import current_app
from models.models import db, Book

class RecommendationService:
    def __init__(self):
        self.item_similarity = None
        self.book_titles = {}
        self._load_artifacts()

    def _load_artifacts(self):
        try:
            base_dir = os.environ.get('AI_MODELS_DIR', '.')
            
            similarity_path = os.path.join(base_dir, 'item_similarity.pkl')
            if os.path.exists(similarity_path):
                with open(similarity_path, 'rb') as f:
                    self.item_similarity = pickle.load(f)
                    
            titles_path = os.path.join(base_dir, 'book_titles.pkl')
            if os.path.exists(titles_path):
                with open(titles_path, 'rb') as f:
                    self.book_titles = pickle.load(f) or {}
                    
        except Exception as e:
            print(f"Error loading recommendation artifacts: {e}")

    def get_popular_books(self, top_n: int = 10) -> List[Dict[str, Any]]:
        books = Book.query.order_by(Book.ratings_count.desc().nulls_last(), Book.average_rating.desc().nulls_last()).limit(top_n).all()
        return [self._format_book(b) for b in books]

    def recommend_similar_books(self, book_id: int, top_n: int = 5) -> List[Dict[str, Any]]:
        if self.item_similarity is None or not hasattr(self.item_similarity, 'index'):
            return self.get_popular_books(top_n)
            
        if book_id not in self.item_similarity.index:
            return self.get_popular_books(top_n)

        # Get top similar book IDs, excluding the book itself (similarity=1.0)
        # Assuming the matrix includes the book itself at position 0
        scores = self.item_similarity.loc[book_id].sort_values(ascending=False)[1: top_n + 1]
        
        results = []
        for sim_bid, score in scores.items():
            book = Book.query.get(int(sim_bid))
            if book:
                formatted = self._format_book(book)
                formatted['similarity_score'] = round(float(score), 4)
                results.append(formatted)
        return results

    def recommend_for_liked_books(self, liked_book_ids: List[int], top_n: int = 10, top_similar_per_book: int = 20) -> List[Dict[str, Any]]:
        if self.item_similarity is None or not hasattr(self.item_similarity, 'index'):
            return self.get_popular_books(top_n)

        liked_set = set()
        for bid in liked_book_ids:
            try:
                bid = int(bid)
                if bid in self.item_similarity.index:
                    liked_set.add(bid)
            except (ValueError, TypeError):
                continue

        if not liked_set:
            return self.get_popular_books(top_n)

        scores: Dict[int, float] = {}
        for bid in liked_set:
            similar_series = self.item_similarity.loc[bid].sort_values(ascending=False).iloc[1: top_similar_per_book + 1]
            for sim_bid, sim_score in similar_series.items():
                if sim_bid in liked_set:
                    continue
                scores[int(sim_bid)] = scores.get(int(sim_bid), 0.0) + float(sim_score)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        if not ranked:
            return self.get_popular_books(top_n)

        results = []
        for sim_bid, score in ranked:
            book = Book.query.get(int(sim_bid))
            if book:
                formatted = self._format_book(book)
                formatted['recommendation_score'] = round(float(score), 4)
                results.append(formatted)
        return results

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
            'ratings_count': book.ratings_count
        }

recommendation_service = RecommendationService()
