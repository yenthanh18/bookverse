from flask import Blueprint, request, jsonify
from services.recommendation_service import recommendation_service
from services.chatbot_service import chatbot_service

api_bp = Blueprint('api_bp', __name__)

@api_bp.route('/chatbot', methods=['POST'])
def chatbot_endpoint():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'message': 'No query provided', 'results': []}), 400
        
    query = data['query']
    response = chatbot_service.process_query(query)
    
    return jsonify(response)
