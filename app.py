from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import requests
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import x
import time
import uuid
import os
import io
import csv
import json
from datetime import datetime
from api_actions import api_actions

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

UPLOAD_FOLDER = 'static/images/user_uploads/avatars'

app = Flask(__name__)
app.register_blueprint(api_actions)

# Set the maximum file size to 10 MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

##############################
# Files that will be loaded in each template 
@app.context_processor
def global_variables():
    return dict (
        x = x
    )

# Generated with chatGPT
@app.template_filter("timeago")
def timeago(timestamp):
    now = datetime.now()
    dt = datetime.fromtimestamp(timestamp)
    diff = now - dt

    seconds = diff.total_seconds()
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    weeks = days // 7
    months = days // 30
    years = days // 365

    if seconds < 60:
        return f"{x.lans('time_moments')}"
    elif minutes < 60:
        return f"{int(minutes)} {x.lans('time_minute')}{x.lans('time_plural_suffix') if minutes > 1 else ''}"
    elif hours < 24:
        return f"{int(hours)} {x.lans('time_hour')}{x.lans('time_plural_suffix') if hours > 1 else ''}"
    elif days < 7:
        return f"{int(days)} {x.lans('time_day')}{x.lans('time_plural_suffix') if days > 1 else ''}"
    elif weeks < 4:
        return f"{int(weeks)} {x.lans('time_week')}{x.lans('time_plural_suffix') if weeks > 1 else ''}"
    elif months < 12:
        return f"{int(months)} {x.lans('time_month')}{x.lans('time_plural_suffix') if months > 1 else ''}"
    else:
        return f"{int(years)} {x.lans('time_year')}{x.lans('time_plural_suffix') if years > 1 else ''}"


##############################
##############################
##############################
def _____USER_____(): pass 
##############################
##############################
##############################

@app.get("/")
@app.route("/<lang>", methods=["GET", "POST"])
def view_index(lang = "en"):
    # Set language
    x.default_language = lang

    return render_template("index.html", lang=lang)

##############################
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<lang>", methods=["GET", "POST"])
@x.no_cache
def view_login( lang = "en"):
    x.default_language = lang

    if request.method == "GET":
        if session.get("user", ""): return redirect(url_for("view_browse"))
        return render_template("login.html", lang=lang)
    

##############################
@app.route("/index-pass-email", methods=["POST"])
@app.route("/index-pass-email/<lang>", methods=["POST"])
def index_signup(lang ="en"):
    try:
        x.default_language = lang
        email = request.form.get("user_email")

        return redirect( url_for('view_signup', email=email, lang=lang))
    except Exception as ex:
        ic(ex)
    finally:
        pass

##############################
@app.route("/signup", methods=["GET"])
@app.route("/signup/<lang>", methods=["GET"])
@x.no_cache
def view_signup(lang = "en"):
    x.default_language = lang

    user_email = request.args.get("email", "")
    return render_template("signup.html", user_email=user_email, lang=lang)

    ##############################
@app.route("/browse")
@x.no_cache
def view_browse():
    try:
        user = session.get("user", "")
        if not user: 
            return redirect(url_for("view_index"))
        
        user_pk = user.get("user_pk", "")
        # set page language
        lang = user.get("user_language", "en")

        db, cursor = x.db()

        headers = {"Authorization": f"Bearer {TMDB_API_KEY}"}

        ### POPULAR
        url_movies_popular = f"https://api.themoviedb.org/3/movie/popular?language=en-US&page=1"
        response = requests.get(url_movies_popular, headers=headers)
        data = response.json()
        # [:9] means how many will be stored in the variable
        movies_popular = data.get("results", [])[:9]

        ### COMEDY
        url_movies_comedy = f"https://api.themoviedb.org/3/discover/movie?language=en-US&sort_by=popularity.desc&with_genres=35&page=2"
        response_comedy = requests.get(url_movies_comedy, headers=headers)
        data_comedy = response_comedy.json()
        movies_comedy = data_comedy.get("results", [])[:9]

        ### ROMANCE
        url_movies_romance = f"https://api.themoviedb.org/3/discover/movie?language=en-US&sort_by=popularity.desc&with_genres=10749&page=1"
        response_romance = requests.get(url_movies_romance, headers=headers)
        data_romance = response_romance.json()
        movies_romance = data_romance.get("results", [])[:9]

        # ChatGPT helped
        ### Fetch all genres for name mapping
        url_movies_genres = "https://api.themoviedb.org/3/genre/movie/list?language=en-US"
        response_genres = requests.get(url_movies_genres, headers=headers)
        genres_data = response_genres.json()

        #create genre mapping dict
        genre_mapping = {g["id"]: g["name"] for g in genres_data["genres"]}

        # Attach genre names to movie categories
        for movie_list in [movies_popular, movies_comedy, movies_romance]:
            for movie in movie_list:
                # replace genre id's with the genre names
                movie["genres"] = [
                    genre_mapping.get(gid, "Unknown")
                    for gid in movie.get("genre_ids", [])
                ]

        return render_template("browse.html", user=user, movies_popular=movies_popular, movies_comedy=movies_comedy, movies_romance=movies_romance, lang=lang)
    except Exception as ex:
        ic(ex)
        return f"error {ex}"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################## 
