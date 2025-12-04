from flask import Flask, render_template, request, session, redirect, url_for
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

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

UPLOAD_FOLDER = 'static/images/user_uploads/avatars'

app = Flask(__name__)

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
    # # Default language
    # default_lang = "en"

    # # Check previous page
    # referer = request.headers.get("Referer", "")

    # if not lang:
    #     # Extract last segment of previous URL
    #     path = referer.split("?", 1)[0].rstrip("/")  # remove query string & trailing slash
    #     last_segment = path.split("/")[-1] if path else ""
    #     if last_segment in ["en", "nl", "es"]:
    #         lang = last_segment
    #     else:
    #         lang = default_lang

    # Set the translation engine
    x.default_language = lang

    return render_template("index.html", lang=lang)



##############################
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<lang>", methods=["GET", "POST"])
@x.no_cache
def login( lang = "en"):
    x.default_language = lang

    if request.method == "GET":
        if session.get("user", ""): return redirect(url_for("browse"))
        return render_template("login.html", lang=lang)

    if request.method == "POST":
        try:
            # Validate           
            user_email = x.validate_user_email(lang)
            user_password = x.validate_user_password(lang)

            # if not user_email:
            #     raise Exception("Please enter a valid email", 400)

            # Connect to the database
            q = "SELECT * FROM users WHERE user_email = %s"
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()

            if not user: 
                raise Exception("User not found, please check for spelling", 400)

            if not check_password_hash(user["user_password"], user_password):
                raise Exception("Invalid credentials", 400)

            if user["user_verification_key"] != "":
                raise Exception(x.lans("feedback_user_not_verified"), 400)
            
            user.pop("user_password")

            # Add the default language to the user
            user["user_language"] = lang
            session["user"] = user
        
            return f"""<browser mix-redirect="/browse"></browser>"""

        except Exception as ex:
            ic(ex)
            
            # User errors
            if ex.args[1] == 400:
                label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
                ic("An error occured in Email")
                return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 400
            
            # System or developer error
            toast_error = render_template("components/toast/___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

##############################
@app.post("/index-pass-email")
@app.post("/index-pass-email/<lang>")
def index_signup(lang ="en"):
        try:
            x.default_language = lang
            email = request.form.get("user_email")

            return redirect( url_for('signup', email=email, lang=lang))
        except Exception as ex:
            ic(ex)
        finally:
            pass

##############################
@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup/<lang>", methods=["GET", "POST"])
@x.no_cache
def signup(lang = "en"):
    x.default_language = lang
    if request.method == "GET":
        user_email = request.args.get("email", "")
        return render_template("signup.html", user_email=user_email, lang=lang)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            user_first_name = x.validate_user_first_name()

            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = "images/twitter_default.png"
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0
            user_deleted_at = 0

            user_hashed_password = generate_password_hash(user_password)

            # Connect to the database
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, 
            user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at, user_deleted_at))
            db.commit()

            # send verification email
            email_verify_account = render_template("components/email/_email_verify_account.html", user_verification_key=user_verification_key)
            ic(email_verify_account)
            x.send_email(user_email, "Verify your account", email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        except Exception as ex:
            ic(ex)
            # User errors
            if ex.args[1] == 400:
                label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
                return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 400
            
            # Database errors
            if "Duplicate entry" and user_email in str(ex): 
                label_error = render_template("components/toast/___label_error.html", message="Email already registered")
                return f"""<mixhtml mix-update="#error_container">{ label_error }</mixhtml>""", 400
            
            # System or developer error 
            label_error = render_template("components/toast/___label_error.html", message="System under maintenance")
            return f"""<mixhtml mix-bottom="#error_container">{ label_error }</mixhtml>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

@app.route("/verify-account", methods=["GET"])
def verify_account():
    try:
        user_verification_key = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        user_verified_at = int(time.time())
        db, cursor = x.db()
        q = "UPDATE users SET user_verification_key = '', user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (user_verified_at, user_verification_key))
        db.commit()
        if cursor.rowcount != 1: raise Exception("Invalid key", 400)
        return redirect( url_for('login') )
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        if ex.args[1] == 400: return ex.args[0], 400    

        # System or developer error
        return "Cannot verify user"

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/logout")
def logout():
    try:
        session.clear()
        return redirect(url_for("view_index"))
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass

    ##############################
@app.route("/browse")
@x.no_cache
def view_browse():
    try:
        user = session.get("user", "")
        if not user: 
            return redirect(url_for("view_index"))
        
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
        genre_mapping = {g["id"]: g["name"] for g in genres_data["genres"]}

        # Attach genre names to movie categories
        for movie_list in [movies_popular, movies_comedy, movies_romance]:
            for movie in movie_list:
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
        SELECT reviews.review_pk, reviews.review_text, users.user_first_name, users.user_avatar_path FROM reviews JOIN users ON users.user_pk = reviews.review_user_fk WHERE reviews.review_movie_id = %s
        """ # reviews.review_count,
        cursor.execute(q, (movie_id,))
        reviews = cursor.fetchall()

        # q = "SELECT * FROM users WHERE review_user_fk = %s"
        # cursor.execute(q, (movie_id,))
        # review_users_data = cursor.fetchall()


        return render_template("movie.html", user=user, data=data, lang=lang, reviews=reviews, movie_id=movie_id)
    except Exception as ex:
        ic(ex)
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

        q = "SELECT * FROM users WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()

        return render_template("account.html", user=user, lang=lang)
    
    except Exception as ex:
        ic(ex)
    finally:
        pass

################## 
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

        # Check if user has uploaded a file, then validate
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
        label_ok = render_template("components/toast/___label_ok.html", message="Account details updated successfully")
        return f"""<browser mix-update="#error_container">{label_ok}</browser>""", 200
    
    except Exception as ex:
        ic(ex)
        
        # User errors
        if ex.args[1] == 400:
            label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#error_container">{ label_error }</mixhtml>""", 400
        
        # Database errors
        if "Duplicate entry" and user_email in str(ex): 
            label_error = render_template("components/toast/___label_error.html", message="Email already registered")
            return f"""<mixhtml mix-update="#error_container">{ label_error }</mixhtml>""", 400
        
        # System or developer error
        label_error = render_template("components/toast/___label_error.html", message="System under maintenance")
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
        q = "SELECT * FROM users WHERE user_deleted_at = '0'" #LIMIT 5
        cursor.execute(q)
        active_users = cursor.fetchall()

         #Active uses in database
        q = "SELECT * FROM users WHERE user_deleted_at != '0'"
        cursor.execute(q)
        deleted_users = cursor.fetchall()
        

        return render_template("admin.html", active_users=active_users, deleted_users=deleted_users)

    except Exception as ex:
        ic(ex)
        return "An error occured", 500
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
            label_error = render_template("components/toast/___label_error.html", message="System under maintenance")
            return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 500
    
        finally:
            pass

################## 
@app.patch("/delete-user")
def delete_user():
    try:
            user_id = request.args.get("user_id")
            if not user_id:
                return "User not found", 400

            db, cursor = x.db()

            # Fetch the users email
            q = "SELECT user_email FROM users WHERE user_pk = %s"
            cursor.execute(q, (user_id,))
            result = cursor.fetchone()
            if not result:
                return "User not found", 404

            # extract email
            # If fetchone() returns a dict - Chatgpt helped me here
            user_email = result['user_email'] if 'user_email' in result else result[0]

            #delete user
            user_deleted_at = int(time.time())
            q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
            cursor.execute(q, (user_deleted_at, user_id))
            db.commit()

            # send email letting user know
            email_user_deleted = render_template("components/email/_email_user_deleted.html")
            x.send_email(user_email, "Dupeflix account suspended", email_user_deleted)

            label_ok = render_template("components/toast/___label_ok.html", message="Successfully deleted user")
            return f"""
            <browser mix-update="#error_container">{ label_ok }</browser>
            """, 200
    except Exception as ex:
        ic(ex)
        return "An error occured", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

################## 
@app.patch("/reactivate-user")
def reactivate_user():
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return "User not found", 400
        
        db, cursor = x.db()
        # Fetch the users email
        q = "SELECT user_email FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_id,))
        result = cursor.fetchone()
        if not result:
            return "User not found", 404

        # extract email
        # If fetchone() returns a dict - Chatgpt helped me here
        user_email = result['user_email'] if 'user_email' in result else result[0]

        #Update user to deleted in database
        user_deleted_at = 0
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        cursor.execute(q, (user_deleted_at, user_id))
        db.commit()
        
        # send email letting user know
        email_user_reactivated = render_template("components/email/_email_user_reactivated.html")
        x.send_email(user_email, "Dupeflix account reactivated", email_user_reactivated)

        label_ok = render_template("components/toast/___label_ok.html", message="Successfully reactivated user")
        return f"""
        <browser mix-update="#error_container">{ label_ok }</browser>
        """, 200
    except Exception as ex:
        ic(ex)
        return "An error occured", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

## Like and unlike with ajax function ###
@app.get("/ajax-heart")
def view_ajax_heart():
    try:
        return render_template("ajax_heart.html")
    except Exception as ex:
        ic(ex)
        return "Error"
    finally:
        pass

@app.patch("/api-like-movie/<movie_id>")
def api_like_movie(movie_id):
    try:
        user_session = session.get("user")
        if not user_session:
            return redirect(url_for("view_index"))

        user_id = user_session.get("user_pk")
        if not user_id:
            return "No user id in session", 500

        db, cursor = x.db()

        # Check if the user already liked the movie
        q = "SELECT movielike_pk FROM movielikes WHERE movielike_user_fk = %s AND movielike_movie_id = %s"
        cursor.execute(q, (user_id, movie_id))
        user_has_liked = cursor.fetchone()

        # If result exists -> unlike (DELETE)
        if user_has_liked:
            # Unlike
            q = "DELETE FROM movielikes WHERE movielike_pk = %s"
            cursor.execute(q, (user_has_liked["movielike_pk"],))
            db.commit()
            like_status = False
        else:
            # Like
            movielike_pk = uuid.uuid4().hex
            created_at = int(time.time())
            q = "INSERT INTO movielikes VALUES (%s, %s, %s, %s)"
            cursor.execute(q, (movielike_pk, movie_id, user_id, created_at))
            db.commit()
            like_status = True

        button_html = render_template("components/___like_movie_btn.html", movie_id=movie_id, like_status=like_status)

        return f"<browser mix-update='#like-btn-{movie_id}'>liked!</browser>"

    except Exception as ex:
        ic(ex)
        return "Error, could not like", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

####################### 
@app.route("/my-list")
def view_mylist():
    try:
        user = session.get("user", "")
        if not user: return redirect(url_for("view_index"))
        lang = user.get("user_language", "en")
        return render_template("mylist.html", user=user, lang=lang)
    except Exception as ex:
        ic(ex)
        return "System under maintenance"
    finally:
        pass


####################### 
@app.get("/api-update-dictionary")
def get_data_from_sheet():
    try:
        # Check if the admin is running this end-point, else show error
        # flaskwebmail
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
    
    # Get referring URL path (e.g., /about/en)
    referer = request.headers.get("Referer", "/")
    path = referer.split("?", 1)[0]  # remove query if present

    # Remove trailing "/" if exists
    path = path.rstrip("/")

    # Split into directory parts
    parts = path.split("/")

    # Replace last part with the new language code
    if parts[-1] in ["en", "nl", "es"]:
        parts[-1] = lang
    else:
        parts.append(lang)

    # Build new URL
    new_path = "/".join(parts)

    return redirect(new_path)


#####################
@app.route("/api-create-review/<movie_id>", methods=["POST"])
def api_create_review(movie_id):
    try:
        user = session.get("user", "")
        if not user: return "invalid user"

        user_pk = user["user_pk"]        
        review_text = x.validate_post(request.form.get("post", ""))
        review_pk = uuid.uuid4().hex
        # Fallbcak
        if not movie_id:
            return redirect(url_for("browse"))

        #review_count = 0
        db, cursor = x.db()
        q = "INSERT INTO reviews VALUES(%s, %s, %s, %s)"
        cursor.execute(q, (review_pk, user_pk, movie_id, review_text))
        db.commit()
        label_ok = render_template("components/toast/___label_ok.html", message="The world is reading your post !")
        review = {
            "user_first_name": user["user_first_name"],
            #"user_avatar_path": user["user_avatar_path"],
            "review_text": review_text,
        }
        html_review_container = render_template("components/___post_container.html")
        html_review = render_template("components/_review.html", review=review)
        return f"""
            <browser mix-bottom="#error_container">{label_ok}</browser>
            <browser mix-top="#reviews">{html_review}</browser>
            <browser mix-replace="#review_container">{html_review_container}</browser>
        """
    except Exception as ex:
        ic("An error accured while creating a review:", ex)
        if "db" in locals(): db.rollback()

        # User errors
        # if "x-error post" in str(ex):
        #     toast_error = render_template("___toast_error.html", message=f"Post - {x.POST_MIN_LEN} to {x.POST_MAX_LEN} characters")
        #     return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # System or developer error
        label_error = render_template("components/toast/___label_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#error_container">{ label_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()   