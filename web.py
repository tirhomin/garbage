from gevent.wsgi import WSGIServer
from flask import Flask, request, render_template, g
from PIL import Image, ImageOps

import io, base64, numpy, threading, werkzeug.serving
import ncvlib, time, uuid
app = Flask(__name__)

FRAMES = {'orig':None,'old':None,'new':None}
USERS = {1:FRAMES}

def load_image_into_numpy_array(image):
    '''convert PIL image data into numpy array for manipulation by TensorFlow'''
    (im_width, im_height) = image.size
    return numpy.array(image.getdata()).reshape((im_height, im_width, 3)).astype(numpy.uint8)

@app.route("/")
def home():
    '''main page / Web UI for webcam'''
    return render_template('main.html')

@app.route("/data", methods = ['GET', 'POST'])
def data():
    '''accept AJAX request containing webcam image, respond with processed image'''
    #process that image
    for f,fo in request.files.items():
        #print('RF:', f, request.files[f])
        #decode base64 jpeg from client request, convert to PIL Image
        x = Image.open(io.BytesIO(base64.b64decode(fo.read())))

        userid = 1
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
            newimg = ncvlib.compare_images(i1,i2)
        

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
