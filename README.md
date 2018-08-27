We've been asked to develop a small web app that handles movie recommendations based on user preferences.

We have access to the Movielens datasets so a very viable approach is to handle recommendations via CF. A very popular way to implement CF these days, AFAIK, is through matrix factorization, frequently through the ALS algorithm.
Spark is frequently used for this purpose, as it features a state of the art implementation of that algorithm.

Because, again, this is a widely encountered use case, there are a lot of examples of implementations based on the above.

Very conveniently, there's already a project/tutorial that guides us through implementing ALS in python using Spark. The project is located here: https://github.com/jadianes/spark-movie-lens/ and apart from the source code, there are also a couple of interesting notebooks that explain the basics of CF, how to build a recommender engine based on Spark's ALS implementation etc. The part about training and discovering the optimal parameters (such as the latent factors/matrix dimensions) for the actual use of the ALS algorithm is particularly interesting. 

Since this is a toy problem, we will simply build upon that project.

The base project is built upon CherryPy, Flask and as mentioned Spark, written obviously in Python. However, it features no persistence at all. We want to get closer to being production ready, even for a toy example, so we add a (dockerized) deployment of Postgresql to persist our data and generated recommendations.

All the work was done in Python 3.7, so make sure to use at least a 3.x version when trying to set this project up.

Install the requirements by running (perhaps under a virtual env)

```bash
pip install -r requirements.txt
```

Then also manually install all the requirements I've undoubtedly missed.

Run the script that downloads the Movielens dataset, provided in the original project:

```bash
./download_dataset.sh
```

Provided docker is already setup, you should be able to run
```bash
docker-compose up -d --build

```
to spin up a container running psql. The included .env file that gets used contains the username and password that is also used on the Python side to connect to the database.


Set up Spark locally, or as a cluster. I didn't get a chance to containerize/automate the rest of the deployment so this is a bit of manual work.
Myself I used a local installation of Spark 2.3.1. My local path to the spark-submit binary for example ended up being:

```path
/usr/local/spark-2.3.1-bin-hadoop2.7/bin/spark-submit
```
Update the start_server.sh script accordingly, with your local path or your remote url, and according to the resources you have available.


You should be ready to run the server start script now:

```bash
./start_server.sh
```

Now, the following end points are accessible:

a) http://localhost:5430/users/create where a simple GET creates a new user, and returns you an ID for that user. You can then subsequently use that ID to capture their preferences and get recommendations for them.
You get back something like this:

```json
{"success": true, "user_id": 1}
```

b) http://localhost:5430/users/{userId}/views where a GET gets you the previous behavior of the user specified by the ID. The response looks like this:


```json
[[["movie_id", 25904], ["title", "Ministry of Fear"], ["description", "Drama|Film-Noir|Thriller"], ["year", 1944], ["rating", 4.5]], [["movie_id", 25903], ["title", "Mask of Dimitrios, The"], ["description", "Crime|Drama|Film-Noir|Mystery"], ["year", 1944], ["rating", 4.5]]]

```
c) http://localhost:5430/users/{userId}/views/{movieId} where you need to POST an additional parameter "rating". An example file is included, you can post it as follows:

```bash
curl --data-binary @view.json http://localhost:5430/users/1/views/25905 -H "Content-Type: application/json"
```

and this captures that the user with that ID saw the movie with the other provided ID (this is the internal Movielens ID mind you, not an external database reference).

d) http://localhost:5430/users/{userId}/recommendations where a simple GET gets you 10 recommended movies for the user specified by the ID. A response looks like this:

