from datetime import datetime
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
users_collection = db['users']
user_chats_collection = db['user_chats']

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
        news_id = request.args.get('newsId')

        if not user_id or not news_id:
            return jsonify({
                'error': 'userId and newsId are required'
            }), 400

        # Find chat in MongoDB
        chat_data = user_chats_collection.find_one({
            'userId': user_id,
            'newsId': int(news_id)
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
                'newsId': chat_data['newsId']
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)