@app.route("/movie", methods=["GET"])
@x.no_cache
def view_movie():
    try:
        user = session.get("user", "")
        if not user: 
            return redirect(url_for("view_index"))
        
        user_pk = user.get("user_pk")
        movie_id = request.args.get("movie_id")

        #Fallback
        if not movie_id:
            return redirect(url_for("view_browse"))
        
        #Get specific movie details
        headers = {"Authorization": f"Bearer {TMDB_API_KEY}"}
        url_movie = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"
        response = requests.get(url_movie, headers=headers)
        data = response.json()
        lang = user.get("user_language", "en")
    
        # Connect to the database
        db, cursor = x.db()
        q = """
        SELECT 
        reviews.review_pk,
        reviews.review_user_fk,
        reviews.review_text,
        reviews.review_created_at,
        users.user_first_name,
        users.user_avatar_path,
        users.user_verified_at
        FROM reviews
        JOIN users 
        ON users.user_pk = reviews.review_user_fk
        LEFT JOIN blocks
        ON (
        (blocks.block_blocker_user_fk = %s AND blocks.block_blocking_user_fk = reviews.review_user_fk)
        OR
        (blocks.block_blocker_user_fk = reviews.review_user_fk AND blocks.block_blocking_user_fk = %s)
        )
        WHERE 
        reviews.review_movie_id = %s
        AND reviews.review_deleted_at = 0
        AND users.user_deleted_at = 0
        AND blocks.block_blocker_user_fk IS NULL
        ORDER BY reviews.review_created_at DESC
        LIMIT 5;
        """
        
        cursor.execute(q, (user_pk, user_pk, movie_id))
        reviews = cursor.fetchall()

        #check if the user has liked the movie
        q = "SELECT * FROM mylists WHERE mylist_user_fk = %s AND mylist_movie_id = %s"
        cursor.execute(q, (user_pk, movie_id,))
        mylist_existing_row = cursor.fetchone()

        #display the correct button in each case
        has_user_liked = False
        if mylist_existing_row and mylist_existing_row.get("mylist_deleted_at") == 0:
            has_user_liked = True

        q = """
        SELECT
        comments.comment_pk,
        comments.comment_review_fk,
        comments.comment_user_fk,
        comments.comment_text,
        comments.comment_created_at,

        users.user_first_name,
        users.user_avatar_path,
        users.user_verified_at

        FROM comments
        JOIN users
        ON users.user_pk = comments.comment_user_fk

        LEFT JOIN blocks
        ON (
        (blocks.block_blocker_user_fk = %s AND blocks.block_blocking_user_fk = comments.comment_user_fk)
        OR
        (blocks.block_blocker_user_fk = comments.comment_user_fk AND blocks.block_blocking_user_fk = %s)
        )

        WHERE
        comments.comment_deleted_at = 0
        AND users.user_deleted_at = 0
        AND blocks.block_blocker_user_fk IS NULL

        ORDER BY comments.comment_created_at DESC;
        """
        cursor.execute(q, (user_pk, user_pk))
        comments = cursor.fetchall()

        return render_template("movie.html", comments=comments, user=user, data=data, lang=lang, reviews=reviews, movie_id=movie_id, has_user_liked=has_user_liked)
    except Exception as ex:
        ic(ex)
        return "An error occured", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################## 
