# news_recommender.py
import numpy as np
import time
from typing import List, Dict, Optional
from sklearn.metrics.pairwise import cosine_similarity
import pymongo
from flask import Flask, request, jsonify
from bson.objectid import ObjectId

# MongoDB connection
mongo_client = pymongo.MongoClient("mongodb+srv://jainambhavsar95:Gr8estSecr8Is%3F@stocks.3zfgscg.mongodb.net/?retryWrites=true&w=majority&appName=stocks")
db = mongo_client["news_articles"]
impressions_collection = db["impressions"]
all_articles_collection = db["all_articles"]


# ===== Data Structures =====

class Article:
    """Article data structure with embedding support"""
    @classmethod
    def from_dict(cls, data):
        """Create Article from dictionary"""
        article = cls()
        article.id = str(data["_id"])
        article.headline = data["headline"]
        article.content = data["content"]
        article.category = data["category"]
        article.newspaper = data["newspaper"]
        article.newsId = data["newsId"]
        article.date = data.get("date")
        article.summary = data.get("summary")
        article.faqs = data.get("faqs")
        article.importance_score = data.get("importanceScore")
        
        if data.get("embedding"):
            article.embedding = np.array(data["embedding"])
        return article


class TimeWeightedProfile:
    """User profile with time-weighted centroids"""
    def __init__(self, user_id: str, decay_factor: float = 0.1):
        self.user_id = user_id
        self.decay_factor = decay_factor  # Controls how quickly older interactions lose importance
    
    def get_interest_centroid(self) -> Optional[np.ndarray]:
        """Calculate and return the time-weighted interest centroid"""
        # Get all interactions for this user
        user_interactions = list(impressions_collection.find({"userId": self.user_id}))
        if not user_interactions:
            return None
        
        # Get all article embeddings and interaction strengths
        embeddings = []
        timestamps = []
        strengths = []
        
        for interaction in user_interactions:
            article_id = interaction["articleId"]
            
            # Get article from database
            article_data = all_articles_collection.find_one({"_id": ObjectId(article_id)})
            if not article_data or "embedding" not in article_data:
                continue
                
            embedding = np.array(article_data["embedding"])
            timestamp = interaction.get("timestamp", time.time())
            strength = interaction.get("interactionStrength", 1.0)
            
            embeddings.append(embedding)
            timestamps.append(timestamp)
            strengths.append(strength)
        
        if not embeddings:
            return None
        
        # Calculate time weights
        current_time = time.time()
        weights = []
        
        for timestamp, strength in zip(timestamps, strengths):
            # Calculate age in days
            age_in_seconds = current_time - timestamp
            age_in_days = age_in_seconds / (24 * 3600)
            
            # Exponential decay based on age
            time_weight = np.exp(-self.decay_factor * age_in_days)
            
            # Combine with interaction strength
            final_weight = time_weight * strength
            
            weights.append(final_weight)
        
        # Convert to numpy arrays
        weights_array = np.array(weights)
        embeddings_array = np.array(embeddings)
        
        # Normalize weights
        if np.sum(weights_array) > 0:
            weights_array = weights_array / np.sum(weights_array)
            # Calculate weighted average
            return np.sum(embeddings_array * weights_array[:, np.newaxis], axis=0)
           
        return None


