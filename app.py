from flask import Flask, jsonify, request
from flask_cors import CORS
from models.Product import db, Product

app = Flask(__name__)
CORS(app)

# Configure SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///thriftease.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create the database
with app.app_context():
    db.create_all()

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        products = Product.query.all()
        return jsonify([{
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "image_url": product.image_url,
            "category": product.category
        } for product in products]), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch products: {str(e)}"}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    try:
        # Validate input data
        if not all(key in data for key in ("name", "price", "image_url", "category")):
            return jsonify({"error": "Missing required fields"}), 400

        # Create and save the product
        product = Product(
            name=data['name'],
            price=data['price'],
            image_url=data['image_url'],
            category=data['category']
        )
        db.session.add(product)
        db.session.commit()
        return jsonify({"message": "Product added successfully!"}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to add product: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)