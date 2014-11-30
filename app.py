import os
from urlparse import urlsplit, urlunsplit
import tempfile
from subprocess import check_output
import json

import urllib
from flask import Flask, redirect, render_template, request, session
from mendeley import Mendeley
from mendeley.session import MendeleySession
from werkzeug.contrib.fixers import ProxyFix
from flask_sslify import SSLify

import wrapper
import codecs

import jinja_filters

#import ssl
#print dir(ssl)
#ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
#ssl_context.load_cert_chain('ssl-bundle.crt', 'easyskim.key')
from OpenSSL import SSL
ssl_context = SSL.Context(SSL.SSLv23_METHOD)
ssl_context.use_privatekey_file('easyskim.key')
ssl_context.use_certificate_file('easyskim.crt')


client_id = os.environ['MENDELEY_CLIENT_ID']
client_secret = os.environ['MENDELEY_CLIENT_SECRET']

app = Flask(__name__)
sslify = SSLify(app)
app.jinja_env.filters['authors'] = jinja_filters.authors
app.debug = True
app.secret_key = client_secret
app.wsgi_app = ProxyFix(app.wsgi_app)


@app.route('/')
def login():
    if 'token' in session:
        return redirect('/home')

    mendeley = get_mendeley_config()
    auth = mendeley.start_authorization_code_flow()

    session['state'] = auth.state

    return render_template('login.html', login_url=(auth.get_login_url()))


@app.route('/oauth')
def oauth():
    mendeley = get_mendeley_config()
    auth = mendeley.start_authorization_code_flow(state=session['state'])
    mendeley_session = auth.authenticate(request.url)

    session.clear()
    session['token'] = mendeley_session.token

    return redirect('/home')


@app.route('/home')
def home():
    if 'token' not in session:
        return redirect('/')

    mendeley_session = get_session_from_cookies()

    name = mendeley_session.profiles.me.display_name
    docs = []
    for document in mendeley_session.documents.iter():
        docs.append(
            {
                'title': document.title,
                'id': document.id,
                'names': ['%s, %s' % (x.last_name, x.first_name) for x in document.authors]
            })

    # print convertToTxt(getPdf(mendeley_session, docs[0]['id']))

    context = {
        'name' : mendeley_session.profiles.me.display_name,
        'docs': docs[:5]
    }

    return render_template('home.html', **context)

@app.route('/document', methods=['POST'])
def document():
    if 'token' not in session:
        return json.dumps({ "error": "not logged in" }), 500

    mendeley_session = get_session_from_cookies()

    doc_id = request.form['doc_id']
    raw_text, _ = convertToTxt(getPdf(mendeley_session, doc_id))
    text = wrapper.textChanger(textToEncoded(raw_text))
    # info = getInfo(mendeley_session, doc_id)
    final_text = '<pre>%s</pre>' % text
    return json.dumps({ "text": final_text }), 200

@app.route('/static/<path:path>')
def static_proxy(path):
    # send_static_file will guess the correct MIME type
    return app.send_static_file(os.path.join('static', path))

@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect('/')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] == 'pdf'

@app.route('/uploaded', methods=['POST'])
def uploaded_file():
    temp = request.files['file']
    if temp and allowed_file(temp.filename):
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(temp.stream.read())
        f.close()
        raw_text, metadata = convertToTxt(f)
        text = wrapper.textChanger(textToEncoded(raw_text))
        final_text = '<pre>%s</pre>' % text
        print final_text
        return json.dumps({ "text": final_text, "meta": metadata }), 200
    return json.dumps({ "error": "not valid file" }), 500

def get_mendeley_config():
    scheme, netloc, path, query_string, fragment = urlsplit(request.url)
    redirect_url = urlunsplit((scheme, netloc, '/oauth', '', ''))

    return Mendeley(client_id, client_secret, redirect_url)

def get_session_from_cookies():
    return MendeleySession(get_mendeley_config(), session['token'])

# def getInfo(session, doc_id):
#     """Get info from Mendeley document id
#     Returns info dict
#     """
#     doc = session.documents.get(doc_id)

#     doc_url = doc.files.list().items[0].download_url

#     f = tempfile.NamedTemporaryFile(delete=False)
#     f.write(urllib.urlopen(doc_url).read())
#     f.close()

#     return f

def getPdf(session, doc_id):
    """Get pdf from Mendeley document id
    Returns temp pdf object
    """
    doc = session.documents.get(doc_id)

    doc_url = doc.files.list().items[0].download_url

    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(urllib.urlopen(doc_url).read())
    f.close()

    return f

def convertToTxt(pdf):
    """convert PDF (file object) to text, returns text"""
    # text = check_output(["pdftotext", pdf.name, "-"])
    text = check_output(["sh", "parseocr.sh", pdf.name])
    with open(pdf.name+'.met') as f:
        metadata = f.read()
    os.unlink(pdf.name)
    name = pdf.name
    os.unlink(name+'.met')
    return (text, metadata)

def textToEncoded(text):

    with tempfile.NamedTemporaryFile() as temp:
        temp.write(text)
        clean = codecs.open(temp.name,encoding="utf-8").read()

    return clean

if __name__ == '__main__':
    app.run(host='127.0.0.1', port='5000', debug=False, ssl_context=ssl_context)
    #app.run()
