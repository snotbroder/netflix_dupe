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


### SIGN UP ###
@api_actions.post("/api-signup")
@api_actions.post("/api-signup/<lang>")
@x.no_cache
def signup(lang = "en"):
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
        user_new_password_key = "0"
        user_deleted_at = 0

        user_hashed_password = generate_password_hash(user_password)

        # Connect to the database
        q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        db, cursor = x.db()
        cursor.execute(q, (user_pk, user_email, user_hashed_password, 
        user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at, user_new_password_key, user_deleted_at))
        db.commit()

        # send verification email
        email_verify_account = render_template("components/email/_email_verify_account.html", user_verification_key=user_verification_key)
        ic(email_verify_account)
        x.send_email(user_email, "Verify your account", email_verify_account)
        
        label_ok = render_template("components/toast/___label_ok.html", message=x.lans("feedback_success_signup_email_sent"))
        return f"""<mixhtml mix-update="#error_container">{ label_ok }</mixhtml>""", 200
    
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


### LOGIN ###
@api_actions.post("/api-login")
@api_actions.post("/api-login/<lang>")
def login( lang = "en"):
    try:
        # Validate           
        user_email = x.validate_user_email(lang)
        user_password = x.validate_user_password(lang)

        # Connect to the database
        q = "SELECT * FROM users WHERE user_email = %s"
        db, cursor = x.db()
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()

        if not user: 
            raise Exception(x.lans("feedback_user_not_found"), 400)
        
        if user["user_deleted_at"] != 0:
            raise Exception(x.lans("feedback_invalid_user_deleted"), 400)

        if not check_password_hash(user["user_password"], user_password):
            raise Exception(x.lans("feedback_invalid_password"), 400)

        if user["user_verification_key"] != "0":
            raise Exception(x.lans("feedback_user_not_verified"), 400)
        
        
        user.pop("user_password")

        # Add the default language to the user session
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


### LOGOUT ###
@api_actions.get("/logout")
def api_logout():
    try:
        session.clear()
        return redirect(url_for("view_index"))
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass


### VERIFY ACCOUNT ###
@api_actions.route("/verify-account", methods=["GET"])
def api_verify_account():
    try:
        user_verification_key = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        user_verified_at = int(time.time())
        db, cursor = x.db()
        q = "UPDATE users SET user_verification_key = '0', user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (user_verified_at, user_verification_key))
        db.commit()
        if cursor.rowcount != 1: raise Exception("Invalid key", 400)
        return redirect( url_for('view_login') )
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        if ex.args[1] == 400: return ex.args[0], 400    

        # System or developer error
        return "Cannot verify user", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


### REVIEW CREATE ###
@api_actions.route("/api-create-review/<movie_id>", methods=["POST"])
def api_create_review(movie_id):
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
            return redirect(url_for("view_browse"))

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


