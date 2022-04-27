import os
from flask import Flask, render_template, redirect, flash, request, session, url_for, jsonify
from flask_session import Session
from flask_login import current_user, logout_user, login_user, login_required
from flask_apscheduler import APScheduler
from redis import Redis
from . import create_app, db, login_manager
from .models import User, Preferences
from .forms import SignupForm, LoginForm, PreferencesForm
import sys
import time
import json
import wiotp.sdk.application
from threading import Thread
from datetime import datetime, timedelta

nfc_val = None
global scheduler
client = None
current_nfc = "None"

def publishEventCallback():
    """Print published when preferences are published"""
    print("Published.")

def clearNFCVal():
    """Clear NFC_val after 60 seconds"""
    global nfc_val
    nfc_val = None

def subscribeEventCallback(evt):
    """Add to pairing variable if it is not paired to an ID, otherwise publish preferences associated with ID"""
    global client
    global nfc_val
    global scheduler
    payload = evt.data
    nfc_arr = payload["User"]
    nfc_id = ' '.join(map(str, nfc_arr))
    # Check if NFC ID is in database
    with app.app_context():
        user_pref = User.query.filter_by(nfc_id=nfc_id).first()
    # Publish user preferences is user is found
    if(user_pref != None):
        preferences = user_pref.preferences
        try:
            eventData = {'Preferences': repr(preferences)}
            client.publishEvent(typeId="RaspberryPi", deviceId="1", eventId="preferences", msgFormat="json",
                                data=eventData, onPublish=publishEventCallback)
            print("Published Data", file=sys.stderr)
        except Exception as e:
            print("Exception: ", e, file=sys.stderr)
    else:
        nfc_val = nfc_id
        future_time = datetime.now() + timedelta(minutes=1)
        # Start job to clear our the NFC ID after 60 seconds
        scheduler.add_job(func=clearNFCVal, trigger='date', run_date=future_time, id=None)

"""Create the app"""
try:
    app = create_app()
    app.secret_key = "thekey"
except ImportError:
    class AppClass:
        config = {}

        def route(self, *args, **kwargs):
            return lambda x: x

        def run(self):
            pass

    app = AppClass()

@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in on every page load."""
    if user_id is not None:
        return User.query.get(user_id)
    return None

@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash('You must be logged in to view that page.')
    return redirect(url_for('login'))

@app.before_first_request
def startSubscriber():
    """Start subscriber to userTag channel before app starts"""
    global client
    try:
        options = wiotp.sdk.application.parseConfigFile("webApp.yaml")
        client = wiotp.sdk.application.ApplicationClient(config=options)
        client.connect()
        print("Connection established", file=sys.stderr)
        client.subscribeToDeviceEvents(eventId="userTag")
        client.deviceEventCallback = subscribeEventCallback
    except Exception as e:
        print("Exception: ", e, file=sys.stderr)

@app.before_first_request
def startScheduler():
    """Start APScheduler before app starts for clearing the NFC ID"""
    global scheduler
    scheduler = APScheduler()
    scheduler.start()

@app.route('/', methods=['GET', 'POST'])
def landingpage():
    """Landing page with preference form is user is authenticated and has NFC ID associated"""
    if current_user.is_authenticated:
        if current_user.nfc_id != None:
            form = PreferencesForm(obj=current_user.preferences)
            if form.validate_on_submit():
                user = User.query.get(current_user.id)
                preferences = user.preferences
                preferences.app1 = form.app1.data
                preferences.app2 = form.app2.data
                preferences.app3 = form.app3.data
                preferences.app4 = form.app4.data
                db.session.commit()

            return render_template(
                "static.html",
                form=form
            )
        else:
            return redirect(url_for('nfc_update', nfc_var="None"))
    else:
        return render_template(
            "static.html"
        )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup page"""
    form = SignupForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user is None:
            user = User(
                name=form.name.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()  # Create new user
            login_user(user)  # Log in as newly created user
            return redirect(url_for('landingpage'))
        flash('A user already exists with that email address.')
    return render_template(
        'signup.html',
        form=form
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    # Bypass if user is logged in
    if current_user.is_authenticated:
        return redirect(url_for('landingpage'))

    form = LoginForm()
    # Validate login attempt
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(password=form.password.data):
            login_user(user)
            return redirect(url_for('landingpage'))
        flash('Invalid username/password combination')
        return redirect(url_for('login'))
    return render_template(
        'login.html',
        form=form,
        body="Log in with your User account."
    )

@app.route("/settings/<nfc_var>", methods=['GET', 'POST'])
@login_required
def nfc_update(nfc_var):
    """
    Settings page
    GET displays current saved NFC ID
    POST pairs NFC ID and saves NFC ID and default User preferences on submit
    """
    global nfc_val
    global current_nfc

    # If it is being paired and nfc_id is nfc_var is none, current_nfc is none
    if(request.form.get("submit") == None):
        if(current_user.nfc_id != None):
            current_nfc = current_user.nfc_id
        elif(nfc_var=="None"):
            current_nfc = "None"

    # If there is a recently sent NFC_ID, set the nfc_id displayed on the page to the id
    if(nfc_val != None and request.form.get("pair")=="pair"):
        current_nfc = nfc_val
        nfc_val = None

    # If the value of the form is not none and they pressed submit, add nfc_id and default preferences to user
    if(request.form.get("submit") == "submit" and len(current_nfc) > 5):
        user = User.query.get(current_user.id)
        user.nfc_id = current_nfc
        preferences = Preferences(app1=True, app2=True, app3=True, app4=True, user=user)
        user.preferences = preferences
        db.session.add(preferences)
        db.session.commit()
        return jsonify({'redirect': url_for("landingpage")})
    elif(request.form.get("submit") == "submit" or request.form.get("pair") == "pair"):
        return jsonify({'redirect': url_for("nfc_update", nfc_var=current_nfc)})
    else:
        return render_template(
            'settings.html',
            nfc_var=current_nfc
        )

@app.route("/logout")
@login_required
def logout():
    """User log-out logic."""
    logout_user()
    return redirect(url_for('landingpage'))

count = 0
if __name__ == "main":
    app.config['SESSION_TYPE'] = 'memcache'
    sess = Session()
    sess.init_app(app)
    app.run(threaded=True)