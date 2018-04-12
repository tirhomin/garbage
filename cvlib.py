import time, numpy, cv2, imutils

IMG1 = 'bin0.jpg'
IMG2 = 'bin2.jpg'

def delta_percent(imagesize, deltavalue):
    '''return delta as a percentage of total image area'''
    return deltavalue / (imagesize[0]*imagesize[1]) * 100

def scale_image(img):
    '''scaling down large images'''
    height, width = img.shape[:2]
    max_height = 640
    max_width = 640

    #scale large images down
    if max_height < height or max_width < width:
        scale = max_height / height
        if max_width/width < scale: scale = max_width / width
        img = cv2.resize(img, None, fx=scale, fy=scale)

    return img

def compare_images(img1, img2, threshpct=5, timesup=False):
    '''compare old frame and current frame for changes'''

    #desaturate & blur to ignore camera noise etc
    f1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    f1 = cv2.GaussianBlur(f1, (21, 21), 0)
    f2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    f2 = cv2.GaussianBlur(f2, (21, 21), 0)

    #find the actual difference between frames
    imgdelta = cv2.absdiff(f1, f2)

    #discard minor differences in lighting, e.g. a faint shadow, camera noise, etc
    #i.e. difference must be at least 25/255 or ~10%
    thresh = cv2.threshold(imgdelta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)

    #find contours, perhaps useful for finding contiguous areas of change
    (contourimage, cnts, hierarchy) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    #set to rgb so we can use a colored bounding box
    contourimage = cv2.cvtColor(contourimage,cv2.COLOR_GRAY2RGB)
    #image with boxes shown
    boximg = contourimage.copy()
    totaldelta = 0

    for c in cnts:
        #find contiguous chanaged areas (contours)        
        dp = delta_percent(f1.shape,cv2.contourArea(c))
        if dp<0.1:
            #ignore tiny differences, probably noise
            continue
        else:
            totaldelta+=dp

        #highlight detected trash
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(boximg, (x, y), (x + w, y + h), (0,0,224), 2)

    #write bin status on top of frame
    if totaldelta>threshpct and timesup:
        cv2.putText(boximg,"bin full", (5,25), cv2.FONT_HERSHEY_SIMPLEX, 1, color=(255,0,0))
    else:
        cv2.putText(boximg,"bin not full", (5,25), cv2.FONT_HERSHEY_SIMPLEX, 1, color=(0,255,0))

    return boximg, contourimage, totaldelta#also try return imgdelta or return thresh
    