### REVIEW DELETE ###
@api_actions.patch("/api-delete-review/<review_pk>")
def api_delete_review(review_pk):
    try:
        user = session.get("user", "")
        if not user: return "invalid user"

        review_deleted_at = int(time.time())  
        # Fallbcak
        if not review_pk:
            return redirect(url_for("view_browse"))

        db, cursor = x.db()
        q = "UPDATE reviews SET review_deleted_at = %s WHERE review_pk = %s AND review_deleted_at = 0"
        cursor.execute(q, (review_deleted_at, review_pk))
        db.commit()
        label_ok = render_template("components/toast/___label_ok.html", message="Deleted review!")        

        # if session.get("admin_session") == True:
        #     q = """
        #     SELECT users.user_email
        #     FROM reviews
        #     JOIN users ON users.user_pk = reviews.review_user_fk
        #     WHERE reviews.review_pk = %s;
        #     """
        #     cursor.execute(q, (review_pk,))
        #     user_email_row = cursor.fetchone()

        #     #extract from row
        #     if user_email_row:
        #         user_email = user_email_row["user_email"]

        #     email_deleted_review = render_template("components/email/_email_deleted_review.html")
        #     x.send_email(user_email, "Deleted review | Dupeflix", email_deleted_review)
            
        #     return f"""
        #     <browser mix-remove="#review-{review_pk}"></browser>
        #     <browser mix-bottom='#error_container'>{label_ok}</browser>
        #     """

        

        return f"""
            <browser mix-bottom="#error_container">{label_ok}</browser>
            <browser mix-bottom=".error_container_dialog">{label_ok}</browser>
            <browser mix-remove="#review-{review_pk}"></browser>
        """
    except Exception as ex:
        ic("An error occured while deleting a review:", ex)
        if "db" in locals(): db.rollback()

        # System or developer error
        label_error = render_template("components/toast/___label_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#error_container">{ label_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close() 


### FORGOT PASSWORD ###
@api_actions.post("/forgot-password")
@api_actions.post("/forgot-password/<lang>")
def api_forgot_password(lang = "en"):
    try:
        user_email = x.validate_user_email(lang)

        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_email = %s"
        cursor.execute(q, (user_email,))
        user = cursor.fetchone()
        ic(user)
        if not user:
            raise Exception(x.lans("feedback_user_not_found"), 400)

        if user["user_verification_key"] != "0":
            raise Exception(x.lans("feedback_user_not_verified"), 400)
        
        if user["user_new_password_key"] != "0":
            raise Exception(x.lans("feedback_pass_email_already_sent"), 400)

        #Create new password key for email and system
        user_new_password_key = uuid.uuid4().hex

        q = "UPDATE users SET user_new_password_key = %s WHERE user_email = %s"
        cursor.execute(q, (user_new_password_key, user_email,))
        db.commit()

        # send email with link and key
        email_new_password = render_template("components/email/_email_forgot_password.html", user_new_password_key=user_new_password_key)
        x.send_email(user_email, "Forgot password | Dupeflix", email_new_password)

        label_ok = render_template("components/toast/___label_ok.html", message=x.lans('feedback_check_email'))

        return f"""
            <browser mix-replace="#error_container">{label_ok}</browser>
        """
    except Exception as ex: 
        ic(ex)
        #User errors
        if ex.args[1] == 400:
            label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
            ic("An error occured in Email")
            return f"""<browser mix-update="#error_container">{ label_error }</browser>""", 400
        
        # System or developer error
        label_error = render_template("components/toast/___label_error.html", message=x.lans('feedback_system_maintenance'))
        return f"""<browser mix-bottom="#error_container">{ label_error }</browser>""", 500

    finally: 
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


### PASSWORD UPDATE ###
@api_actions.route("/api-update-password", methods=["POST"])
@x.no_cache
def api_update_password():
    try: 
        user_new_password_key = x.validate_uuid4_without_dashes(request.args.get("key"))

        if user_new_password_key == "0":
            raise redirect(url_for("index.html"))

        user_new_password = x.validate_user_password()
        user_confirm_new_password = x.validate_user_password_confirm()

        if user_new_password != user_confirm_new_password:
            raise Exception(x.lans('feedback_pass_must_match'), 400)
        
        user_hashed_new_password = generate_password_hash(user_new_password)
        db, cursor = x.db()
        q = "UPDATE users SET user_new_password_key = '0', user_password = %s WHERE user_new_password_key = %s"
        cursor.execute(q, (user_hashed_new_password, user_new_password_key))
        db.commit()

        #label_ok = render_template("components/toast/___label_ok.html", message=x.lans('feedback_pass_updated_success'))
        #<browser mix-update="#error_container">{label_ok}</browser>
        return f"""
                <browser mix-redirect="/login"></browser>
                """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        if ex.args[1] == 400:
            label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
            return f"""<browser mix-update="#error_container">{label_error}</browser>""", 400

        # System or developer error
        label_error = render_template("components/toast/___label_error.html", message=ex.args[0])
        return f"""<browser mix-update="#error_container">{label_error}</browser>""", 400
    finally: 
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

### ACCOUNT DELETE ###
@api_actions.patch("/delete-user")
def api_delete_user():
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

            # Check if the deletion comes from the logged in user
            user = session.get("user")
            logged_in_user = user.get("user_pk")

            if logged_in_user == user_id:
                session.clear()
                return "<browser mix-redirect='/logout'></browser>"

            label_ok = render_template("components/toast/___label_ok.html", message="Successfully deleted user")
            return f"""
            <browser mix-update="#error_container">{ label_ok }</browser>
            <browser mix-remove="#user-{user_id}"></browser>
            """, 200
    except Exception as ex:
        ic(ex)
        return "An error occured", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@api_actions.patch("/reactivate-user")
def api_reactivate_user():
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
        <browser mix-remove="#user-{user_id}"></browser>
        <browser mix-update="#error_container">{ label_ok }</browser>
        """, 200
    except Exception as ex:
        ic(ex)
        return "An error occured", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

### BLOCK USER ###
@api_actions.patch("/api-block-user/<blocking_user_fk>/<blocker_user_fk>/<review_pk>")
def api_block_user(blocking_user_fk, blocker_user_fk, review_pk):
    try:
        user = session.get("user")
        user_pk = user.get("user_pk")
        if not user_pk:
            return "No user id in session", 500

        db, cursor = x.db()
        q = "INSERT INTO blocks (block_blocker_user_fk, block_blocking_user_fk) VALUES(%s, %s)"
        cursor.execute(q, (blocker_user_fk, blocking_user_fk))
        db.commit()

        label_ok = render_template("components/toast/___label_ok.html", message=x.lans("feedback_success_blocked_user"))
        return f"""
        <browser mix-replace='#review-{review_pk}'></browser>
        <browser mix-replace='#error_container'>{label_ok}</browser>
        """
    
    except Exception as ex:
        ic(ex)
        if "Duplicate entry" in str(ex): 
            label_error = render_template("components/toast/___label_error.html", message=x.lans("feedback_invalid_already_blocked"))
            return f"""<mixhtml mix-update="#error_container">{ label_error }</mixhtml>""", 400
        return "Error, could not like", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

### UNBLOCK USER ###
@api_actions.patch("/api-block-user/<blocked_user_fk>/<blocker_user_fk>")
def api_unblock_user(blocked_user_fk, blocker_user_fk):
    try:
        user = session.get("user")
        user_pk = user.get("user_pk")
        if not user_pk:
            return "No user id in session", 500

        db, cursor = x.db()
        q = "DELETE FROM blocks WHERE block_blocker_user_fk = %s AND block_blocking_user_fk = %s"
        cursor.execute(q, (blocker_user_fk, blocked_user_fk))
        db.commit()

        #button_html = render_template("components/___mylist_container.html", movie_id=movie_id, has_user_liked=has_user_liked)
        #f"<browser mix-replace='#review-{review_pk}'>You have blocke this user</browser>"
        label_ok = render_template("components/toast/___label_ok.html", message=x.lans("feedback_success_unblocked_user"))
        return f"""
        <browser mix-update="#error_container">{ label_ok }</browser>
        <browser mix-replace="#blocked-{blocked_user_fk}"></browser>
        """, 200

    except Exception as ex:
        ic(ex)
        return "Error, could not unblock", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

