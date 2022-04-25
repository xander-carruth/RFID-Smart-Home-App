import os
from flask import Flask, render_template, redirect, flash, request, session, url_for
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

def publishEventCallback():
    print("Published.")

def clearNFCVal():
    global nfc_val
    nfc_val = None

def subscribeEventCallback(evt):
    global client
    global nfc_val
    global scheduler
    payload = evt.data
    nfc_arr = payload["User"]
    nfc_id = ' '.join(map(str, nfc_arr))
    print(nfc_id, sys.stderr)
    with app.app_context():
        user_pref = User.query.filter_by(nfc_id=nfc_id).first()
    if(user_pref != None):
        print(user_pref.name, file=sys.stderr)
        preferences = user_pref.preferences
        try:
            print("Beginning")
            eventData = {'Preferences': repr(preferences)}
            client.publishEvent(typeId="RaspberryPi", deviceId="1", eventId="preferences", msgFormat="json",
                                data=eventData, onPublish=publishEventCallback)
            print("Published Data", file=sys.stderr)
        except Exception as e:
            print("Exception: ", e, file=sys.stderr)
    else:
        nfc_val = nfc_id
        future_time = datetime.now() + timedelta(minutes=1)
        scheduler.add_job(func=clearNFCVal, trigger='date', run_date=future_time, id=None)

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
    global client
    try:
        options = wiotp.sdk.application.parseConfigFile("webApp.yaml")
        client = wiotp.sdk.application.ApplicationClient(config=options)
        client.connect()
        print("Connection established", file=sys.stderr)
        client.subscribeToDeviceEvents(eventId="doorStatus")
        client.deviceEventCallback = subscribeEventCallback
    except Exception as e:
        print("Exception: ", e, file=sys.stderr)

@app.before_first_request
def startScheduler():
    global scheduler
    scheduler = APScheduler()
    scheduler.start()

@app.route('/', methods=['GET', 'POST'])
def landingpage():
    if current_user.is_authenticated:
        if current_user.nfc_id != None:
            form = PreferencesForm(obj=current_user.preferences)
            if form.validate_on_submit():
                user = User.query.get(current_user.id)
                preferences = user.preferences
                print(form.app1.data, file=sys.stderr)
                print(form.app2.data, file=sys.stderr)
                preferences.app1 = form.app1.data
                preferences.app2 = form.app2.data
                preferences.app3 = form.app3.data
                preferences.app4 = form.app4.data
                db.session.commit()
                print(current_user.preferences, file=sys.stderr)
                print(preferences, file=sys.stderr)

            return render_template(
                "static.html",
                form=form
            )
        else:
            return redirect(url_for('nfc_update'))
    else:
        return render_template(
            "static.html"
        )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    User sign-up page.
    GET requests serve sign-up page.
    POST requests validate form & user creation.
    """
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
        title='Create an Account.',
        form=form,
        template='signup-page',
        body="Sign up for a user account."
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Log-in page for registered users.
    GET requests serve Log-in page.
    POST requests validate and redirect user to dashboard.
    """
    # Bypass if user is logged in
    if current_user.is_authenticated:
        return redirect(url_for('landingpage'))

    form = LoginForm()
    # Validate login attempt
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(password=form.password.data):
            login_user(user)
            # next_page = request.args.get('next')
            # return redirect(next_page or url_for('landingpage'))
            return redirect(url_for('landingpage'))
        flash('Invalid username/password combination')
        return redirect(url_for('login'))
    return render_template(
        'login.html',
        form=form,
        title='Log in.',
        template='login-page',
        body="Log in with your User account."
    )

@app.route("/settings", methods=['GET', 'POST'])
@login_required
def nfc_update():
    global nfc_val
    global current_nfc

    if(request.form.get("submit") == None):
        if(current_user.nfc_id != None):
            current_nfc = current_user.nfc_id
        else:
            current_nfc = "None"
    # if(request.form.get("nfc_var")!=None):
    #     current_nfc = request.form.get("nfc_var")
    #     print(current_nfc, file=sys.stderr)
    if(nfc_val != None):
        current_nfc = nfc_val
        nfc_val = None


    if(request.form.get("submit") != None):
        print(current_nfc, file=sys.stderr)
    if(request.form.get("submit") == "submit" and len(current_nfc) > 5):
        user = User.query.get(current_user.id)
        user.nfc_id = current_nfc
        preferences = Preferences(app1=True, app2=True, app3=True, app4=True, user=user)
        user.preferences = preferences
        db.session.add(preferences)
        # print(current_user.preferences, file=sys.stderr)
        # print(preferences, file=sys.stderr)
        db.session.commit()
        return redirect(url_for('landingpage'))
    elif(request.form.get("submit") == "submit"):
        return render_template(
            'settings.html',
            title='Settings',
            template='settings-page',
            body="Update your NFC ID",
            nfc_var=current_nfc,
            err_text="Pairing failed"
        )
    else:
        return render_template(
            'settings.html',
            title='Settings',
            template='settings-page',
            body="Update your NFC ID",
            nfc_var=current_nfc,
            err_text=""
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

