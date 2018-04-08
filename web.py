from gevent.wsgi import WSGIServer
from flask import Flask, request, render_template
from PIL import Image, ImageOps

from queue import LifoQueue, Queue
import io, base64, numpy, threading, werkzeug.serving
import cvlib, time
app = Flask(__name__)

def load_image_into_numpy_array(image):
    '''convert PIL image data into numpy array for manipulation by TensorFlow'''
    (im_width, im_height) = image.size
    return numpy.array(image.getdata()).reshape((im_height, im_width, 3)).astype(numpy.uint8)

def imagehandler(inqueue,outqueue):
    ''' analyze new frame for garbage '''
    while True:
        image_np = inqueue.get()
        output = Image.fromarray(numpy.uint8(image_np)).convert('RGB')
        outqueue.put(output)

#only store up to 3 frames so as not to get overwhelmed, dropped frames are fine
inqueue = Queue(maxsize=3) #queue for frames being sent to the neural net
outqueue = Queue(maxsize=3) #final labelled images to show user

tthread = threading.Thread(target=cvlib.tfworker,args=(inqueue,inqueue))
tthread.daemon = True
tthread.start()

#updatethread is fetching images from input queue, feeding them to tensorflow thread
#and then adding the results to an output queue for return to the client
updatethread = threading.Thread(target=imagehandler,args=(inqueue,outqueue))
updatethread.daemon = True
updatethread.start()  


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

        #convert image to numpy array and insert into tensorflow queue
        arr = load_image_into_numpy_array(x)
        inqueue.put(arr)

        #get the next available processed frame from the output queue
        #note this may not be the image we inserted into the tensorflow queue
        #that image may still be awaiting processing, this image is instead simply
        #the next available one, which may have been processed some milliseconds ago
        quedata = outqueue.get()
        out = io.BytesIO()
        quedata.save(out,format='jpeg')
        
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
