"""Flask-OAuthlib sample for Microsoft Graph"""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.
import uuid

import flask
from flask_oauthlib.client import OAuth
from flask import session, request, redirect

from json2html import *
import config
import stringcase
from requests import get
from requests_oauthlib import OAuth2Session
from urllib.request import pathname2url
import datetime
from urllib.parse import urlparse


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
apply_prefix = '/apply'

@APP.route('/')
def homepage():
    """Render the home page."""
    return flask.render_template('homepage.html', sample='Flask-OAuthlib')

@APP.route('/login')
def login():
    """Prompt user to authenticate."""
    flask.session['state'] = str(uuid.uuid4())
    if urlparse(request.headers.get("Referer")).netloc == urlparse(config.REDIRECT_URI).netloc:
        flask.session['referrer'] = request.headers.get("Referer")
    else:
        flask.session['referrer'] = urlparse(config.REDIRECT_URI).netloc
    return MSGRAPH.authorize(callback=config.REDIRECT_URI, state=flask.session['state'])

@APP.route('/login/authorized')
def authorized():
    """Handler for the application's Redirect Uri."""
    if str(flask.session['state']) != str(flask.request.args['state']):
        raise Exception('state returned to redirect URL does not match!')
    response = MSGRAPH.authorized_response()
    flask.session['access_token'] = response['access_token']
    print('---token: ' + response['access_token'])
    return flask.redirect('/audit')

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
    html_top = '<div class="container">'
    html_bottom = '</div>'
    section_html = '<h2>' + stringcase.titlecase(section_title) + '</h2>'
    # configs = data[section_title]
    html_content = ''
    code = 200
    for content_data in data[section_title]:
            # html_content = html_content + content_title['name']
            content_html, code_out = content(section_title, content_data)
            if code_out != 200: code = code_out
            html_content = html_content + content_html
    return html_top + section_html + html_content + html_bottom, code

def content(section_title, content_data):
    api_name = content_data['name']
    if section_title == 'general':
        apiCall = api_name
    else:
        apiCall = section_title + '/' + api_name

    section_html = '<h3>' + stringcase.titlecase(api_name) + ' [' + apiCall + ']</h3>'

    # section_html = section_html + ' [' + apiCall + ']'
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
    all_results = []
    configuration_details = np.empty([1,5])

    all_configs, configuration_details = get_baseline(api, primary, configuration_details)
     
    if result.get('value'):
        for item in result['value']:
            item_processed = dict(item.items())
            trimmed = item_processed
            if item.get(primary):
                all_results.append(item[primary])
                link = '<a href=/download/msGraph/' + api + '?id=' + str(item['id']) + '&type=api&name=' + pathname2url(item[primary]) + '&primary=' + primary + '><i class="fas fa-cloud-download-alt"></i>Download</a>'
                configuration_details = np.append(configuration_details, [[str(item[primary]), str(item['id']), 'api', 'tbd' ,link]], axis = 0)
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

            

            compared_table, existing_policy, compliant = check_existing(trimmed.items(), endpoint, item[primary], primary)
            print('---------------------------' + item[primary] + '----------------------')
            print(trimmed.items())
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
            # trimmed = trim_values(item_processed)
            # convert the json to a table
            # table = json2html.convert(json = trimmed, table_attributes="class=\"leftheader-table\"")
            # table = json2html.convert(json = compared_table, table_attributes="class=\"leftheader-table\"")
            table = compared_table.to_html(index=False)
            table = table.replace(okstr, okstr_new)
            table = table.replace(errorstr, errorstr_new)
            
            # process the @type bit
            item_name = item[primary]
            if item.get('@odata.type'):
                item_type = item['@odata.type'].replace('#microsoft.graph.','')
                item_name = '[' + stringcase.sentencecase(item_type) + '] ' + item_name

            # write the table header with the primary key (usually displayName) as the title
            table_head = flask.render_template('report_table_head.html',
                                    download_link=api + '?id=' + item['id'] + '&name=' +item[primary] + '&primary=' + primary, 
                                    compliant=compliant,
                                    reapply_hidden=hide_reapply,
                                    item_name=item_name )
            table_foot = flask.render_template('report_table_foot.html')
            html = html + table_head + table + table_foot
    else:
        if result.get('error'):
            if result['error']['code']:
                result = result['error']['code']
        # table_head = flask.render_template('report_table_head.html',
        #                             powershell='',
        #                             item_name='No Data' )
        # table_foot = flask.render_template('report_table_foot.html') 
        # html = html + table_head  + table_foot
        if result == 'InvalidAuthenticationToken':
            code = 403

    
    missing_config = (set(all_results).difference(all_configs))
    missing_in_api = (set(all_configs).difference(all_results))
    header = ['Name', 'ID', 'Location', 'Missing', 'Action']
    
    configuration_details = np.delete(configuration_details, 0, axis=0)
    df = pd.DataFrame(configuration_details,index=configuration_details[:, 0], columns=header)
    for item in missing_config:
        df.loc[(df['Name'] == item) & (df['Location'] == 'api'),'Missing'] = 'True'
    for item in missing_in_api:
        df.loc[(df['Name'] == item) & (df['Location'] == 'baseline'),'Missing'] = 'True'

    # remove everything else
    df = df[df.Missing != 'tbd']
    df = df.drop('ID', axis=1)
    df = df.drop('Location', axis=1)
    df = df.drop('Missing', axis=1)
    # prints the missing and additional elements in list2  
    print("[|" + str(len(missing_in_api)) + "]Missing settings in API:" + str(missing_in_api) ) 
    print("[|" + str(len(missing_config)) + "]Additional settings in API (not in baseline):" + str(missing_config))

    if len(missing_in_api) > 0:
        html = html + '<button type="button" class="collapsible"><i class="fa fa-exclamation-triangle"></i>Missing Configuration<i class="fa fa-eye"></i></button><div class="content">' + df.to_html(index=False,escape=False) + '</div>'
        # html = html + '<h5>Missing Configuration</h5><p>Configuration that is in the saved baseline, but is not applied to the live environment</p>' + df.to_html(index=False,escape=False)

    return html, code

