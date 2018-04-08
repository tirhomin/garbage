import time, numpy, cv2
from PIL import Image, ImageOps

def tfworker(inqueue,outqueue):
    ''' fetch video frames from queue and send them to object detector function,
    adding the processed result to the output frames queue, to be displayed to the user'''

    while True:
        time.sleep(1/5) #dont go crazy on the cpu
        frame = inqueue.get()
        output = Image.fromarray(numpy.uint8(frame)).convert('RGB')
        outqueue.put(output)


import numpy as np
import cv2, imutils

IMG1 = 'bin0.jpg'
IMG2 = 'bin2.jpg'

def delta_percent(imagesize, deltavalue):
    #return delta as a percentage of total image area
    return deltavalue / (imagesize[0]*imagesize[1]) * 100

def load_image(img):
    '''load image from file into opencv, scaling down large images'''
    height, width = img.shape[:2]
    max_height = 640
    max_width = 640

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

    for c in cnts:
        #find contiguous chanaged areas (contours)        
        dp = delta_percent(f1.shape,cv2.contourArea(c))
        if dp<0.1:continue #ignore small contours

        #highlight detected trash
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(img2, (x, y), (x + w, y + h), (0,0,224), 2)

    return contourimage #also try return imgdelta or return thresh

def main():
    img1 = load_image(IMG1)
    img2 = load_image(IMG2)
    imgdelta = compare_images(img1,img2)

    cv2.imshow('img1',img1); cv2.moveWindow('img1',0,50)
    cv2.imshow('img2',img2); cv2.moveWindow('img2',640,50)
    cv2.imshow('delta',imgdelta); cv2.moveWindow('delta',1280,50)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__=="__main__":main()