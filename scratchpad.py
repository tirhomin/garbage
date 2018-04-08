'''
notes:
    basic algorithm:
        original frame is "empty bin"
        we then monitor new frames to see whether they are above some threshold
        (for example, if 4% of the frame changes, there is now enough rubbish to consider the bin "full")
        but we also check to make sure the delta is above a threshold for some period of time
        i.e. that the frame has not changed simply due to a transient object entering the view,
        e.g. a person walking into the frame to throw away some rubbish and leaving again.


    plans:
        make thresholds user-selectable in the UI as well as making the transience-time selectable
'''
import numpy as np
import cv2, imutils

def delta_percent(imagesize, deltavalue):
    #return delta as a percentage of total image area
    return deltavalue / (imagesize[0]*imagesize[1]) * 100

def load_image(filename):
    '''load image from file into opencv, scaling down large images'''
    img = cv2.imread(filename,1)
    height, width = img.shape[:2]
    max_height = 480
    max_width = 480

    #scale large images down
    if max_height < height or max_width < width:
        scale = max_height / height
        if max_width/width < scale: scale = max_width / width
        img = cv2.resize(img, None, fx=scale, fy=scale)

    return img

def compare_images(img1, img2):
    '''compare old frame and current frame for changes'''

    #desaturate & blur to ignore camera noise etc
    f1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    f1 = cv2.GaussianBlur(f1, (21, 21), 0)
    f2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    f2 = cv2.GaussianBlur(f2, (21, 21), 0)

    #find the actual difference between frames
    imgdelta = cv2.absdiff(f1, f2)

    #discard minor differences
    thresh = cv2.threshold(imgdelta, 5, 192, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)

    #find contours, perhaps useful for finding contiguous areas of change
    (contourimage, cnts, hierarchy) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    #set to rgb so we can use a colored bounding box
    f2 = cv2.cvtColor(f2,cv2.COLOR_GRAY2BGR)
    print('------')
    tempimg = img2.copy()
    totaldelta = 0
    for c in cnts:
        #find contiguous chanaged areas (contours)        
        dp = delta_percent(f1.shape,cv2.contourArea(c))
        if dp<0.1:
            #ignore tiny differences, probably noise
            continue
        else:
            totaldelta+=dp
        print('deltapercent',dp)

        #highlight detected trash
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(tempimg, (x, y), (x + w, y + h), (0,0,224), 2)

    return tempimg, contourimage, totaldelta#also try return imgdelta or return thresh

def main():
    IMG1 = 'img/bin0.jpg'
    IMG2 = 'img/bin1.jpg'
    IMG3 = 'img/bin11.jpg'
    IMG4 = 'img/bin2.jpg'
    IMG5 = 'img/bin3.jpg'

    img1 = load_image(IMG1)
    img2 = load_image(IMG2)
    img3 = load_image(IMG3)
    img4 = load_image(IMG4)
    img5 = load_image(IMG5)
    id1,delta1,td1 = compare_images(img1,img2)
    id2,delta2,td2 = compare_images(img1,img3)
    id3,delta3,td3 = compare_images(img1,img4)
    id4,delta4,td4 = compare_images(img1,img5)

    print("%.1f, %.1f, %.1f, %.1f" %(td1,td2,td3,td4))
    '''
        cv2.imshow('img1',id1); cv2.moveWindow('img1',0,50)
        cv2.imshow('img2',id2); cv2.moveWindow('img2',480,50)
        cv2.imshow('img3',id3); cv2.moveWindow('img3',480*2,50)
        cv2.imshow('img4',id4); cv2.moveWindow('img4',480*3,50)

        cv2.imshow('delta',delta1); cv2.moveWindow('delta',480*2,50)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    '''

if __name__=="__main__":main()