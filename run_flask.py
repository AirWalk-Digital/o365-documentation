"""Flask-OAuthlib sample for Microsoft Graph"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import uuid

import flask
from flask_oauthlib.client import OAuth
from json2html import *
import config
import stringcase
from requests import get
from requests_oauthlib import OAuth2Session


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
    return flask.redirect('/test')

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
    code = 0
    with open("o365.yml", 'r') as yaml_in:
        # data = json.dumps(yaml.load(yaml_in))
        global data
        data = json.loads(json.dumps(yaml.load(yaml_in)))
        for section_title in data.keys():
            content_new, code = section(section_title)
            content = content + content_new
    html = html + content + footer
    if code == 403:
        return flask.redirect('/login')
    else:
        return html
    
def section(section_title):
    section_html = '<h2>' + stringcase.titlecase(section_title) + '</h2>'
    # configs = data[section_title]
    html_content = ''
    code = 200
    for content_data in data[section_title]:
            # html_content = html_content + content_title['name']
            content_html, code_out = content(section_title, content_data)
            if code_out != 200: code = code_out
            html_content = html_content + content_html
    return section_html + html_content, code

def content(section_title, content_data):
    api_name = content_data['name']
    section_html = '<h3>' + stringcase.titlecase(api_name) + '</h3>'
    if section_title == 'general':
        apiCall = api_name
    else:
        apiCall = section_title + '/' + api_name

    section_html = section_html + '<p> /' + apiCall + '</p>'
    # configs = data[section_title]
    # configuration(api_name, content_data)
    # return section_html
    content, code = configuration(apiCall, content_data)
    return section_html + content, code
    # return section_html + str(get_api(apiCall))

def configuration2(api, content_data):
    endpoint = api
    html = ''
    primary = content_data['primary']
    try:
        result = get_api(endpoint)
        if result.get('value'):
            for item in get_api(endpoint)['value']:
                item_processed = dict(sorted(item.items()))
                for remove_item in content_data['exclude']:
                    # If key exist in dictionary then delete it using del.
                    if remove_item in item_processed:
                        del item_processed[remove_item]
                # remove None, NotConfigured and blank items
                trimmed = item_processed
                for key, value in item_processed.copy().items():
                    if str(value) == 'None':
                        del trimmed[key]
                    elif str(value) == 'notConfigured':
                        del trimmed[key]
                    elif str(value) == '':
                        del trimmed[key]
                    elif str(value) is None:
                        del trimmed[key]
                    elif str(value) == '[]':
                        del trimmed[key]

            table = json2html.convert(json = trimmed, table_attributes="class=\"leftheader-table\"")
            cmd = ''
            if 'powershell' in content_data:
                cmd = generate_powershell(content_data['powershell'], trimmed )

            head = flask.render_template('report_table_head.html',
                                    powershell=cmd,
                                    item_name= item[primary] )
            foot = flask.render_template('report_table_foot.html')                                
            html = html + head + table + foot
            pass
    except TypeError as identifier:
        html = str(identifier) + str(get_api(endpoint))
    except KeyError as identifier:
        html = str(identifier) + str(get_api(endpoint))
    return html



def configuration(api, content_data):
    endpoint = api
    html = ''
    code = 200
    primary = content_data['primary']
    result = get_api(endpoint)
     
    if result.get('value'):
        for item in result['value']:
            # write the table header with the primary key (usually displayName) as the title
            table_head = flask.render_template('report_table_head.html',
                                    powershell='',
                                    item_name=item[primary] )
            table_foot = flask.render_template('report_table_foot.html') 
            item_processed = dict(sorted(item.items()))
            # remove any key from the 'exclude' section in the config
            if content_data.get('exclude'):
                for remove_item in content_data['exclude']:
                    # If key exist in dictionary then delete it using del.
                    if remove_item in item_processed:
                        del item_processed[remove_item]    
            # trim any null, None or empty values
            trimmed = trim_vaules(item_processed)
            # convert the json to a table
            table = json2html.convert(json = trimmed, table_attributes="class=\"leftheader-table\"")

            html = html + table_head + table + table_foot
    else:
        if result.get('error'):
            if result['error']['code']:
                result = result['error']['code']
        table_head = flask.render_template('report_table_head.html',
                                    powershell='',
                                    item_name='Bad Structure' )
        table_foot = flask.render_template('report_table_foot.html') 
        html = html + table_head + str(result) + table_foot
        if result == 'InvalidAuthenticationToken':
            code = 403

    
    return html, code

# def get_api_old(api):
#     endpoint = api
#     headers = {'SdkVersion': 'sample-python-flask',
#                'x-client-SKU': 'sample-python-flask',
#                'client-request-id': str(uuid.uuid4()),
#                'return-client-request-id': 'true'}
#     graphdata = MSGRAPH.get(endpoint, headers=headers).data
#     return graphdata

def trim_vaules(item_processed):
    trimmed = item_processed
    for key, value in item_processed.copy().items():
        if str(value) == 'None':
            del trimmed[key]
        elif str(value) == 'notConfigured':
            del trimmed[key]
        elif str(value) == '':
            del trimmed[key]
        elif str(value) is None:
            del trimmed[key]
        elif str(value) == '[]':
            del trimmed[key]
    return trimmed

def get_api(api):
    if api.startswith("general/"):
        api = api.replace("general/", "")
    return proxy(api)


def generate_powershell_old(powershell, item_processed ):
    # cmd = powershell
    cmd = "$hashtable = @{"
    for key, value in item_processed.items():
        if str(value) != 'None':
            if str(value) == 'True':
                cmd = cmd + key + " = '$True'\n"   
            elif str(value) == 'False':
                cmd = cmd + key + " = '$False'\n"  
            else:
                cmd = cmd + key + " = '" + str(value) + "'\n"

    cmd = cmd + "}\n" + powershell + " $hashtable"
    return cmd

def generate_powershell(powershell, item_processed ):
    # cmd = powershell
    cmd = powershell + " "
    for key, value in item_processed.items():
        if str(value) != 'None':
            if str(value) == 'True':
                cmd = cmd + "-" + key + " $True "   
            elif str(value) == 'False':
                cmd = cmd + "-" + key + " $False "  
            else:
                cmd = cmd + "-" + key + " '" + str(value) + "'"
    # return cmd
    return ''


@APP.route('/', defaults={'path': ''})
@APP.route('/msGraph/<path:path>')
def proxy(path):
    endpoint = path
    headers = {'SdkVersion': 'sample-python-flask',
               'x-client-SKU': 'sample-python-flask',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    return MSGRAPH.get(endpoint, headers=headers).data



@APP.route('/deviceManagement/deviceConfigurations')
def deviceManagement_deviceConfigurations():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = 'me'
    endpoint = 'deviceManagement/deviceConfigurations'
    headers = {'SdkVersion': 'sample-python-flask',
               'x-client-SKU': 'sample-python-flask',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    return MSGRAPH.get(endpoint, headers=headers).data
    

@APP.route('/test')
def testing():
    return process()
  

@MSGRAPH.tokengetter
def get_token():
    """Called by flask_oauthlib.client to retrieve current access token."""
    return (flask.session.get('access_token'), '')

if __name__ == '__main__':
    APP.run(host="0.0.0.0",port=5001)
