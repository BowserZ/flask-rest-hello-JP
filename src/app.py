"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, People, Planet, Favorite
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.url_map.strict_slashes = False

# Configuración de la base de datos
db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración JWT
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET") 
jwt = JWTManager(app)

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

# ====== AUTH ENDPOINTS ======
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validación básica
    if not data.get('email') or not data.get('password'):
        raise APIException('Email and password are required', status_code=400)
    
    if User.query.filter_by(email=data.get('email')).first():
        raise APIException('Email already registered', status_code=400)
    
    user = User(
        email=data['email'],
        password=generate_password_hash(data['password']),
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg": "User created successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    password = request.json.get('password')
    
    if not email or not password:
        raise APIException('Email and password are required', status_code=400)
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password, password):
        raise APIException('Invalid credentials', status_code=401)
    
    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200

# ====== STAR WARS ENDPOINTS ======
@app.route('/people', methods=['GET', 'POST']) 
def handle_people():
    if request.method == 'POST':
        data = request.get_json()
        # Validación básica
        if not data.get('name') or not data.get('height') or not data.get('mass'):
            raise APIException('Name, height and mass are required', status_code=400)
            
        new_person = People(
            name=data['name'],
            height=data['height'],
            mass=data['mass']
        )
        db.session.add(new_person)
        db.session.commit()
        return jsonify(new_person.serialize()), 201
    
    else:  # GET
        people = People.query.all()
        return jsonify([person.serialize() for person in people]), 200
    

@app.route('/people/<int:people_id>', methods=['GET'])
def get_one_person(people_id):
    person = People.query.get(people_id)
    if not person:
        raise APIException('Person not found', status_code=404)
    return jsonify(person.serialize()), 200

@app.route('/planets', methods=['GET', 'POST'])  # ¡Ahora acepta POST!
def handle_planets():
    if request.method == 'POST':
        data = request.get_json()
        
        # Validación de campos requeridos
        required_fields = ['name', 'climate', 'terrain']
        if not all(field in data for field in required_fields):
            raise APIException('Missing required fields: name, climate, terrain', status_code=400)
            
        new_planet = Planet(
            name=data['name'],
            climate=data['climate'],
            terrain=data['terrain'],
            # Campos opcionales
            population=data.get('population', 0),
            diameter=data.get('diameter')
        )
        db.session.add(new_planet)
        db.session.commit()
        return jsonify(new_planet.serialize()), 201
    
    else:  # GET
        planets = Planet.query.all()
        return jsonify([planet.serialize() for planet in planets]), 200

@app.route('/planets/<int:planet_id>', methods=['GET'])
def get_one_planet(planet_id):
    planet = Planet.query.get(planet_id)
    if not planet:
        raise APIException('Planet not found', status_code=404)
    return jsonify(planet.serialize()), 200

@app.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    if get_jwt_identity() != 1:  # Solo admin puede ver todos los usuarios
        raise APIException('Unauthorized', status_code=403)
    users = User.query.all()
    return jsonify([user.serialize() for user in users]), 200

@app.route('/users/favorites', methods=['GET'])
@jwt_required()
def get_user_favorites():
    current_user = get_jwt_identity()
    favorites = Favorite.query.filter_by(user_id=current_user).all()
    return jsonify([fav.serialize() for fav in favorites]), 200

@app.route('/favorite/planet/<int:planet_id>', methods=['POST'])
@jwt_required()
def add_favorite_planet(planet_id):
    current_user = get_jwt_identity()
    planet = Planet.query.get(planet_id)
    
    if not planet:
        raise APIException('Planet not found', status_code=404)
    
    existing_fav = Favorite.query.filter_by(user_id=current_user, planet_id=planet_id).first()
    if existing_fav:
        raise APIException('Planet already in favorites', status_code=400)
    
    new_fav = Favorite(user_id=current_user, planet_id=planet_id)
    db.session.add(new_fav)
    db.session.commit()
    
    return jsonify({"msg": "Planet added to favorites"}), 201

@app.route('/favorite/people/<int:people_id>', methods=['POST'])
@jwt_required()
def add_favorite_people(people_id):
    current_user = get_jwt_identity()
    person = People.query.get(people_id)
    
    if not person:
        raise APIException('Person not found', status_code=404)
    
    existing_fav = Favorite.query.filter_by(user_id=current_user, people_id=people_id).first()
    if existing_fav:
        raise APIException('Person already in favorites', status_code=400)
    
    new_fav = Favorite(user_id=current_user, people_id=people_id)
    db.session.add(new_fav)
    db.session.commit()
    
    return jsonify({"msg": "Person added to favorites"}), 201

@app.route('/favorite/planet/<int:planet_id>', methods=['DELETE'])
@jwt_required()
def delete_favorite_planet(planet_id):
    current_user = get_jwt_identity()
    fav = Favorite.query.filter_by(user_id=current_user, planet_id=planet_id).first()
    
    if not fav:
        raise APIException('Favorite not found', status_code=404)
    
    db.session.delete(fav)
    db.session.commit()
    return jsonify({"msg": "Planet removed from favorites"}), 200

@app.route('/favorite/people/<int:people_id>', methods=['DELETE'])
@jwt_required()
def delete_favorite_people(people_id):
    current_user = get_jwt_identity()
    fav = Favorite.query.filter_by(user_id=current_user, people_id=people_id).first()
    
    if not fav:
        raise APIException('Favorite not found', status_code=404)
    
    db.session.delete(fav)
    db.session.commit()
    return jsonify({"msg": "Person removed from favorites"}), 200



# ====== END ENDPOINTS ======

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