```json
[[["movie_id", 86237], ["expected_rating", 5.58396177012906], ["movie_id", 86237], ["title", "Connections"], ["description", "Documentary"], ["year", 1978]], [["movie_id", 165069], ["expected_rating", 5.18385224218535], ["movie_id", 165069], ["title", "Baseball"], ["description", "Documentary"], ["year", 1994]], [["movie_id", 134849], ["expected_rating", 5.15729392105471], ["movie_id", 134849], ["title", "Duck Amuck"], ["description", "Animation|Children|Comedy"], ["year", 1953]], [["movie_id", 26082], ["expected_rating", 5.133645504377], ["movie_id", 26082], ["title", "Harakiri (Seppuku)"], ["description", "Drama"], ["year", 1962]], [["movie_id", 64241], ["expected_rating", 5.13330119611914], ["movie_id", 64241], ["title", "Lonely Wife, The (Charulata)"], ["description", "Drama|Romance"], ["year", 1964]], [["movie_id", 26109], ["expected_rating", 5.10960371753984], ["movie_id", 26109], ["title", "Crooks in Clover (a.k.a. Monsieur Gangster) (Les tontons flingueurs)"], ["description", "Action|Comedy|Crime"], ["year", 1963]], [["movie_id", 82143], ["expected_rating", 5.09552358458852], ["movie_id", 82143], ["title", "Alone in the Wilderness"], ["description", "Documentary"], ["year", 2004]], [["movie_id", 159817], ["expected_rating", 5.09314152094635], ["movie_id", 159817], ["title", "Planet Earth"], ["description", "Documentary"], ["year", 2006]], [["movie_id", 3739], ["expected_rating", 5.08522735111204], ["movie_id", 3739], ["title", "Trouble in Paradise"], ["description", "Comedy|Romance"], ["year", 1932]], [["movie_id", 25975], ["expected_rating", 5.07998912787381], ["movie_id", 25975], ["title", "Life of Oharu, The (Saikaku ichidai onna)"], ["description", "Drama"], ["year", 1952]]]
```







Quick rundown of the app:

See the revelant notebooks from the original project, these do a much better job of explaining both the recommender as well as the web server setup. In order to achieve the outlined functionality for the assignment, we had to do the following additional work:

a) Setup a database, and create the appropriate models. Since we don't have a great idea of the performance requirements of this system, a relational database is a good place to start. We pick the battletested Postgresql DB and we can investigate in the far, far future if we need to move to NoSQL to scale.
The models and thus the tables are found under the models.py file. Basically, we maintain a table for Users, a table for Movies, a table for Views/Ratings and a table for generated Recommendations.

b) Add some provisions to ingest the movie dataset into the database. This happens once upon application startup, if the movie table is found empty. This happens under the init_movie_table method under the app.py file. The only tricky part was extracting the year from the title string, where we simply pick the last occurence of a 4 digit number contained within parenthesis from said string.

c) Change the routes to serve the requests we need. These routes are defined under app.py and cover the previously mentioned functionality. Unfortunately, the validation is minimal but it could be made more robust without significant effort.

d) Change the app to, instead of retraining upon request, to handle captured interactions in batches. This is handled under server.py and app.py. The basic idea is the following. Every X minutes (currently hard coded to 12 under server.py but subject to change depending to our actual load and resources) we trigger a scheduled task, that calls the retrain method found under app.py. The retrain method basically keeps track of up to where in the Views table we've already processed into our model, and when called retrieves DB rows from there onwards and submits them for addition to the recommendation engine.
Because this offset isn't persisted anywhere, and neither is anything else related to this, an application restart means that we will have to not only retrain with the initial data, but also trigger a retraining with all the recorded interactions.
This could be a good place to do some work down the road as this mechanism isn't too robust.

e) Since we're not training on the fly on each recorded interaction/rating, we generate the top 10 recommendations for each user and save them in a database table. This means that at some point, the training process can also happen offline, apart from the rest of our system. 
For this part, we also had to slightly modify the recommender implementation of the original project, since we want to get back User ID - Movie ID - Rating tuples and not just a title to show the user as originally done. 
Furthermore, in order to avoid collisions between the Movieles user IDs and our own internal ones (which refer to different sets of users) we add an offset of 1 million to our internal user ID before mixing them up with the Movielens IDs. Small thing but mentioned here as it might be a bit puzzling if encountered in the code.








Drawbacks of current implementatin:


We haven't investigated the best strategy to handle cold starts (ie. new user, gets no recommendations). We generally will need a fallback strategy to handle such cases. One such fallback could be to suggest the universally most popular films to a user with little or no preferences.

We haven't investigated the real constraints of our system. Perhaps recommendations need to happen in real time, and an algorithm that dictates that frequent retrainings need to happen might not be the best choice here.

System restarts are painful, as the entire model needs to be retrained. Perhaps we need a strategy to persist RDDs or the entirety of the generated matrixes.