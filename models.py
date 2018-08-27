from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship

Base = declarative_base()

class Users(Base):
    __tablename__ = 'Users'

    id = Column(Integer, primary_key=True)

    def __repr__(self):
        return '<User {}>'.format(self.id)


class Movies(Base):
    __tablename__ = 'Movies'

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    description = Column(Text())
    year = Column(Integer)

    def __repr__(self):
        return '<Movie {}>'.format(self.id)

class Views(Base):
    __tablename__ = 'Views'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('Users.id'),
        nullable=False)
    movie_id = Column(Integer, ForeignKey('Movies.id'),
        nullable=False)
    rating = Column(Float)
    __table_args__ = (UniqueConstraint('user_id', 'movie_id', name='unique_rating_per_movie_user_pair'),)

    movie = relationship("Movies", foreign_keys=[movie_id])
    user = relationship("Users", foreign_keys=[user_id])
    def __repr__(self):
        return '<View {} for user {} and movie {} with rating{}>'.format(self.id, self.user_id, self.movie_id, self.rating)


class Recommendations(Base):
    __tablename__ = 'Recommendations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('Users.id'),
        nullable=False)
    movie_id = Column(Integer, ForeignKey('Movies.id'),
        nullable=False)
    rating = Column(Float)
    __table_args__ = (UniqueConstraint('user_id', 'movie_id', name='unique_recommendation_per_movie_user_pair'),)
    movie = relationship("Movies", foreign_keys=[movie_id])
    user = relationship("Users", foreign_keys=[user_id])
    def __repr__(self):
        return '<Recommendation {} for user {} and movie {}>'.format(self.id, self.user_id, self.movie_id)
