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

import datetime

import yaml
import json
import os
import errno
import numpy as np
import pandas as pd


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
            item_processed = dict(item.items())
            trimmed = item_processed
            #remove any key from the 'exclude' section in the config
            if content_data.get('exclude'):
                for remove_item in content_data['exclude']:
                    # If key exist in dictionary then delete it using del.
                    if remove_item in item_processed:
                        del item_processed[remove_item]    
            # trim any null, None or empty values
    
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

            compared_table, existing_policy = check_existing(trimmed.items(), endpoint, item[primary])

            okstr = '<td>OK</td>'
            okstr_new = '<td bgcolor="#00FF00">OK</td>'
            errorstr = '<td>Error</td>'
            errorstr_new = '<td bgcolor="#FF0000">Error</td>'
            if existing_policy == True:
                hide_reapply = 'block'
            else:
                hide_reapply = 'none'
            # remove any key from the 'exclude' section in the config
            # if content_data.get('exclude'):
            #     for remove_item in content_data['exclude']:
            #         # If key exist in dictionary then delete it using del.
            #         if remove_item in item_processed:
            #             del item_processed[remove_item]    
            # # trim any null, None or empty values
            # trimmed = trim_vaules(item_processed)
            # convert the json to a table
            # table = json2html.convert(json = trimmed, table_attributes="class=\"leftheader-table\"")
            # table = json2html.convert(json = compared_table, table_attributes="class=\"leftheader-table\"")
            table = compared_table.to_html(index=False)
            table = table.replace(okstr, okstr_new)
            table = table.replace(errorstr, errorstr_new)
            if content_data.get('powershell'):
                cmd = generate_powershell(content_data['powershell'], trimmed )
            else:
                cmd = ''
            # write the table header with the primary key (usually displayName) as the title
            table_head = flask.render_template('report_table_head.html',
                                    powershell=cmd,
                                    download_link=api + '?id=' + item['id'] + '&name=' +item[primary] , 
                                    reapply_hidden=hide_reapply,
                                    item_name=item[primary] )
            table_foot = flask.render_template('report_table_foot.html')
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

def trim_policy(item_processed, content_data):
    trimmed = item_processed
    #remove any key from the 'exclude' section in the config
    if content_data.get('exclude'):
        for remove_item in content_data['exclude']:
            # If key exist in dictionary then delete it using del.
            if remove_item in item_processed:
                del item_processed[remove_item]    
    # trim any null, None or empty values

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

def check_existing(table, api, name):
    # load template
    path = 'config/msGraph/' + api + '/' + name
    try:
        # f=open(path,"r")
        with open(path, 'r') as f:
            parsed_json = json.load(f)
        a = np.empty([1,3])
        header = ['Setting', 'Vaule', 'Baseline']
        for key, value in table:
            if str(value) == str(parsed_json[key]):
                good = 'OK'
            else: 
                good = 'Error'
            a = np.append(a, [[str(key), str(value), good ]], axis = 0)

        a = np.delete(a, 0, axis=0)
        df = pd.DataFrame(a,index=a[:, 0], columns=header)
        df.set_index(df.columns[0])
        existing = True
    except FileNotFoundError:
        a = np.empty([1,2])
        header = ['Setting', 'Vaule']
        for key, value in table:
            a = np.append(a, [[str(key), str(value)]], axis = 0)
        a = np.delete(a, 0, axis=0) # delete the empty first row
        df = pd.DataFrame(a, columns=header)
        existing = False
    return df, existing





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
        if str(key) == '@odata.type':
            cmd = cmd + '-' + str(value).replace('#microsoft.graph.', '') + ' '
        elif str(value) != 'None' and str(value) != '' :
            if str(value) == 'True':
                cmd = cmd + " -" + key + " $True"   
            elif str(value) == 'False':
                cmd = cmd + " -" + key + " $False"  
            else:
                cmd = cmd + " -" + key + " '" + str(value) + "'"
    return cmd


@APP.route('/', defaults={'path': ''})
@APP.route('/msGraph/<path:path>')
def proxy(path):
    endpoint = path
    headers = {'SdkVersion': 'sample-python-flask',
               'x-client-SKU': 'sample-python-flask',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    return MSGRAPH.get(endpoint, headers=headers).data

@APP.route('/download/msGraph/<path:path>')
def download(path):
    endpoint = path
    headers = {'SdkVersion': 'sample-python-flask',
               'x-client-SKU': 'sample-python-flask',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    graph = MSGRAPH.get(endpoint, headers=headers).data
    error = "{'error': {'code': 'invalidParams','message': 'Invalid Parameters passed to download API','innerError': {'request-id': 'TBD','date': '" + str(datetime.datetime.now()) +"'} } }"
    if flask.request.args.get('name') and flask.request.args.get('id'):    
        filename = 'config/msGraph/' + path + '/' + flask.request.args.get('name')
        itemtosave = graph['value']
        itemtosave = [itemtosave for itemtosave in itemtosave if itemtosave['id'] == flask.request.args.get('id')][0]
        savefile(filename, itemtosave)
        return flask.render_template('redirect.html',
                                    message='Your file has been saved as ' + filename + '.',
                                    location=flask.request.referrer,
                                    data=str(itemtosave) )
    else:
        return error

def savefile(path, data):
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    with open(path, 'w') as f:
        json.dump(data, f)
    
@APP.route('/reapply/msGraph/<path:path>') # reapply from the template
def reapply(path):
    endpoint = path
    headers = {'SdkVersion': 'sample-python-flask',
               'x-client-SKU': 'sample-python-flask',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    graph = MSGRAPH.get(endpoint, headers=headers).data
    error = "{'error': {'code': 'invalidParams','message': 'Invalid Parameters passed to download API','innerError': {'request-id': 'TBD','date': '" + str(datetime.datetime.now()) +"'} } }"
    if flask.request.args.get('name') and flask.request.args.get('id'):
        data, existing = generate_replacement_json(flask.request.args.get('id'), path, flask.request.args.get('name'))
        if existing == True:
            resp = MSGRAPH.post(endpoint, headers=headers, data=data)
            print('-----')
            print(str(resp.status))
            if resp.status == 200:
                msg = 'Successfully updated policy.'
                error = 'No error'
            else:
                msg = 'Error updatging policy.'
                error = str(resp.data)
            return flask.render_template('redirect.html',
                                    message=msg,
                                    location=flask.request.referrer,
                                    error=error,
                                    data=str(data))
    else:
        return error    

def generate_replacement_json(existing_id, api, name):
    # load template
    path = 'config/msGraph/' + api + '/' + name
    jsonpolicy = ''
    try:
        with open(path, 'r') as f:
            parsed_json = json.load(f)
        existing = True
        parsed_json['id'] = existing_id
        jsonpolicy = parsed_json
    except FileNotFoundError:
        existing = False
    return jsonpolicy, existing


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
