from typing import List, Dict
from timeline_profile import TimeWeightedProfile, Article
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient

ARTICLE_IMPORTANCE_SCORE = 0.5
class NewsRecommender:
    """Recommendation service for financial news"""
    def __init__(self, client):
        self.client = client
        
    
    def get_recommendations(self, user_id: str, date: str, excluded_article_ids: List[str] = None, 
                           count: int = 18, is_initial_feed: bool = False) -> List[Dict]:
        """
        Unified recommendation function that handles both initial feed and follow-up recommendations
        
        Parameters:
        - user_id: ID of the user
        - date: Date to filter articles (format: "DD-MM-YYYY")
        - excluded_article_ids: List of article IDs to exclude (for follow-up recommendations)
        - count: Number of articles to return
        - is_initial_feed: Whether this is the initial feed request
        """
        # Get articles for the specified date
        query = {"date": date}
        db = self.client['news_articles']
        all_articles_collection = db['all_articles']
        impressions_collection = db['impressions']
        users_collection = db['users']

        articles_data = list(all_articles_collection.find(query))
        # articles = [Article.from_dict(data) for data in articles_data]
        

        if not articles_data:
            return []
            
        # Filter out excluded articles if provided
        if excluded_article_ids:
            available_articles = [article for article in articles_data 
                                 if str(article["_id"]) not in excluded_article_ids]
        else:
            available_articles = articles_data
            
        # Get user profile and calculate centroid
        user_profile = TimeWeightedProfile(user_id)
        user_centroid = user_profile.get_interest_centroid()
        # For new users or if it's initial feed without user history
        user_has_interactions = impressions_collection.count_documents({"userId": user_id}) > 0
        if user_centroid is None or (is_initial_feed and not user_has_interactions):
            # Return editorial content
            sorted_articles = sorted(available_articles, key=lambda x: x["rank"], reverse=False)
            return sorted_articles[:count]
            
        
        # Score articles by similarity to interest centroid
        article_scores = []
        
        for article in available_articles:
            # Calculate similarity
            similarity = cosine_similarity([user_centroid], [article["embedding"]])[0][0]
            
            # Calculate final score (combine with editorial importance)
            final_score = (0.7 * similarity) + (0.3 * article["importanceScore"])
            
            article_scores.append((article, final_score))
        
        # For initial feed, create a blended result
        if is_initial_feed:
            # Sort all articles by editorial importance
            editorial_top = sorted(available_articles, key=lambda x: x["importanceScore"], reverse=True)
            
            # Sort articles by personalization score
            article_scores.sort(key=lambda x: x[1], reverse=True)
            personalized = [article for article, _ in article_scores[:15]]
            
            # Create blended feed
            feed = []
            editorial_weight = 0.4  # 40% editorial, 60% personalized
            editorial_count = int(count * editorial_weight)
            personalized_count = count - editorial_count
            
            # Take top editorial content
            feed.extend(editorial_top[:editorial_count])
            
            # Add personalized content, avoiding duplicates
            added = 0
            for article in personalized:
                if article not in feed and added < personalized_count:
                    feed.append(article)
                    added += 1
            
            # Fill remaining slots with editorial if needed
            remaining = count - len(feed)
            if remaining > 0:
                for article in editorial_top[editorial_count:]:
                    if article not in feed and len(feed) < count:
                        feed.append(article)
            return feed
        
        # For follow-up recommendations, just return the top scored articles
        else:
            # Sort by score and return top results
            article_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return minimal article data
            return [article for article, _ in article_scores[:count]]





