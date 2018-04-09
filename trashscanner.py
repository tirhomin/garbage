from gevent.wsgi import WSGIServer
from flask import Flask, request, render_template, session
from PIL import Image, ImageOps
import io, base64, numpy, threading, werkzeug.serving
import cvlib, time, uuid
app = Flask(__name__)
app.secret_key = b'\xd3\xdd!\xf3k8\xf0\xd4p+J\xdc\\4\x01^S\x86[Q\xc3\x91I\x1a!BMi]\xcby\xd1'

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
    USERS[userid]['threshpct'] = float(request.form['threshpct'])
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
            'threshpct':2,'lastupdate':0,
            'transiencetime':5,'lastdelta':0,
            'lastempty':time.time()}

@app.route("/")
def home():
    '''main page / Web UI for webcam'''
    session.clear() #clear session when user refreshes page
    session_setup()
    return render_template('main.html')

@app.route("/data", methods = ['GET', 'POST'])
def data():
    '''accept image from user webcam for processing,
    user will send frame to this function from an AJAX call'''
    session_setup()
    userid = session['guid']
    
    try:
        for f,fo in request.files.items():
            #decode base64 jpeg from client request, convert to PIL Image
            cameraframe = Image.open(io.BytesIO(base64.b64decode(fo.read())))       
            USERS[userid]['lastupdate'] = time.time()
            USERS[userid]['curframe'] = cameraframe

            if USERS[userid]['emptybinframe']==None:
                USERS[userid]['emptybinframe'] = cameraframe

            #prepare images for processing
            i1 = load_image_into_numpy_array(USERS[userid]['emptybinframe'])
            i2 = load_image_into_numpy_array(USERS[userid]['curframe'])

            lastdelta = USERS[userid]['lastdelta']
            threshpct = USERS[userid]['threshpct']
            transiencetime = USERS[userid]['transiencetime']
            lastempty = USERS[userid]['lastempty']         

            if (time.time()-lastempty) > transiencetime:
                #bin has been full for longer than threshold time
                #indicating the fullness is not a transient object
                timesup = True
            else:
                timesup = False
            timg, newimg, lastdelta = cvlib.compare_images(i1,i2,threshpct,timesup)
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
            return imdata
    except Exception as e:
        print('error',e)
        return 'error occurred'
    return 'no webcam image provided'

@werkzeug.serving.run_with_reloader
def serve():
    server = WSGIServer(("0.0.0.0", 8080), app)
    server.serve_forever()
