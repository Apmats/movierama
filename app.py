from flask import Blueprint, Flask, request, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from models import Base, Users, Movies, Views, Recommendations
import psycopg2
import time
import os
import csv
import re
import sys
import json
from engine import RecommendationEngine

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

DBUSER = 'admin'
DBPASS = '123123123'
DBHOST = 'localhost'
DBPORT = '5432'
DBNAME = 'movieramadb'

last_processed_view_id = 0
local_users_offset = 1000000

@main.route("/users/<int:user_id>/recommendations", methods = ["GET"])
def get_recommendations(user_id):
    rec_movies = db.session.query(Recommendations).join(Recommendations.movie).filter(Recommendations.user_id == user_id).all()
    result = list(map(lambda rm: (('movie_id', rm.movie_id), ('expected_rating', rm.rating),('movie_id', rm.movie.id),  ('title', rm.movie.title), ('description', rm.movie.description), ('year', rm.movie.year)), rec_movies))
    return Response(json.dumps(result), status= 200, mimetype=u'application/json')
 
@main.route("/users/<int:user_id>/views/<int:movie_id>", methods = ["POST"])
def add_view(user_id, movie_id):
    content = request.get_json()
    rating = float(content['rating'])
    if (rating > 5 or rating < 0):
        return Response(json.dumps({'success':False, 'reason':'Rating outside of 0 to 5 range'}), status= 400, mimetype=u'application/json')
    new_view = Views(user_id=user_id, movie_id=movie_id, rating=rating)
    Session = sessionmaker(bind=db.engine)
    session = Session()
    session.add(new_view)
    session.commit()
    session.refresh(new_view)
    session.close()
    
    return Response(json.dumps({'success':True}), status= 200, mimetype=u'application/json')

@main.route("/users/<int:user_id>/views", methods = ["GET"])
def get_views(user_id):
    Session = sessionmaker(bind=db.engine)
    session = Session()
    movie_views = session.query(Views).join(Views.movie).filter(Views.user_id == user_id).all()
    result = list(map(lambda mv: (('movie_id', mv.movie.id),  ('title', mv.movie.title), ('description', mv.movie.description), ('year', mv.movie.year),  ('rating', mv.rating)), movie_views))
    session.close()

    return Response(json.dumps(result), status= 200, mimetype=u'application/json')

@main.route("/users/create", methods = ["GET"])
def create_user():
    new_user = Users()
    Session = sessionmaker(bind=db.engine)
    session = Session()
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    session.close()

    return Response(json.dumps({'success': True, 'user_id': new_user.id}), status= 200, mimetype=u'application/json')

 
def create_app(spark_context, dataset_path):    
    app = Flask(__name__)
    app.register_blueprint(main)
    app.config['SQLALCHEMY_DATABASE_URI'] = \
    'postgresql://{user}:{passwd}@{host}:{port}/{db}'.format(
        user=DBUSER,
        passwd=DBPASS,
        host=DBHOST,
        port=DBPORT,
        db=DBNAME)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = '123123123'
    global db
    db = SQLAlchemy(app)
    Base.metadata.create_all(bind=db.engine)
    
    global recommendation_engine 
    recommendation_engine = RecommendationEngine(spark_context, dataset_path)    

    return app

def init_movie_table(dataset_path):
    Session = sessionmaker(bind=db.engine)
    session = Session()
    if session.query(Movies).first():
        logger.info("Movie table has entries, skipping population")
        session.close()
        return
    movies_file_path = os.path.join(dataset_path, 'movies.csv')
    with open(movies_file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        Session = sessionmaker(bind=db.engine)
        session = Session()
        for row in reader:
            title_with_year = row['title']
            iter = re.finditer(' \([0123456789]{4}\)', title_with_year)
            try:
                *_, last_occurence = iter
                year = int(last_occurence.group()[2:6])
                title = title_with_year[:last_occurence.start()]
                new_movie = Movies(id=int(row['movieId']),description=row['genres'], title=title, year=year)
                session.add(new_movie)
                logger.info("Inserted movie with title " + title + " into db")
            except:
                pass
        session.commit()
        session.close()

def retrain():
    global last_processed_view_id

    Session = sessionmaker(bind=db.engine)
    session = Session()
    users = session.query(Users).all()
    views = session.query(Views).filter(Views.id > last_processed_view_id).order_by(Views.id.asc()).all()
    session.close()

    ratings = map(lambda view: (view.user_id + local_users_offset,view.movie_id, view.rating), views)
    recommendation_engine.add_ratings(ratings)
    for user in users:
        recommendations = recommendation_engine.get_top_ratings(user.id + local_users_offset, 10)
        Session = sessionmaker(bind=db.engine)
        session = Session()
        session.query(Users).all()
        session.query(Recommendations).filter(Recommendations.user_id == user.id).delete(synchronize_session='evaluate')
        for recommendation in recommendations:
            new_recommendation = Recommendations(user_id=user.id, movie_id=recommendation[0], rating=recommendation[2])
            session.add(new_recommendation)
        session.commit()
        session.close()
    if views:
        last_processed_view_id = views[-1].id
    logger.info("Training done up to view with id " + str(last_processed_view_id) + " and will resume from there next training")

    return
