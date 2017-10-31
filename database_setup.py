import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

class NC(Base):
    __tablename__= 'nintendo'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }

#class for Game list Database
class GameList(Base):
    __tablename__ = 'list'

    name = Column(String(80), nullable=False)
    maker = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(80), nullable=False) 
    price = Column(String(8))
    nintendo_id = Column(Integer, ForeignKey('nintendo.id'))
    nintendo = relationship(NC)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'maker': self.maker,
            'id': self.id,
            'description': self.description,
            'price': self.price,
        }


engine = create_engine('sqlite:///nintendolistwithusers.db')


Base.metadata.create_all(engine)