@app.route("/account")
@x.no_cache
def view_account():
    
    try:
        user = session.get("user", "")
        if not user: return redirect(url_for("view_index"))
        # lang = x.default_language
        lang = user.get("user_language", "en")

        #Get account data
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()

        #Get blocklist
        q = """
        SELECT users.user_pk, users.user_first_name 
        FROM blocks
        JOIN users 
        ON blocks.block_blocking_user_fk = users.user_pk
        WHERE blocks.block_blocker_user_fk = %s 
        """
        cursor.execute(q, (user["user_pk"],))
        blocked_users = cursor.fetchall()

        return render_template("account.html", user=user, lang=lang, blocked_users=blocked_users)
    
    except Exception as ex:
        ic(ex)
        return "An error occured", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################## I wanted this api to be in the api_actions file, but I cant get the validation for the upload file to work
@app.route("/api-update-account", methods=["POST"])
def api_update_account():

    try:
        user = session.get("user", "")
        if not user: return "invalid user"

        # Validate
        user_email = x.validate_user_email()
        user_first_name = x.validate_user_first_name()

        file = request.files.get('user_avatar_file_upload')
        file_path = None

        # Check if user has uploaded a file, then validate, got help from ChatGPT
        if file and x.validate_avatar_file(file.filename):
            filetype = os.path.splitext(file.filename)[1].lower()
            filename = f"{uuid.uuid4().hex}{filetype}"

            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # Save the relative path (NO 'static/' prefix)
            file_path = os.path.join('images/user_uploads/avatars', filename)

        # Connect to the database
        db, cursor = x.db()
        if file_path:
            q = "UPDATE users SET user_email = %s, user_first_name = %s, user_avatar_path = %s WHERE user_pk = %s"
            cursor.execute(q, (user_email, user_first_name, file_path, user["user_pk"]))
        else:
            q = "UPDATE users SET user_email = %s, user_first_name = %s WHERE user_pk = %s"
            cursor.execute(q, (user_email, user_first_name, user["user_pk"]))
        db.commit()

        # Response to the browser
        label_ok = render_template("components/toast/___label_ok.html", message=x.lans("feedback_success_account_updated"))
        return f"""
        <browser mix-update="#error_container">{label_ok}</browser>
        <browser mix-update="#header-profile-icon">
            <img class="profile-icon"
                    src="static/{file_path}"
                    alt="Profile">
        </browser>
        <browser mix-update="#account-profile-icon">
            <img src="static/{file_path}"
                alt="Profile picture" class="img rounded-md aspect-ratio:1/1">
        </browser>
        <browser mix-update="#account-header">{x.lans("account_header_1")} {user_first_name}</browser>
        """, 200
    
    except Exception as ex:
        ic(ex)
        
        # User errors
        if ex.args[1] == 400:
            label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#error_container">{ label_error }</mixhtml>""", 400
        
        # Database errors
        if "Duplicate entry" and user_email in str(ex): 
            label_error = render_template("components/toast/___label_error.html", message=x.lans("feedback_email_already_registered"))
            return f"""<mixhtml mix-update="#error_container">{ label_error }</mixhtml>""", 400
        
        # System or developer error
        label_error = render_template("components/toast/___label_error.html", message=x.lans("feedback_system_maintenance"))
        return f"""<mixhtml mix-bottom="#error_container">{ label_error }</mixhtml>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################## 
@app.route("/admin")
def view_admin():
    try:
        user = session.get("admin_session", "")
        if not user: 
            return redirect(url_for("view_admin_login"))
        # Connect to the database
        db, cursor = x.db()
        #Active uses in database
        q = "SELECT * FROM users WHERE user_deleted_at = '0'" 
        cursor.execute(q)
        active_users = cursor.fetchall()

         #Inactive uses in database
        q = "SELECT * FROM users WHERE user_deleted_at != '0'"
        cursor.execute(q)
        deleted_users = cursor.fetchall()

        #reviews
        q = "SELECT * FROM reviews"
        cursor.execute(q)
        reviews = cursor.fetchall()

        return render_template("admin.html", active_users=active_users, deleted_users=deleted_users, reviews=reviews)

    except Exception as ex:
        ic(ex)
        return f"An error occured {ex}", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################## 
@app.route("/admin-login", methods=["GET", "POST"])
@x.no_cache
def view_admin_login():

    if request.method == "GET":
        if session.get("admin_session", ""): return render_template("admin.html")
        return render_template("adminlogin.html")

    if request.method == "POST":
        try:
            # Validate           
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            
            # HArdcoded for demonstration purposes 
            admin_email = "admin@email.com"
            admin_password = "password"

            if not user_email:
                raise Exception("Please enter a valid email", 400)

            if user_email != admin_email or user_password != admin_password:
                raise Exception ("Invalid credentials", 400)
            
            session["admin_session"] = True

            return f"""<browser mix-redirect="/admin"></browser>"""

        except Exception as ex:
            ic(ex)
            # User errors
            if ex.args[1] == 400:
                label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
                ic("An error occured in Email")
                return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 400
            
            # System or developer error
            label_error = render_template("components/toast/___label_error.html", message=x.lans("feedback_system_maintenance"))
            return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 500
    
        finally:
            pass


#################
@app.patch("/api-like-movie/<movie_id>")
def api_like_movie(movie_id):
    try:
        user = session.get("user")
        user_pk = user.get("user_pk")
        if not user_pk:
            return "No user id in session", 500

        db, cursor = x.db()
        q = "SELECT * FROM mylists WHERE mylist_user_fk = %s AND mylist_movie_id = %s"
        cursor.execute(q, (user_pk, movie_id))
        existing_row = cursor.fetchone()

        if existing_row:
            if existing_row["mylist_deleted_at"] == 0:
                # Unlike
                mylist_deleted_at = int(time.time())
                q = "UPDATE mylists SET mylist_deleted_at = %s WHERE mylist_user_fk = %s AND mylist_movie_id = %s"
                cursor.execute(q, (mylist_deleted_at, user_pk, movie_id))
                db.commit()
                has_user_liked = False
                button_html = render_template("components/___add_mylist_btn.html", movie_id=movie_id)
            else:
                # Re-like
                mylist_deleted_at = 0
                q = "UPDATE mylists SET mylist_deleted_at = %s WHERE mylist_user_fk = %s AND mylist_movie_id = %s"
                cursor.execute(q, (mylist_deleted_at, user_pk, movie_id))
                db.commit()
                has_user_liked = True
                button_html = render_template("components/___remove_mylist_btn.html", movie_id=movie_id)
        else:
            # Create like
            mylist_created_at = int(time.time())
            mylist_deleted_at = 0
            q = "INSERT INTO mylists VALUES (%s, %s, %s, %s)"
            cursor.execute(q, (user_pk, movie_id, mylist_created_at, mylist_deleted_at))
            db.commit()
            has_user_liked = True

        button_html = render_template("components/___mylist_container.html", movie_id=movie_id, has_user_liked=has_user_liked)

        return f"<browser mix-replace='#mylist_btn_container'>{button_html}</browser>"

    except Exception as ex:
        ic(ex)
        return "Error, could not like", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

####################### 
@app.route("/my-list")
@x.no_cache
def view_mylist():
    try:
        user = session.get("user", "")
        if not user: 
            return redirect(url_for("view_index"))

        user_pk = user.get("user_pk", "")
        lang = user.get("user_language", "en")

        db, cursor = x.db()
        q = "SELECT mylist_movie_id FROM mylists WHERE mylist_user_fk = %s AND mylist_deleted_at = 0"
        cursor.execute(q, (user_pk,))
        rows = cursor.fetchall()

        # Get all movie_ids from all matching rows
        movie_ids = [row["mylist_movie_id"] for row in rows]  

        movie_list = []

        # Fetch movie details from TMDB for each ID
        for movie_id in movie_ids:
            headers = {"Authorization": f"Bearer {TMDB_API_KEY}"}
            url_movie = f"https://api.themoviedb.org/3/movie/{movie_id}?language={lang}"
            response = requests.get(url_movie, headers=headers)
            if response.status_code == 200:
                #if fetch went correctly, add the fetched movies to the empty dict
                movie_list.append(response.json())
            if response.status_code != 200:
                return "Fetching failed"
            
        return render_template("mylist.html", user=user, lang=lang, movie_list=movie_list)

    except Exception as ex:
        ic(ex)
        return "System under maintenance"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


####################### 
@app.get("/api-update-dictionary")
def get_data_from_sheet():
    try:
        # Create a google sheet
        # share and make it visible to "anyone with the link"
        # In the link, find the ID of the sheet. Here: 1aPqzumjNp0BwvKuYPBZwel88UO-OC_c9AEMFVsCw1qU
        # Replace the ID in the 2 places bellow
        url= f"https://docs.google.com/spreadsheets/d/{x.google_spread_sheet_key}/export?format=csv&id={x.google_spread_sheet_key}"
        res=requests.get(url=url)
        # ic(res.text) # contains the csv text structure
        csv_text = res.content.decode('utf-8')
        csv_file = io.StringIO(csv_text) # Use StringIO to treat the string as a file
        # Initialize an empty list to store the data
        data = {}
        # Read the CSV data
        reader = csv.DictReader(csv_file)
        ic(reader)
        # Convert each row into the desired structure
        for row in reader:
            item = {
                    'en': row['english'],
                    'nl': row['dutch'],
                    'es': row['spanish']
            }
            # Append the dictionary to the list
            data[row['key']] = (item)
        # Convert the data to JSON
        json_data = json.dumps(data, ensure_ascii=False, indent=4)
        # ic(data)
        # Save data to the file
        with open("dictionary.json", 'w', encoding='utf-8') as f:
            f.write(json_data)
        return "ok"
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        pass

###############
@app.route("/update-user-language", methods=["GET"])
def update_user_language():
    # get selected language from form
    chosen_language = request.args.get("language_selector")

    # Update the user's session
    if "user" in session:
        user = session["user"]
        user["user_language"] = chosen_language
        session["user"] = user

    # Update translation engine language
    x.default_language = chosen_language

    # Redirect back to the page the user was
    return redirect(request.headers.get("Referer", "/"))

@app.get("/update-website-language")
def update_website_language():
    lang = request.args.get("language_selector", "en")

    # Get the referring URL
    referer = request.headers.get("Referer", "/")

    # Split into path and query
    if "?" in referer:
        path, query = referer.split("?", 1)
        query = "?" + query  # keep the ? for later
    else:
        path, query = referer, ""

    # Split the path into parts
    path_parts = path.rstrip("/").split("/")

    # Replace last part if it's a language code, else append
    if path_parts[-1] in ["en", "nl", "es"]:
        path_parts[-1] = lang
    else:
        path_parts.append(lang)

    # Rebuild the new path
    new_path = "/".join(path_parts)

    # Combine new path with original query
    new_url = new_path + query

    return redirect(new_url)

##########
@app.route("/forgot-password", methods=["GET", "POST"])
@app.route("/forgot-password/<lang>", methods=["GET", "POST"])
def view_forgot_password(lang = "en"):
    x.default_language = lang

    return render_template("forgotpassword.html", lang=lang)

##############
@app.route("/new-password", methods=["GET", "POST"])
@app.route("/new-password/<lang>", methods=["GET", "POST"])
def view_new_password(lang = "en"):
    x.default_language = lang
    try: 
        # Get the key and find the user in the database
        user_new_password_key = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_new_password_key = %s"
        cursor.execute(q, (user_new_password_key,))
        user = cursor.fetchone()

        #Does the database return a matching key as in the url?
        if cursor.rowcount != 1: 
            # raise Exception("Invalid key", 400)
            return redirect(url_for("view_index", lang=lang))

        # If user doesnt have the key then redirect
        if not user:
            return redirect(url_for("view_index", lang=lang))
            # raise Exception("Invalid or expired reset link", 400)

        return render_template("newpassword.html", lang=lang)

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if ex.args[1] == 400:
            label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
            ic("An error occured in Email")
            return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 400

    
        # System or developer error
        return "An error occured", 500

    finally: 
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