def get_baseline(api, primary, configuration_details):
    all_configs = []
    path = 'config/msGraph/' + api
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                with open(entry, 'r') as f:
                    parsed_json = json.load(f)
                    all_configs.append(parsed_json[primary])
                    link = '<a href=/post/msGraph/' + api + '?id=' + pathname2url(str(entry.name)) + '&type=baseline><i class="fas fa-angle-double-up"></i>Apply</a>'
                    configuration_details = np.append(configuration_details, [[str(parsed_json[primary]), str(entry.name), 'baseline', 'tbd' , link]], axis = 0)
    except FileNotFoundError:
        print('file not found' + path)
    return all_configs, configuration_details
def getfile(file):
    try:
        with open(file, 'r') as f:
            parsed_json = json.load(f)
            return parsed_json
    except FileNotFoundError:
        return "{'error': 'file not found'}"

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

def find_file_by_name(api, name, primary):
    path = 'config/msGraph/' + api
    rreturn = ''
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                with open(entry, 'r') as f:
                    parsed_json = json.load(f)
                    if parsed_json[primary] == name:
                        rreturn = f.name
    except FileNotFoundError:
        print('file not found' + path)
    return rreturn




def check_existing(table, api, name, primary):
    # load template
    path = find_file_by_name(api, name, primary)
    compliant = True
    try:
        # f=open(path,"r")
        with open(path, 'r') as f:
            parsed_json = json.load(f)
        a = np.empty([1,3])
        header = ['Setting', 'Value', 'Baseline']
        for key, value in table:
            if key in parsed_json:
                if str(value).lower() == str(parsed_json[key]).lower():
                    good = 'OK'
                elif value == True and parsed_json[key] == True:
                    good = 'OK'
                elif value == False and parsed_json[key] == False:
                    good = 'OK'
                else:
                    print(parsed_json[key])
                    good = 'Error'
                    compliant = False
            else:
                good = 'Error'
                compliant = False
            a = np.append(a, [[str(key), str(value), good ]], axis = 0)

        a = np.delete(a, 0, axis=0)
        df = pd.DataFrame(a,index=a[:, 0], columns=header)
        df.set_index(df.columns[0])
        existing = True
    except FileNotFoundError:
        a = np.empty([1,2])
        header = ['Setting', 'Value']
        for key, value in table:
            a = np.append(a, [[str(key), str(value)]], axis = 0)
        a = np.delete(a, 0, axis=0) # delete the empty first row
        df = pd.DataFrame(a, columns=header)
        existing = False
        compliant = False
    return df, existing, compliant

def missing_in_api_table(api, missing_in_api):
    a = np.empty([1,2])
    header = ['Setting', 'Action']
    for item in missing_in_api:
        url = '<a href=/apply_missing__api/' + stringcase.alphanumcase(item) + '> Apply </a>'
        a = np.append(a, [[str(item), str(url) ]], axis = 0)
    a = np.delete(a, 0, axis=0)
    df = pd.DataFrame(a,index=a[:, 0], columns=header)
    df.set_index(df.columns[0])    
    return df




