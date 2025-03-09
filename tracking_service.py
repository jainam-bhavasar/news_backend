import numpy as np
from bson import ObjectId

class TrackingService:
    def __init__(self, articles_collection):
        self.articles_collection = articles_collection

    def calculate_interaction_strength(self, article_id, view_time_seconds):
        """
        Calculate interaction strength based on view time and article content.
        
        Parameters:
        - article_id: ID of the article that was read
        - view_time_seconds: How long user spent viewing the article (in seconds)
        
        Returns:
        - interaction_strength: Normalized score (0.0-1.2) representing engagement
        """
        # Ignore very short views (likely accidental clicks or bounces)
        if view_time_seconds < 5:
            return 0.0

        try:
            # Get article content length
            article = self.articles_collection.find_one({"_id": ObjectId(article_id)})
            if not article or 'content' not in article:
                return 0.0

            # Calculate word count and estimated read time
            word_count = len(article['content'].split())
            estimated_read_time = word_count / 250 * 60  # In seconds (250 words/min)

            # Calculate normalized engagement score using logarithmic scale
            if estimated_read_time > 0:
                engagement_ratio = min(1.0, 0.3 + (0.7 * np.log(1 + view_time_seconds) /
                                                  np.log(1 + estimated_read_time)))
            else:
                engagement_ratio = 0.3  # Fallback if article length data is missing

            # Adjust score based on engagement thresholds
            if view_time_seconds > estimated_read_time * 1.2:
                # User spent significantly more time than expected (high engagement)
                interaction_strength = 1.2
            elif engagement_ratio > 0.7:
                # User read most of the article
                interaction_strength = 1.0
            elif engagement_ratio > 0.4:
                # User read a significant portion
                interaction_strength = 0.8
            elif engagement_ratio > 0.2:
                # User skimmed the article
                interaction_strength = 0.5
            else:
                # User barely engaged with content
                interaction_strength = 0.3

            return interaction_strength

        except Exception as e:
            print(f"Error calculating interaction strength: {e}")
            return 0.0 