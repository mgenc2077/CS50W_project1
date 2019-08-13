import os
import json
import requests
from flask import Flask, session, render_template, request, redirect, g, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import jsonify

global isbn
app = Flask(__name__, static_url_path='/static')
app.secret_key = os.urandom(24)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
db = db()

@app.route("/")
def index():
    if g.user:
        return render_template("index.html", g=g)
    else:
        return redirect(url_for("giris"))

#user kontrolü:        
@app.before_request
def before_request():
    g.user = None
    if 'user' in session:
        g.user = session['user']

@app.route("/form", methods=["GET", "POST"])
def form():
    global isbn
    if g.user:
        #Formdan verilerin toplanması:
        isbn = request.form.get("isbn")
        title = request.form.get("title")
        author = request.form.get("author")
        #Alınan verinin Databese üzerinde taranması:
        anlik = db.execute("SELECT * FROM books WHERE isbn = cast(:isbn as varchar)",{"isbn":isbn}).fetchone()
        ad = db.execute("SELECT * FROM books WHERE title = :title",{"title":title}).fetchone()
        yazar = db.execute("SELECT * FROM books WHERE author = :author",{"author":author}).fetchone()
        data = db.execute("SELECT rating, yorum FROM review WHERE isbn = cast(:isbn as varchar)",{"isbn":isbn}).fetchall()
        if db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).rowcount > 0 or db.execute("SELECT * FROM books WHERE title = :title",{"title":title}).rowcount > 0 or db.execute("SELECT * FROM books WHERE author = :author",{"author":author}).rowcount > 0:
            #test = "dolu"
            #Goodreads api kullanılarak inceleme alınması:
            if isbn == None:
                if ad != None:
                    isbn = ad.isbn
                elif yazar != None:
                    isbn = yazar.isbn
            response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "52j1xxeQBcRscR5fosPYLQ", "isbns": isbn})
            json_data = json.loads(response.text)
            x = json_data["books"]
            y = x[0]
            work_ratings_count = y['work_ratings_count']
            average_rating = y['average_rating']
            return render_template("isbn_ara.html", anlik=anlik, ad=ad, yazar=yazar, average_rating=average_rating, work_ratings_count=work_ratings_count, data=data, g=g)
        #Gelen veri boş ise hata mesajı:   
        else:
            return render_template("error.html", message="404-Kitap Bulunamadı", g=g)
            #test = "boş"
    else:
        redirect(url_for('giris'))
        
@app.route("/kayit", methods=["GET", "POST"])
def kayit():
    return render_template("kayit.html", g=g)

#kayıt işleminin SQL database'e yazılması:
@app.route("/success", methods=["POST"])
def success():
    email = request.form.get("email")
    password = request.form.get("password")
    db.execute("INSERT INTO users (email, password) VALUES (:email, :password)",{"email": email, "password": password})
    db.commit()
    return render_template("success.html", g=g)

    
@app.route("/giris", methods=["GET", "POST"])
def giris():
    return render_template("giris.html", g=g)

#email ve şifre kontrolü:
@app.route("/login", methods=["GET", "POST"])
def login():
    eid = request.form.get("eid")
    lpass = request.form.get("epass")
    if db.execute("SELECT email FROM users WHERE email = :eid", {"eid": eid}).rowcount > 0 and db.execute("SELECT password FROM users WHERE password = :password", {"password": lpass}).rowcount > 0:
        session['user'] = eid
        return render_template("login_success.html", g=g)
    else:
        return render_template("login_failed.html", g=g)

#Kullanıcı çıkışı:
@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session.pop('user', None)
    return render_template("logout_success.html", g=g)

#Alınan yorumların database'e işlenmesi:    
@app.route("/ratext", methods=["POST"])
def ratext():
    deger = request.form.get("deger")
    inc = request.form.get("inc")
    db.execute("INSERT INTO review(isbn, rating, yorum) VALUES(:isbn, :deger, :inc)",{"isbn": isbn, "deger": deger, "inc": inc})
    db.commit()
    return render_template("sent.html", g=g)

#isbn kullanımı ile sorgu api:
@app.route("/api/<string:isbn1>", methods=["GET", "POST"])
def api(isbn1):
    api_1 = db.execute("SELECT * FROM books WHERE isbn = cast(:isbn1 as varchar)",{"isbn1":isbn1}).fetchone()
    api_2 = dict(api_1)
    return jsonify(api_2)