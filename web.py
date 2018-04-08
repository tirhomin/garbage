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

@app.route('/clearcache')
def clearcache():
    for user in USERS:
        if time.time() - USERS[user]['lastupdate'] > (60*2):
            USERS[user]['orig'] = None
            USERS[user]['old'] = None
            USERS[user]['new'] = None           

@app.route("/")
def home():
    '''main page / Web UI for webcam'''
    #TODO FIX
    session.clear()
    if not 'guid' in session:
        session['guid'] = uuid.uuid4()
        USERS[session['guid']] = {'orig':None,'old':None,'new':None,
            'detection-thresh-pct':4,'lastupdate':0,
            'transience-secs':10,'lastchange':0,'olddelta':0, 'newdelta':0}

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
    if True:#try:
        for f,fo in request.files.items():
            #print('RF:', f, request.files[f])
            #decode base64 jpeg from client request, convert to PIL Image
            x = Image.open(io.BytesIO(base64.b64decode(fo.read())))
        
            userid = session['guid']
            print(USERS)
            USERS[userid]['lastupdate'] = time.time()

            #
            if USERS[userid]['orig']==None:
                print('stage1')
                USERS[userid]['orig'] = x
            elif USERS[userid]['new']:
                print('stage2')
                USERS[userid]['old'] = USERS[userid]['new']
                USERS[userid]['new'] = x
            else:
                print('stage3')
                USERS[userid]['new'] = x
            newimg = x

            if USERS[userid]['new']:
                print('found new')
                i1 = USERS[userid]['old']
                i2 = USERS[userid]['new']
                i1 = load_image_into_numpy_array(i1)
                i2 = load_image_into_numpy_array(i2)
                #TODO new algorithm compare to orig image every time
                timg, newimg, newdelta = cvlib.compare_images(i1,i2,USERS[userid]['lastchange'])
            
            if newdelta > USERS[userid]['newdelta']:
                USERS[userid]['lastchange'] = time.time()
                USERS[userid]['olddelta'] = USERS[userid]['newdelta']
                USERS[userid]['newdelta'] = newdelta

            print('---->',type(newimg))
            newimg = Image.fromarray(numpy.uint8(newimg)).convert('RGB')
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
