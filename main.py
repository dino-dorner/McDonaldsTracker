from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from flask_sqlalchemy import SQLAlchemy

from geoalchemy2 import Geometry, WKTElement, Geography
from geoalchemy2.functions import ST_DWithin
from geoalchemy2.shape import to_shape

from flask_migrate import Migrate
import csv

app = Flask(__name__)
app.secret_key = "your_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:password!@localhost:5432/mcdonalds"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_ECHO'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

visited_McDonalds = db.Table('visited_McDonalds', db.Column('user_id', db.Integer, db.ForeignKey('User.id')), db.Column('McDLocations', db.Integer, db.ForeignKey('McDonaldsLocations.id')))

class User(db.Model):

    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable = False)
    visited = db.relationship('McDonaldsLocations', lazy="dynamic", secondary = visited_McDonalds, backref = 'visitors')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class McDonaldsLocations(db.Model):

    __tablename__ = 'McDonaldsLocations'
    id = db.Column(db.Integer, primary_key = True)
    address = db.Column(db.String(100), nullable = False)
    geom = db.Column(Geography('POINT', srid=4326))


@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for('dashboard'))
    return render_template("login.html")



@app.route("/login", methods=["POST"])
def login():
    username = request.form['username']
    password = request.form["password"]

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['username'] = username
        return redirect(url_for('dashboard'))
    else:
        return render_template("login.html", error = "Incorrect Username or Password")
    


@app.route("/register", methods=["POST"])
def register():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if user:
        return render_template("login.html", error="Username already taken.")
    elif len(password) < 10:
        return render_template("login.html", error = "Password is less than 10 letters long!")
    else:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = username
        return redirect(url_for('dashboard'))


@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))




@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return render_template("dashboard.html", username=session['username'], arr = getMcDonalds())
    return redirect(url_for('home'))




@app.route("/getMcDonalds", methods=["GET"])
def getMcDonalds():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'User not logged in'}), 401
    
    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify({'error': 'No user logged in'}), 401
    
    userLocations = user.visited.all()
    arr = []
    for i in range(len(userLocations)):
        point = to_shape(userLocations[i].geom)
        arr.append([userLocations[i].address, point.x, point.y, userLocations[i].id])
    return jsonify(my_array=arr)




@app.route("/addMcDonaldsScroll", methods = ["GET"])
def addMcDonaldsScroll():
    latitude = float(request.args.get('latitude'))
    longitude = float(request.args.get('longitude'))

    search_point = WKTElement('POINT(' + str(longitude) + ' ' + str(latitude) + ')', srid = 4326)

    locate = McDonaldsLocations.query.filter(ST_DWithin(McDonaldsLocations.geom, search_point, 5000)).all()

    arr = [[loc.address, loc.id] for loc in locate]
    print(arr)
    bleh = jsonify(arr).data
    return bleh
        

@app.route("/addAllLocations", methods = ["GET"])
def addAllLocations():
    locations = McDonaldsLocations.query.all()
    arr = [[to_shape(loc.geom).x, to_shape(loc.geom).y, loc.id] for loc in locations]
    bleh = jsonify(arr).data
    return bleh


@app.route("/AddorDeleteMcDonaldsLocal", methods= ["POST"])
def AddorDeleteMcDonaldsLocal():
    id = request.json['id']
    print(request.json)

    user = User.query.filter_by(username=session.get('username')).first()
    locale = McDonaldsLocations.query.filter_by(id=id).first()

    if user.visited.filter_by(id=locale.id).first():
        user.visited.remove(locale)
    else:
        user.visited.append(locale)

    db.session.commit()
    return jsonify({'message' : 'done'})

if __name__ in "__main__":
    app.run(debug=True)