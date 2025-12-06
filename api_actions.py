from flask import Flask, Blueprint, render_template, request, session, redirect, url_for
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
from datetime import datetime
from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

api_actions = Blueprint("api_actions", __name__)

### LOGIN ###
@api_actions.post("/api-login")
@api_actions.post("/api-login/<lang>")
def login( lang = "en"):
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

### BLOCK USER ###
@api_actions.patch("/api-block-user/<blocking_user_fk>/<blocker_user_fk>")
def block_user(blocking_user_fk, blocker_user_fk):
    try: 
        ic(blocking_user_fk)
        ic(blocker_user_fk)
    except Exception as ex: 
        ic(ex)
    finally:
        pass

### CREATE REVIEW ###
@api_actions.route("/api-create-review/<movie_id>", methods=["POST"])
def create_review(movie_id):
    try:
        user = session.get("user", "")
        if not user: return "invalid user"

        user_pk = user["user_pk"]        
        review_text = x.validate_post(request.form.get("post", ""))
        review_pk = uuid.uuid4().hex
        review_created_at = int(time.time()) 
        review_deleted_at = 0
        # Fallbcak
        if not movie_id:
            return redirect(url_for("browse"))

        db, cursor = x.db()
        q = "INSERT INTO reviews VALUES(%s, %s, %s, %s, %s, %s)"
        cursor.execute(q, (review_pk, user_pk, movie_id, review_text, review_created_at, review_deleted_at))
        db.commit()

        review = {
            "user_first_name": user["user_first_name"],
            "user_avatar_path": user["user_avatar_path"],
            "review_text": review_text,
            "review_created_at": review_created_at,
        }
        html_review_container = render_template("components/___review_container.html")
        html_review = render_template("components/_review.html", review=review, user=user)
        label_ok = render_template("components/toast/___label_ok.html", message=x.lans("feedback_success_created_review"))
        return f"""
            <browser mix-bottom="#error_container">{label_ok}</browser>
            <browser mix-top="#reviews">{html_review}</browser>
            <browser mix-replace="#review_container">{html_review_container}</browser>
        """
    except Exception as ex:
        ic("An error accured while creating a review:", ex)
        if "db" in locals(): db.rollback()

       # User errors
        if "x-error post" in str(ex):
            label_error = render_template("components/toast/___label_error.html", message=f"{x.lans('feedback_invalid_review')} {x.POST_MIN_LEN} {x.lans('system_to')} {x.POST_MAX_LEN} {x.lans('system_characters')}")
            return f"""<browser mix-bottom="#error_container">{label_error}</browser>"""

        # System or developer error
        label_error = render_template("components/toast/___label_error.html", message=x.lans("feedback_system_maintenance"))
        return f"""<browser mix-bottom="#error_container">{ label_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()   