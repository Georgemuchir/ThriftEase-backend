from flask import Flask, jsonify, request
from flask_cors import CORS
from models.Product import db, Product, User, Category
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
from marshmallow import Schema, fields, ValidationError

app = Flask(__name__)
CORS(app)

# Configure SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///thriftease.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

SECRET_KEY = 'your_secret_key_here'

# Create the database
with app.app_context():
    db.create_all()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['id'])
        except Exception as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# Define schemas for validation
class SignupSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class SigninSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class ProductSchema(Schema):
    name = fields.Str(required=True)
    category = fields.Str(required=True)
    price = fields.Float(required=True)
    image_url = fields.Url(required=False)
    stock = fields.Int(required=True)

signup_schema = SignupSchema()
signin_schema = SigninSchema()
product_schema = ProductSchema()

@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.all()
        return jsonify([{
            "id": category.id,
            "name": category.name,
            "parent_id": category.parent_id,
            "subcategories": [{
                "id": sub.id,
                "name": sub.name
            } for sub in category.subcategories]
        } for category in categories]), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch categories: {str(e)}"}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        # Get query parameters for filtering and pagination
        category = request.args.get('category')
        subcategory = request.args.get('subcategory')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Build the query
        query = Product.query
        if category:
            query = query.join(Category).filter(Category.name == category)
        if subcategory:
            query = query.join(Category).filter(Category.name == subcategory)

        # Apply pagination
        products = query.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            "products": [{
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "image_url": product.image_url,
                "stock": product.stock,
                "category": product.category.name
            } for product in products.items],
            "total": products.total,
            "pages": products.pages,
            "current_page": products.page
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch products: {str(e)}"}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    try:
        validated_data = product_schema.load(data)
        product = Product(
            name=validated_data['name'],
            category=validated_data['category'],
            price=validated_data['price'],
            image_url=validated_data.get('image_url'),
            stock=validated_data['stock']
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({'message': 'Product added successfully!'}), 201
    except ValidationError as ve:
        return jsonify({'error': ve.messages}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to add product: {str(e)}'}), 500

@app.route('/api/auth/signin', methods=['POST'])
def signin():
    data = request.get_json()
    try:
        validated_data = signin_schema.load(data)
        user = User.query.filter_by(username=validated_data['username']).first()
        if user and user.check_password(validated_data['password']):
            token = jwt.encode({'id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, SECRET_KEY, algorithm='HS256')
            return jsonify({'token': token}), 200
        return jsonify({'error': 'Invalid credentials'}), 401
    except ValidationError as ve:
        return jsonify({'error': ve.messages}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to sign in: {str(e)}'}), 500

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    try:
        validated_data = signup_schema.load(data)
        if User.query.filter_by(username=validated_data['username']).first():
            return jsonify({'error': 'User already exists'}), 400

        user = User(username=validated_data['username'], email=validated_data['email'])
        user.set_password(validated_data['password'])
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully'}), 201
    except ValidationError as ve:
        return jsonify({'error': ve.messages}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to sign up: {str(e)}'}), 500

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    try:
        data = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=['HS256'], options={"verify_exp": False})
        new_token = jwt.encode({'id': data['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, SECRET_KEY, algorithm='HS256')
        return jsonify({'token': new_token}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to refresh token: {str(e)}'}), 401

@app.route('/api/protected', methods=['GET'])
@token_required
def protected_route(current_user):
    return jsonify({'message': f'Welcome {current_user.username}, you have access to this protected route!'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Add a test user for login testing
        if not User.query.filter_by(username='testuser').first():
            user = User(username='testuser', email='testuser@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            print("Test user 'testuser' created with password 'password123'.")
    app.run(debug=True, port=5001)