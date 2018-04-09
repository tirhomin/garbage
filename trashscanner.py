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
    print('emptying bin')
    
    pass

@app.route('/settings', methods=['POST'])
def settings():
    print('updating settings')
    print(request.form['threshpct'])
    print(request.form['transiencetime'])
    return 'OK'

@app.route('/clearcache')
def clearcache():
    for user in USERS:
        if time.time() - USERS[user]['lastupdate'] > (60*2):
            USERS[user]['emptybinframe'] = None
            USERS[user]['prevframe'] = None
            USERS[user]['curframe'] = None           

def session_setup():
    if not 'guid' in session or not session['guid'] in USERS:
        #ensure user has an ID and that server has a copy of this ID
        session['guid'] = uuid.uuid4()
        USERS[session['guid']] = {'emptybinframe':None,'prevframe':None,'curframe':None,
            'threshpct':2,'lastupdate':0,
            'transiencetime':5,'lastchange':0,'lastdelta':0}


@app.route("/")
def home():
    '''main page / Web UI for webcam'''
    session.clear() #debug
    session_setup()
    #where lastupdate is the last time the frame was updated,
    #lastchange is the last time the frame delta changed
    #totaldelta is the current total delta
    #transience secs is the amount of time to allow transient objects, i.e. people, into the frame
    
    #so in simple terms, the algorithm should detect trash if the following is true:
    "if totaldelta > detection-thresh-pct and lastchange > transience-secs"

    return render_template('main.html')

@app.route("/data", methods = ['GET', 'POST'])
def data():
    '''accept AJAX request containing webcam image, respond with processed image'''
    #process that image
    session_setup()
    if True:#try:
        for f,fo in request.files.items():
            #print('RF:', f, request.files[f])
            #decode base64 jpeg from client request, convert to PIL Image
            x = Image.open(io.BytesIO(base64.b64decode(fo.read())))
        
            userid = session['guid']
            #print(USERS)
            USERS[userid]['lastupdate'] = time.time()

            if USERS[userid]['emptybinframe']==None:
                USERS[userid]['emptybinframe'] = x
            elif USERS[userid]['curframe']:
                USERS[userid]['prevframe'] = USERS[userid]['curframe']
                USERS[userid]['curframe'] = x
            else:
                USERS[userid]['curframe'] = x
            newimg = x


            lastdelta = USERS[userid]['lastdelta']
            if USERS[userid]['curframe']:
                i1 = USERS[userid]['emptybinframe']#USERS[userid]['prevframe']
                i2 = USERS[userid]['curframe']
                i1 = load_image_into_numpy_array(i1)
                i2 = load_image_into_numpy_array(i2)

                lastchange = USERS[userid]['lastchange']
                threshpct = USERS[userid]['threshpct']
                transiencetime = USERS[userid]['transiencetime']
                lastdelta = USERS[userid]['lastdelta']                
                timg, newimg, lastdelta = cvlib.compare_images(i1,i2,lastchange,lastdelta,threshpct,transiencetime)
            
            #if over thresh start a counter, when thresh has exceeded for n seconds then flag full
            if lastdelta > USERS[userid]['lastdelta']:
                USERS[userid]['lastchange'] = time.time()
                USERS[userid]['lastdelta'] = lastdelta

            #print('---->',type(newimg))
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
    if False:#except Exception as e:
        print('error',e)
        return 'error occurred'
    return 'no webcam image provided'

@app.route('/testroute')
def testroute():
    return 'test route returned OK'
#debug server which auto-reloads for live changes during development
#app.run(debug=True, port=8080, host='0.0.0.0')
@werkzeug.serving.run_with_reloader
def serve():
    server = WSGIServer(("0.0.0.0", 8080), app)
    server.serve_forever()
