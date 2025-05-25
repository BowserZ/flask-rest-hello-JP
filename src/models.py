from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Boolean, Integer, ForeignKey  # Añade Integer aquí
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()

class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "email": self.email,
            # do not serialize the password, its a security breach
        }

class People(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    height: Mapped[int] = mapped_column(Integer)
    mass: Mapped[int] = mapped_column(Integer)
    
    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "height": self.height,
            "mass": self.mass
        }

class Planet(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    climate: Mapped[str] = mapped_column(String(250))
    terrain: Mapped[str] = mapped_column(String(250))  # ¡Añade este campo!
    population: Mapped[int] = mapped_column(Integer, nullable=True)
    diameter: Mapped[int] = mapped_column(Integer, nullable=True)
    
    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "climate": self.climate,
            "population": self.population
        }

class Favorite(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user.id'))
    planet_id: Mapped[int] = mapped_column(ForeignKey('planet.id'), nullable=True)
    people_id: Mapped[int] = mapped_column(ForeignKey('people.id'), nullable=True)
    
    user: Mapped["User"] = relationship("User", backref="favorites")
    planet: Mapped["Planet"] = relationship("Planet")
    people: Mapped["People"] = relationship("People")
    
    def serialize(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "planet": self.planet.serialize() if self.planet else None,
            "people": self.people.serialize() if self.people else None
        }