def trim_values(item_processed):
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
    headers = {'SdkVersion': 'ms365-documentation',
               'x-client-SKU': 'ms365-documentation',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    return MSGRAPH.get(endpoint, headers=headers).data

@APP.route('/download/msGraph/<path:path>')
def download(path):
    endpoint = path
    headers = {'SdkVersion': 'ms365-documentation',
               'x-client-SKU': 'ms365-documentation',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    graph = MSGRAPH.get(endpoint, headers=headers).data
    error = "{'error': {'code': 'invalidParams','message': 'Invalid Parameters passed to download API','innerError': {'request-id': 'TBD','date': '" + str(datetime.datetime.now()) +"'} } }"
    if flask.request.args.get('name') and flask.request.args.get('id'):    
        filename = 'config/msGraph/' + path + '/' + flask.request.args.get('name').replace(' ','') + '.json'
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
    headers = {'SdkVersion': 'ms365-documentation',
               'x-client-SKU': 'ms365-documentation',
               'Content-type': 'application/json',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    error = "{'error': {'code': 'invalidParams','message': 'Invalid Parameters passed to download API','innerError': {'request-id': 'TBD','date': '" + str(datetime.datetime.now()) +"'} } }"
    if flask.request.args.get('name') and flask.request.args.get('id') and flask.request.args.get('primary'):
        data, existing = generate_replacement_json(flask.request.args.get('id'), path, flask.request.args.get('name'),flask.request.args.get('primary'))
        if existing == True:
            endpoint = endpoint + '/' + flask.request.args.get('id')
            print(json.dumps(data))
            resp = MSGRAPH.patch(endpoint, headers=headers, data=data, format='json')
            print('-----')
            print(str(resp.status))
            if resp.status == 200 or resp.status == 201 or resp.status == 204:
                msg = 'Successfully updated policy.'
                error = ''
            else:
                msg = 'Error updatging policy via ' + endpoint
                error = str(resp.data)
            return flask.render_template('redirect.html',
                                    message=msg,
                                    location=flask.request.referrer,
                                    error=error,
                                    data=str(data))
    else:
        return error    


    
@APP.route('/post/msGraph/<path:path>') # reapply from the template
def post_create(path):
    endpoint = path
    headers = {'SdkVersion': 'ms365-documentation',
               'x-client-SKU': 'ms365-documentation',
               'Content-type': 'application/json',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    error = "{'error': {'code': 'invalidParams','message': 'Invalid Parameters passed to download API','innerError': {'request-id': 'TBD','date': '" + str(datetime.datetime.now()) +"'} } }"
    if flask.request.args.get('type') and flask.request.args.get('id'):
        if flask.request.args.get('type') == 'baseline':
            data = getfile('config/msGraph/' + path + '/' + flask.request.args.get('id'))
            resp = MSGRAPH.post(endpoint, headers=headers, data=data, format='json')
            
            print(str(resp.status))
            if resp.status == 200 or resp.status == 201 or resp.status == 204:
                msg = 'Successfully updated policy.'
                error = ''
                noerror = True
            else:
                msg = 'Error updatging policy via ' + endpoint
                error = str(resp.data)
                noerror = False
            return flask.render_template('redirect.html',
                                    message=msg,
                                    noError=noerror,
                                    location=flask.request.referrer,
                                    error=error,
                                    data=str(data))
        else:
            return error
    else:
        return error    


def generate_replacement_json(existing_id, api, name, primary):

    path = find_file_by_name(api, name, primary)
    # load template
    # path = 'config/msGraph/' + api + '/' + name
    jsonpolicy = ''
    try:
        with open(path, 'r') as f:
            parsed_json = json.load(f)
        existing = True
        parsed_json['id'] = existing_id
        # del parsed_json['@odata.type']
        # del parsed_json['id']
        jsonpolicy = parsed_json
    except FileNotFoundError:
        existing = False
    return jsonpolicy, existing


@APP.route('/deviceManagement/deviceConfigurations')
def deviceManagement_deviceConfigurations():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = 'me'
    endpoint = 'deviceManagement/deviceConfigurations'
    headers = {'SdkVersion': 'ms365-documentation',
               'x-client-SKU': 'ms365-documentation',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    return MSGRAPH.get(endpoint, headers=headers).data
    
@APP.route('/me')
def me():
    """Confirm user authentication by calling Graph and displaying some data."""
    endpoint = 'me'
    headers = {'SdkVersion': 'ms365-documentation',
               'x-client-SKU': 'ms365-documentation',
               'client-request-id': str(uuid.uuid4()),
               'return-client-request-id': 'true'}
    return MSGRAPH.get(endpoint, headers=headers).data
    


@APP.route('/audit')
def process_audit():
    return process()
  

@MSGRAPH.tokengetter
def get_token():
    """Called by flask_oauthlib.client to retrieve current access token."""
    return (flask.session.get('access_token'), '')

if __name__ == '__main__':
    APP.run(host="0.0.0.0",port=5002)
