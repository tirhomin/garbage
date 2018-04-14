from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer
from flask import g,Flask, request, render_template, session, redirect, send_from_directory
from PIL import Image, ImageOps
import sys, io, base64, numpy, time, uuid, werkzeug.serving
import cv2,cvlib
import numpy as np
app = Flask(__name__, static_url_path='')
app.secret_key = b'\xd3\xdd!\xf3k8\xf0\xd4p+J\xdc\\4\x01^S\x86[Q\xc3\x91I\x1a!BMi]\xcby\xd1'

#use SSL certificate or not
if 'ssl' in sys.argv: SSL = True
else: SSL = False
if 'production' in sys.argv: PRODUCTION = True
else: PRODUCTION = False

USERS = dict()

def load_image_into_numpy_array(image):
    '''convert PIL image data into numpy array for manipulation by TensorFlow'''
    (im_width, im_height) = image.size
    return numpy.array(image.getdata()).reshape((im_height, im_width, 3)).astype(numpy.uint8)

@app.route('/emptybin')
def emptybin():
    '''set current frame as "empty bin" frame'''
    userid = session['guid']
    USERS[userid]['emptybinframe'] = USERS[userid]['curframe']
    return 'emptied'

@app.route('/settings', methods=['POST'])
def settings():
    '''update user settings (provided by HTTP POST from button on web UI)'''
    userid = session['guid']
    USERS[userid]['threshpct'] = float(request.form['threshpct'].strip('%%'))
    USERS[userid]['floorthresh'] = float(request.form['floorthresh'].strip('%%'))
    USERS[userid]['transiencetime'] = float(request.form['transiencetime'])
    return 'settings changed'

@app.route('/clearcache')
def clearcache():
    '''delete old frames for user privacy after 2 minutes of no updates from user camera'''
    for user in USERS:
        if time.time() - USERS[user]['lastupdate'] > (60*2):
            USERS[user]['emptybinframe'] = None
            USERS[user]['curframe'] = None           

def session_setup():
    '''set up user session (server-side frame storage since they wont fit in 4kb client-side session)'''
    if not 'guid' in session or not session['guid'] in USERS:
        #ensure user has an ID and that server has a copy of this ID
        session['guid'] = uuid.uuid4()
        USERS[session['guid']] = {'emptybinframe':None,
            'curframe':None,
            'floorthresh':20,
            'threshpct':2,'lastupdate':0,
            'transiencetime':5,'lastdelta':0,
            'lastempty':time.time()}

@app.route("/")
def home():
    '''main page / Web UI for webcam'''
    #if running on live server, send everyone to SSL
    if PRODUCTION and not SSL:return redirect('https://garbage.tirhomin.com')
    session.clear() #clear session when user refreshes page
    session_setup()
    return render_template('main.html')

@app.route("/data", methods = ['GET', 'POST'])
def data():
    '''accept image from user webcam for processing,
    user will send frame to this function from an AJAX call'''
    session_setup()
    userid = session['guid']
    if 1:#try:
        for f,fo in request.files.items():
            t1=time.time()
            #decode base64 jpeg from client request
            fr=io.BytesIO(base64.b64decode(fo.read()))
            image = np.asarray(bytearray(fr.read()), dtype="uint8")
            cameraframe = cv2.imdecode(image, cv2.IMREAD_COLOR)

            USERS[userid]['lastupdate'] = time.time()
            USERS[userid]['curframe'] = cameraframe

            if type(USERS[userid]['emptybinframe'])==type(None):
                USERS[userid]['emptybinframe'] = cameraframe#load_image_into_numpy_array(cameraframe)

            #prepare images for processing
            i1 = USERS[userid]['emptybinframe']
            i2 = cameraframe#load_image_into_numpy_array(USERS[userid]['curframe'])

            lastdelta = USERS[userid]['lastdelta']
            threshpct = USERS[userid]['threshpct']
            floorthresh = USERS[userid]['floorthresh']
            transiencetime = USERS[userid]['transiencetime']
            lastempty = USERS[userid]['lastempty']         

            #check if frame has not changed for some time 
            #(i.e. there is no one walking about in the frame)
            if (time.time()-lastempty) > transiencetime:
                #bin has been full for longer than threshold time
                #indicating the fullness is not a transient object
                timesup = True
            else:
                timesup = False
            
            #check whether bin is full (output image will be automatically labelled, see cvlib)
            timg, newimg, lastdelta = cvlib.compare_images(i1,i2,threshpct,timesup,floorthresh)
            if lastdelta < threshpct:
                #bin is not full yet, but may have been full in a previous frame
                #due to a transient object -- reset the counter so we know
                #when the bin has been full for longer than the threshold time, 
                #accounting for transient objects by discarding them by resetting the timer
                USERS[userid]['lastempty'] = time.time()

            newimg = Image.fromarray(numpy.uint8(timg)).convert('RGB')
            out = io.BytesIO()
            newimg.save(out,format='jpeg')
            
            #convert to base64 to respond to client 
            data=out.getvalue()
            out.close()
            data = base64.b64encode(data)

            #add data type so the browser can simply render the base64 data as an image on a canvas
            imdata="data:image/jpeg;base64,"+data.decode('ascii')
            t2=time.time()-t1
            print('TIME:',t2)
            return imdata

    else:#except Exception as e:
        print('error',e)
        return 'error occurred'
    return 'no webcam image provided'

@app.route('/static/<path:path>')
@app.route('/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@werkzeug.serving.run_with_reloader
def serve():
    if SSL:
        #/etc/letsencrypt/live/garbage.tirhomin.com/fullchain.pem'
        print('running with SSL')
        srv = WSGIServer(('0.0.0.0', 8081), app,
                            certfile='fullchain.pem',
                            keyfile='privkey.pem')
        srv.serve_forever()
    else:
        print('running without SSL')
        srv = WSGIServer(('0.0.0.0', 8080), app)
        srv.serve_forever()
