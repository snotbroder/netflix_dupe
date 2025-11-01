from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import x
import time
import uuid
import os

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

app = Flask(__name__)

# Set the maximum file size to 10 MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024   # 1 MB

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
 

##############################
##############################
##############################
def _____USER_____(): pass 
##############################
##############################
##############################

@app.get("/")
def view_index():
    
    return render_template("index.html")


##############################
@app.route("/login", methods=["GET", "POST"])
@x.no_cache
def login():

    if request.method == "GET":
        if session.get("user", ""): return redirect(url_for("browse"))
        return render_template("login.html", x=x)

    if request.method == "POST":
        try:
            # Validate           
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            # Connect to the database
            q = "SELECT * FROM users WHERE user_email = %s"
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()
            if not user: raise Exception("User not found, please check for spelling", 400)

            if not check_password_hash(user["user_password"], user_password):
                raise Exception("Invalid credentials", 400)

            if user["user_verification_key"] != "":
                raise Exception("User not verified. Please check your email", 400)

            user.pop("user_password")

            session["user"] = user
        
            return f"""<browser mix-redirect="/browse"></browser>"""

        except Exception as ex:
            ic(ex)

            # User errors
            if ex.args[1] == 400:
                label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
                return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 400

            # System or developer error
            toast_error = render_template("components/toast/___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()


##############################
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "GET":
        return render_template("signup.html", x=x)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            user_first_name = x.validate_user_first_name()

            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = "twitter_default.png"
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0

            user_hashed_password = generate_password_hash(user_password)

            # Connect to the database
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s)"
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, 
            user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at))
            db.commit()

            # send verification email
            email_verify_account = render_template("components/email/_email_verify_account.html", user_verification_key=user_verification_key)
            ic(email_verify_account)
            x.send_email(user_email, "Verify your account", email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        except Exception as ex:
            ic(ex)
            # # User errors
            # if ex.args[1] == 400:
            #     toast_error = render_template("components/toast/___toast_error.html", message=ex.args[0])
            #     return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            # User errors
            if ex.args[1] == 400:
                label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
                return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 400
            
            # Database errors
            if "Duplicate entry" and user_email in str(ex): 
                toast_error = render_template("components/toast/___toast_error.html", message="Email already registered")
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # System or developer error 
            toast_error = render_template("components/toast/___toast_error.html", message="System under maintenance")
            return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

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
@app.get("/browse")
@x.no_cache
def browse():
    try:
        user = session.get("user", "")
        if not user: return redirect(url_for("view_index"))
        db, cursor = x.db()

        # q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk ORDER BY RAND() LIMIT 5"
        # cursor.execute(q)
        # tweets = cursor.fetchall()
        # ic(tweets)

        # q = "SELECT * FROM trends ORDER BY RAND() LIMIT 3"
        # cursor.execute(q)
        # trends = cursor.fetchall()
        # ic(trends)

        # q = "SELECT * FROM users WHERE user_pk != %s ORDER BY RAND() LIMIT 3"
        # cursor.execute(q, (user["user_pk"],))
        # suggestions = cursor.fetchall()
        # ic(suggestions)

        return render_template("browse.html", user=user)
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
