from flask import Flask, render_template, request, redirect, jsonify, \
    url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import NC, Base, GameList, User

from flask import session as login_session
import random
import string

# IMPORTS FOR THIS STEP
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "nintendo"

app = Flask(__name__)

engine = create_engine('sqlite:///nintendolistwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create anti-forgery state token


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already '
                                            ' connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

# see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;"'
    '"-webkit-border-radius: 150px;-moz-border-radius: 150px;">"'
    flash("  logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not'
                                            ' connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
          % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token'
                                            'for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Json section
@app.route('/nintendo/<int:nintendo_id>/list/JSON')
def nintendoListJSON(nintendo_id):
    nintendo = session.query(NC).filter_by(id=nintendo_id).one()
    lists = session.query(GameList).filter_by(nintendo_id=nintendo_id).all()
    return jsonify(GameLists=[i.serialize for i in lists])


# Show all Consoles
@app.route('/')
@app.route('/nintendo/')
def showNintendos():
    nintendos = session.query(NC).order_by(asc(NC.name))
    if 'username' not in login_session:
        return render_template('publicnintendos.html', nintendos=nintendos)
    else:
        # return "This page will show all my consoles"
        return render_template('nintendos.html', nintendos=nintendos)

# Create a new Console


@app.route('/nintendo/new/', methods=['GET', 'POST'])
def newNintendo():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newNintendo = NC(name=request.form['name'],
                         user_id=login_session['user_id'])
        session.add(newNintendo)
        flash('New Console %s Successfully Created' % newNintendo.name)
        session.commit()
        return redirect(url_for('showNintendos'))
    else:
        return render_template('newNintendo.html')
    

# Edit a console


@app.route('/nintendo/<int:nintendo_id>/edit/', methods=['GET', 'POST'])
def editNintendo(nintendo_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedNintendo = session.query(
        NC).filter_by(id=nintendo_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedNintendo.name = request.form['name']
            flash('Console Successfully Edited %s' % editedNintendo.name)
            return redirect(url_for('showNintendos'))
    else:
        return render_template(
            'editNintendo.html', nintendo=editedNintendo)

    

# Delete a Console


@app.route('/nintendo/<int:nintendo_id>/delete/', methods=['GET', 'POST'])
def deleteNintendo(nintendo_id):
    if 'username' not in login_session:
        return redirect('/login')
    nintendoToDelete = session.query(NC).filter_by(id=nintendo_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if nintendoToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction()"
        "{alert('You are not authorized to delete this console.'"
        "' Please create your own console in order to delete.')"
        ";}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(nintendoToDelete)
        flash('%s Successfully Deleted' % nintendoToDelete.name)
        session.commit()
        return redirect(
            url_for('showNintendos', nintendo_id=nintendo_id))
    else:
        return render_template(
            'deleteNintendo.html', nintendo=nintendoToDelete)
    

# Show Games


@app.route('/nintendo/<int:nintendo_id>/')
@app.route('/nintendo/<int:nintendo_id>/list/')
def showGameList(nintendo_id):
    nintendo = session.query(NC).filter_by(id=nintendo_id).one()
    creator = getUserInfo(nintendo.user_id)
    lists = session.query(GameList).filter_by(
        nintendo_id=nintendo_id).all()
    if 'username' not in login_session or \
            creator.id != login_session['user_id']:
        return render_template('publicgames.html',
                               lists=lists, nintendo=nintendo, creator=creator)
    else:
        return render_template('list.html', lists=lists,
                               nintendo=nintendo, creator=creator)
    


# Show Game detail
@app.route('/nintendo/<int:nintendo_id>/list/<int:list_id>/', methods=['GET'])
def GameDetail(nintendo_id, list_id):
    nintendo = session.query(NC).filter_by(id=nintendo_id).one()
    lists = session.query(GameList).filter_by(
        id=list_id).all()
    return render_template('description.html', lists=lists, nintendo=nintendo)


# Create a new game


@app.route('/nintendo/<int:nintendo_id>/list/new/', methods=['GET', 'POST'])
def newGameList(nintendo_id):
    if 'username' not in login_session:
        return redirect('/login')
    nintendo = session.query(NC).filter_by(id=nintendo_id).one()
    if login_session['user_id'] != nintendo.user_id:
        return "<script>function myFunction()"
        "{alert('You are not authorized to games to this console.'"
        "'Please create your own console in order to add games.');"
        "}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        newGame = GameList(name=request.form['name'],
                           maker=request.form['maker'],
                           description=request.form['description'],
                           price=request.form['price'],
                           nintendo_id=nintendo_id)
        session.add(newGame)
        session.commit()
        flash('New game %s Item Successfully Created' % (newGame.name))

        return redirect(url_for('showGameList', nintendo_id=nintendo_id))
    else:
        return render_template('newGameList.html', nintendo_id=nintendo_id)
    

# Edit a Game 


@app.route('/nintendo/<int:nintendo_id>/list/<int:list_id>/edit',
           methods=['GET', 'POST'])
def editGameList(nintendo_id, list_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedGame = session.query(GameList).filter_by(id=list_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedGame.name = request.form['name']
        if request.form['maker']:
            editedGame.maker = request.form['maker']
        if request.form['description']:
            editedGame.description = request.form['description']
        if request.form['price']:
            editedGame.price = request.form['price']
        session.add(editedGame)
        session.commit()
        flash('Game Successfully Edited')
        return redirect(url_for('showGameList', nintendo_id=nintendo_id))
    else:

        return render_template('editGameList.html', nintendo_id=nintendo_id,
                               list_id=list_id, lists=editedGame)

    

# Delete a game 


@app.route('/nintendo/<int:nintendo_id>/list/<int:list_id>/delete',
           methods=['GET', 'POST'])
def deleteGameList(nintendo_id, list_id):
    if 'username' not in login_session:
        return redirect('/login')
    nintendo = session.query(NC).filter_by(id=nintendo_id).one()
    gameToDelete = session.query(GameList).filter_by(id=list_id).one()
    if login_session['user_id'] != nintendo.user_id:
        return "<script>function myFunction()"
        "{alert('You are not authorized to'"
        "'delete a game to this console.'"
        "'Please create your own console in order to delete games.');"
        "}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(gameToDelete)
        session.commit()
        flash('Game Successfully Deleted')
        return redirect(url_for('showGameList', nintendo_id=nintendo_id))
    else:
        return render_template('deleteGameList.html', list=gameToDelete)
    


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
