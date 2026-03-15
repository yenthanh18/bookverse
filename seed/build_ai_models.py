import os
import sys
import pandas as pd
import pickle
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def build_models():
    print("[AI BUILD] Starting AI model artifact generation...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Locate dataset
    csv_path = os.path.join(base_dir, 'seed', 'books_store_ready.csv')
    if not os.path.exists(csv_path):
        csv_path = os.path.join(base_dir, 'books_store_ready.csv')
        
    if not os.path.exists(csv_path):
        print(f"[AI BUILD ERROR] Could not find {csv_path}")
        return

    print(f"[AI BUILD] Loading CSV from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # We'll use a clean DataFrame specifically for Chatbot
    print("[AI BUILD] Cleaning text data...")
    df['title_clean'] = df['title'].apply(clean_text)
    df['authors_clean'] = df['authors'].fillna('Unknown').apply(clean_text)
    df['genre_clean'] = df['genre'].fillna('Uncategorized').apply(clean_text)
    df['desc_clean'] = df['description'].fillna('').apply(clean_text)
    
    # Combined features for semantic search
    df['combined_features'] = df['title_clean'] + " " + df['authors_clean'] + " " + df['genre_clean'] + " " + df['desc_clean']
    
    print("[AI BUILD] Building TF-IDF Vectorizer...")
    vectorizer = TfidfVectorizer(stop_words='english', max_features=10000)
    tfidf_matrix = vectorizer.fit_transform(df['combined_features'])
    
    # Save Chatbot Artifacts
    print("[AI BUILD] Saving Chatbot Models...")
    with open(os.path.join(base_dir, 'chatbot_vectorizer.pkl'), 'wb') as f:
        pickle.dump(vectorizer, f)
    with open(os.path.join(base_dir, 'chatbot_tfidf_matrix.pkl'), 'wb') as f:
        pickle.dump(tfidf_matrix, f)
    with open(os.path.join(base_dir, 'books_chatbot_processed.pkl'), 'wb') as f:
        pickle.dump(df, f)
        
    print("[AI BUILD] Building Recommendation Item Similarity Matrix...")
    # Compute similarity between books. To save disk/memory config, we compute full cosine similarity
    # for a subset and limit the size.
    # Alternatively, compute dense similarity for top ~1000 popular books so item_similarity.pkl stays light.
    top_books = df.sort_values('ratings_count', ascending=False).head(3000)
    top_tfidf = vectorizer.transform(top_books['combined_features'])
    sim_matrix = cosine_similarity(top_tfidf)
    
    item_sim_df = pd.DataFrame(sim_matrix, index=top_books['book_id'], columns=top_books['book_id'])
    
    print("[AI BUILD] Saving Recommendation Models...")
    with open(os.path.join(base_dir, 'item_similarity.pkl'), 'wb') as f:
        pickle.dump(item_sim_df, f)
        
    titles_dict = dict(zip(df['book_id'], df['title']))
    with open(os.path.join(base_dir, 'book_titles.pkl'), 'wb') as f:
        pickle.dump(titles_dict, f)
        
    print("[AI BUILD] Successfully rebuilt all AI artifacts for production constraints!")

if __name__ == '__main__':
    build_models()
