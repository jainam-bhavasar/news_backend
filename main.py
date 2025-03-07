from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.json_util import dumps
import os

app = Flask(__name__)

mongo_pass = os.environ.get("MONGO_PASS")
# MongoDB connection
MONGO_URI = f"mongodb+srv://jainambhavsar95:{mongo_pass}@stocks.3zfgscg.mongodb.net/?retryWrites=true&w=majority&appName=stocks"
client = MongoClient(MONGO_URI)
db = client['news_articles']

@app.route('/api/articles', methods=['GET'])
def get_top_articles():
    """
    API-1: Get top 50 articles for a given date
    Query parameter: date (e.g., '7th_march_2025')
    """
    try:
        date_param = request.args.get('date')
        if not date_param:
            return jsonify({"error": "Date parameter is required"}), 400
        
        collection_name = f"news_{date_param}"
        
        # Check if collection exists
        if collection_name not in db.list_collection_names():
            return jsonify({"error": f"No articles found for date {date_param}"}), 404
        
        collection = db[collection_name]
        
        # Try to sort by rank if it exists, otherwise use newsId
        try:
            articles = list(collection.find().sort("rank", 1).limit(50))
            if len(articles) == 0 and collection.count_documents({}) > 0:
                # If rank doesn't exist, fall back to newsId
                articles = list(collection.find().sort("newsId", 1).limit(50))
        except Exception:
            articles = list(collection.find().sort("newsId", 1).limit(50))
        
        return dumps(articles), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/article', methods=['GET'])
def get_article():
    """
    API-2: Get a specific article by date and newsId
    Query parameters: date (e.g., '7th_march_2025') and newsId
    """
    try:
        date_param = request.args.get('date')
        news_id = request.args.get('newsId')
        
        if not date_param or not news_id:
            return jsonify({"error": "Both date and newsId parameters are required"}), 400
        
        try:
            news_id = int(news_id)
        except ValueError:
            return jsonify({"error": "newsId must be an integer"}), 400
        
        collection_name = f"news_{date_param}"
        
        if collection_name not in db.list_collection_names():
            return jsonify({"error": f"No articles found for date {date_param}"}), 404
        
        collection = db[collection_name]
        article = collection.find_one({"newsId": news_id})
        
        if not article:
            return jsonify({"error": f"Article with newsId {news_id} not found"}), 404
        
        return dumps(article), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)