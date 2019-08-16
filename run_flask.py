"""Flask-OAuthlib sample for Microsoft Graph"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import uuid

import flask
from flask_oauthlib.client import OAuth
from json2html import *
import config
import stringcase

import yaml
import json

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
    html = html + content + footer
    return html

def process():
    html = flask.render_template('report_head.html',
                                 sample='Flask-OAuthlib')
    footer = flask.render_template('report_foot.html')                                 
    content = ''
    with open("o365.yml", 'r') as yaml_in:
        # data = json.dumps(yaml.load(yaml_in))
        global data
        data = json.loads(json.dumps(yaml.load(yaml_in)))
        content = ''
        for section_title in data.keys():
            content = content + section(section_title)
    html = html + content + footer
    return html
    
def section(section_title):
    section_html = '<h2>' + stringcase.titlecase(section_title) + '</h2>'
    # configs = data[section_title]
    html_content = ''
    for content_data in data[section_title]:
            # html_content = html_content + content_title['name']
            html_content = html_content + content(section_title, content_data)
    return section_html + html_content

def content(section_title, content_data):
    api_name = content_data['name']
    section_html = '<h3>' + stringcase.titlecase(api_name) + '</h3>'
    apiCall = section_title + '/' + api_name
    section_html = section_html + '<p> /' + apiCall + '</p>'
    # configs = data[section_title]
    # configuration(api_name, content_data)
    # return section_html 
    return section_html + configuration(apiCall, content_data)
    # return section_html + str(get_api(apiCall))


def configuration(api, content_data):
    endpoint = api
    html = ''
    primary = content_data['primary']
    for item in get_api(endpoint)['value']:
        item_processed = dict(sorted(item.items()))
        for remove_item in content_data['exclude']:
            # If key exist in dictionary then delete it using del.
            if remove_item in item_processed:
                del item_processed[remove_item]
        table = json2html.convert(json = item_processed, table_attributes="id=\"info-table\"")
        head = flask.render_template('report_table_head.html',
                                 item_name= item[primary] )
        foot = flask.render_template('report_table_foot.html')                                
        html = html + head + table + foot
    return html

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


@APP.route('/test')
def testing():
    return process()
  

@MSGRAPH.tokengetter
def get_token():
    """Called by flask_oauthlib.client to retrieve current access token."""
    return (flask.session.get('access_token'), '')

if __name__ == '__main__':
    APP.run(host="0.0.0.0",port=5001)
