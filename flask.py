"""Flask-OAuthlib sample for Microsoft Graph"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import uuid

import flask
from flask_oauthlib.client import OAuth
from json2html import *
import config

APP = flask.Flask(__name__, template_folder='static/templates')
APP.debug = True
APP.secret_key = 'development'
OAUTH = OAuth(APP)
MSGRAPH = OAUTH.remote_app(
    'microsoft', consumer_key=config.CLIENT_ID, consumer_secret=config.CLIENT_SECRET,
    request_token_params={'scope': config.SCOPES},
    base_url=config.RESOURCE + config.API_VERSION + '/',
    request_token_url=None, access_token_method='POST',
    access_token_url=config.AUTHORITY_URL + config.TOKEN_ENDPOINT,
    authorize_url=config.AUTHORITY_URL + config.AUTH_ENDPOINT)

@APP.route('/')
def homepage():
    """Render the home page."""
    return flask.render_template('homepage.html', sample='Flask-OAuthlib')

@APP.route('/login')
def login():
    """Prompt user to authenticate."""
    flask.session['state'] = str(uuid.uuid4())
    return MSGRAPH.authorize(callback=config.REDIRECT_URI, state=flask.session['state'])

@APP.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""
    if str(flask.session['state']) != str(flask.request.args['state']):
        raise Exception('state returned to redirect URL does not match!')
    response = MSGRAPH.authorized_response()
    flask.session['access_token'] = response['access_token']
    return flask.redirect('/document')

@APP.route('/document')
def document():
    """Confirm user authentication by calling Graph and displaying some data."""
    html = flask.render_template('report_head.html',
                                 sample='Flask-OAuthlib')
    footer = flask.render_template('report_foot.html')                                 
    content = ''

    endpoint = 'deviceManagement/deviceConfigurations'


    for item in get_api(endpoint)['value']:
        table = json2html.convert(json = item, table_attributes="id=\"info-table\"")
        head = flask.render_template('report_table_head.html',
                                 endpoint= '/' + endpoint + '[' + item['displayName'] + ']')
        foot = flask.render_template('report_table_foot.html')                                
        content = content + head + table + foot
    html = html + con + footer
    return html

def section():

def configuration(api):
    for item in get_api(endpoint)['value']:
        table = json2html.convert(json = item, table_attributes="id=\"info-table\"")
        head = flask.render_template('report_table_head.html',
                                 endpoint= '/' + endpoint + '[' + item['displayName'] + ']')
        foot = flask.render_template('report_table_foot.html')                                
        return head + table + foot


def get_api(api):
    endpoint = api
    headers = {'SdkVersion': 'sample-python-flask',
               'x-client-SKU': 'sample-python-flask',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    graphdata = MSGRAPH.get(endpoint, headers=headers).data
    return graphdata

@APP.route('/deviceManagement/deviceConfigurations')
def graphcall():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = 'me'
    endpoint = 'deviceManagement/deviceConfigurations'
    headers = {'SdkVersion': 'sample-python-flask',
               'x-client-SKU': 'sample-python-flask',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    graphdata = MSGRAPH.get(endpoint, headers=headers).data
    return flask.render_template('graphcall.html',
                                 graphdata=graphdata,
                                 endpoint=config.RESOURCE + config.API_VERSION + '/' + endpoint,
                                 sample='Flask-OAuthlib')

@MSGRAPH.tokengetter
def get_token():
    """Called by flask_oauthlib.client to retrieve current access token."""
    return (flask.session.get('access_token'), '')

if __name__ == '__main__':
    APP.run(host="0.0.0.0",port=5001)
