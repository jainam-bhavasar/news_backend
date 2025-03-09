from datetime import datetime
from bson import ObjectId
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.json_util import dumps
import os
from google import genai
from models.user_chat import UserChat, ChatMessage

app = Flask(__name__)

mongo_pass = os.environ.get("MONGO_PASS")
# MongoDB connection
MONGO_URI = f"mongodb+srv://jainambhavsar95:{mongo_pass}@stocks.3zfgscg.mongodb.net/?retryWrites=true&w=majority&appName=stocks"
client = MongoClient(MONGO_URI)
db = client['news_articles']
articles_collection = db['all_articles']
users_collection = db['users']
user_chats_collection = db['user_chats']

# Initialize Gemini client
genai_client = genai.Client(api_key="AIzaSyCJpSC__LjrvsIuazWA2HfFiUURhT5QgRw")

def get_embedding(text):
    """Generate embedding for given text using Gemini API"""
    try:
        result = genai_client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        # Convert ContentEmbedding object to a regular list
        return result.embeddings[0].values  # Get the first embedding's values as a list
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def perform_vector_search(query_text, num_results=5):
    """Perform vector search on articles collection."""
    query_embedding = get_embedding(query_text)
    if query_embedding is None:
        raise Exception("Failed to generate embedding for search query")
        
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vectorSearch",
                "queryVector": query_embedding,
                "path": "embedding",
                "numCandidates": 10,
                "limit": num_results,
            }
        },
        {
            "$project": {
                "_id": 1,
                "embedding": 0,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    results = list(articles_collection.aggregate(pipeline))
    return results

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
        
        
        # Query articles for the specific date and sort by rank or newsId
        try:
            articles = list(articles_collection.find(
                {"date": date_param},
                {"embedding": 0}
            ).sort("rank", 1).limit(50))
            if len(articles) == 0:
                # If rank doesn't exist, fall back to newsId
                articles = list(articles_collection.find(
                    {"date": date_param},
                    {"embedding": 0}
                ).sort("newsId", 1).limit(50))
        except Exception:
            articles = list(articles_collection.find(
                {"date": date_param},
                {"embedding": 0}
            ).sort("newsId", 1).limit(50))
        
        if not articles:
            return jsonify({"error": f"No articles found for date {date_param}"}), 404
            
        return dumps(articles), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/article', methods=['GET'])
def get_article():
    """
    API-2: Get a specific article by document ID
    Query parameter: id (MongoDB document _id)
    """
    try:
        doc_id = request.args.get('id')
        
        if not doc_id:
            return jsonify({"error": "Document ID parameter is required"}), 400
        
        try:
            from bson.objectid import ObjectId
            article = articles_collection.find_one({"_id": ObjectId(doc_id)})
        except Exception:
            return jsonify({"error": "Invalid document ID format"}), 400
            
        if not article:
            return jsonify({"error": f"Article with ID {doc_id} not found"}), 404
        
        return dumps(article), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/users', methods=['POST'])
def register_user():
    try:
        user_data = request.json
        
        # Required fields from Google Sign In
        required_fields = ['email', 'displayName', 'uid']
        if not all(field in user_data for field in required_fields):
            return jsonify({
                'error': 'Missing required fields'
            }), 400
        
        # Check if user already exists
        existing_user = users_collection.find_one({'uid': user_data['uid']})

        if existing_user:
            # Update last login time
            users_collection.update_one(
                {'uid': user_data['uid']},
                {'$set': {'lastLoginAt': datetime.utcnow()}}
            )
            return jsonify({
                'message': 'User login recorded',
                'userId': str(existing_user['_id'])
            }), 200
        
        # Add additional fields
        user_data['createdAt'] = datetime.now()
        user_data['lastLoginAt'] = datetime.now()
           
        # Insert new user
        result = users_collection.insert_one(user_data)
        
        return jsonify({
            'message': 'User registered successfully',
            'userId': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
@app.route('/api/users/logout', methods=['POST'])
def logout_user():
    try:
        user_data = request.json
        
        # Required field
        if 'uid' not in user_data:
            return jsonify({
                'error': 'Missing user ID'
            }), 400
        
        # Update last logout time
        result = users_collection.update_one(
            {'uid': user_data['uid']},
            {'$set': {'lastLogoutAt': datetime.now()}}
        )
        
        if result.modified_count == 0:
            return jsonify({
                'error': 'User not found'
            }), 404
            
        return jsonify({
            'message': 'User logout recorded successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
        
@app.route('/api/chat', methods=['POST'])
def chat_with_article():
    try:
        data = request.json
        user_message = data.get('message')
        article_context = data.get('articleContext')
        chat_history = data.get('chatHistory', [])
        
        if not user_message or not article_context:
            return jsonify({
                'error': 'Message and article context are required'
            }), 400
        
      
        gemini_client = genai.Client(api_key="AIzaSyCJpSC__LjrvsIuazWA2HfFiUURhT5QgRw")
        model = "gemini-2.0-flash"
        # Start a new chat if no history
        if chat_history:
            
            article_content = article_context.get('content', '')
            
            conversation_prompt = f"""
            You are a helpful AI assistant that helps users understand news articles.
            If they are curious and want to know more about other things , then don't hesitate to answer.
            
            Article: {article_content}
            
            Previous conversation history:
            {chat_history}
            
            user message: {user_message}
            your response (only answer the question):
            """
            
            # Generate the response with the correct format
            response = gemini_client.models.generate_content(contents= conversation_prompt,model=model)
            
            return jsonify({
                'response': response.text,
            }), 200
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/user-chat', methods=['GET'])
def get_user_chat():
    try:
        user_id = request.args.get('userId')
        article_id = request.args.get('articleId')

        if not user_id or not article_id:
            return jsonify({
                'error': 'userId and newsId are required'
            }), 400

        # Find chat in MongoDB
        chat_data = user_chats_collection.find_one({
            'userId': user_id,
            'articleId': article_id,
        })

        if not chat_data:
            return '', 404

        # Convert MongoDB document to UserChat model
        chat = UserChat.from_mongo(chat_data)
        return jsonify(chat.dict(by_alias=True))

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/user-chat', methods=['POST'])
def save_user_chat():
    try:
        chat_data = request.json
        
        # Ensure required fields are present
        if 'userId' not in chat_data:
            return jsonify({
                'error': 'userId is required'
            }), 400
            
        if 'articleId' not in chat_data:
            return jsonify({
                'error': 'articleId is required'
            }), 400
            
        if 'messages' not in chat_data:
            chat_data['messages'] = []
        
        # Validate input data using Pydantic model
        chat = UserChat(**chat_data)
        
        # Convert to MongoDB format
        mongo_data = chat.to_mongo()
        
        # Remove _id if it's empty (new chat)
        if not mongo_data.get('_id'):
            mongo_data.pop('_id', None)

        # Upsert the chat document
        result = user_chats_collection.update_one(
            {
                'userId': chat_data['userId'],
                'articleId': chat_data['articleId']
            },
            {'$set': mongo_data},
            upsert=True
        )

        return jsonify({
            'success': True,
            'modified': result.modified_count > 0,
            'upserted': result.upserted_id is not None
        })

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
@app.route('/api/chat-history', methods=['GET'])
def get_chat_history():
    try:
        user_id = request.args.get('userId')
        if not user_id:
            return jsonify({
                'error': 'userId is required'
            }), 400

        # Get all chats for this user, sorted by createdAt in descending order
        chat_history = list(user_chats_collection.find({'userId': user_id}))
        if not chat_history:
            return jsonify([]), 200

        # Get all article IDs from chat history
        article_ids = [ObjectId(chat['articleId']) for chat in chat_history]
       
        # Get all articles in one query
        articles = list(articles_collection.find({
            '_id': {'$in': article_ids}
        }))
    
        print("found articles",len(articles))
        return dumps(articles), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/vector-search', methods=['GET'])
def search_articles():
    """
    API endpoint for semantic vector search of articles
    Query parameters:
    - query: Search query text
    - limit: Number of results to return (default: 5)
    """
    try:
        query = request.args.get('query')
        limit = int(request.args.get('limit', 5))

        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        results = perform_vector_search(query, limit)
        return dumps(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/related-articles', methods=['GET'])
def get_related_articles():
    """
    API endpoint to fetch related articles based on vector similarity
    Query parameters:
    - id: MongoDB document ID of the source article
    - limit: Number of related articles to return (default: 5)
    """
    try:
        article_id = request.args.get('id')
        limit = int(request.args.get('limit', 5))

        if not article_id:
            return jsonify({"error": "Article ID parameter is required"}), 400

        # Get the source article
        try:
            source_article = articles_collection.find_one({"_id": ObjectId(article_id)})
        except Exception:
            return jsonify({"error": "Invalid article ID format"}), 400

        if not source_article:
            return jsonify({"error": f"Article with ID {article_id} not found"}), 404

        # Get the embedding from the source article
        source_embedding = source_article.get('embedding')
        if not source_embedding:
            return jsonify({"error": "Source article does not have an embedding"}), 400

        # Perform vector search using the source article's embedding
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vectorSearch",
                    "queryVector": source_embedding,
                    "path": "embedding",
                    "numCandidates": 10,
                    "limit": limit + 1,  # Add 1 to account for the source article
                }
            },
            {
                "$match": {
                    "_id": {"$ne": ObjectId(article_id)}  # Exclude the source article
                }
            },
            {
                "$limit": limit
            },
            {
                "$project": {
                    "embedding": 0  # Exclude embedding from results
                }
            }
        ]
        
        results = list(articles_collection.aggregate(pipeline))
        return dumps(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)