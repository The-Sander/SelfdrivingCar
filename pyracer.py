from gather_data import takeScreens, datastream, DSOutput
# from predict import predict
from threading import Thread
import pyvjoy
import cv2
import time
import settings
from PIL import ImageGrab
import numpy as np
import keyboard
from functools import partial

from fastai.vision.all import *
j = pyvjoy.VJoyDevice(1)
x_max = 32767
def get_x (r): return Path(f"./data/images/{r['img_path']}")
def get_y(r): return [r['steer'], r['accel'], r['brake']]
learn = load_learner('./models/export.pkl')
def crop(img):
    x=0
    w=1600
    y=350
    h=900-350

    return img[y:y+h, x:x+w]
        

def sendInputs(x,z):
    if  x >= 0.51:
        x += 0.2
    elif x<=0.48:
        x -= 0.1
    print(f'X:{x*(x_max+x_max)-x_max} Z {z*512 - 255}')

    j.data.wAxisX = int(x*x_max)
    j.data.wAxisZ=int( (z*x_max) * 2 )

    j.data.wAxisY= int(0)
    #send data to vJoy device
    j.update()


def inputRDP(steer, accel,brake):
    print(f'X:{steer} accel {accel} Brake:{brake}')

    deadzone = 10000
    x_max_dz = x_max - deadzone

    #unnormalizing
    s = steer * 254 - 127
    s_tosend = 0
    if s > 5:
        s_tosend = (s/127) * x_max_dz + deadzone
    elif s < -5:
        s_tosend = ((s*-1)/127  * x_max_dz + deadzone) * -1


    s_tosend = int((s_tosend + x_max) / 2)
    x_half = int(x_max/2)

    
    # translated = s_tosend * 2 - 32767
    a = accel * x_max_dz + deadzone
    b =brake * x_max_dz + deadzone
    if accel <0.3:
        a = 0
    if brake < 0.3:
        b = 0
        


    j.data.wAxisX = int(s_tosend)
    j.data.wAxisZ=int(b)
    j.data.wAxisY= int(a)
    #send data to vJoy device
    j.update()


def resetkey():
    j.data.wAxisX = int(x_max/2)
    j.data.wAxisZ=int(0)
    j.data.wAxisY= int(0)
    #send data to vJoy device
    j.update()



def listenkeys():
    keys = ['left', 'up', 'right']    
    for k in lab_dictkey:
        keys[keys.index(k)] = keyboard.is_pressed(k)
        print("manual steering: "+str(keys))
        
def run(udp):
    settings.init()
    autopilot = False
    recording = False
    showFps = False
    autorecord = False
    last_time = time.time()
    framecounter = 0 

    global dsout

    # print('get ready to bind in 3s')
    # time.sleep(3)
    while settings.run_loops:
        # printscreen = np.array(ImageGrab.grab(bbox=(0, 80, 1024, 700)))
        # resized = cv2.resize(printscreen, (244,244))
        # cv2.imshow('window', cv2.cvtColor(printscreen, cv2.COLOR_BGR2RGB))
     
        resolutionx, resolutiony = (1600,900)
        margin = 40
        printscreen = np.array(ImageGrab.grab(bbox=(0, margin, resolutionx, resolutiony+margin)))
        printscreen = cv2.cvtColor(printscreen, cv2.COLOR_BGR2RGB)
        printscreen = crop(printscreen)
        resized = cv2.resize(printscreen, (480,277))
        smoll = cv2.resize(printscreen, (int(resolutionx/2),int(resolutiony/2)))
        cv2.imshow('window', resized)

        if showFps:
            ##Check fps if needed
            print('loop took {} seconds'.format(time.time()-last_time))
            last_time = time.time()

        if autopilot:
            prediction = learn.predict(resized)
            # print(prediction[0][0], prediction[0][1])
            inputRDP(prediction[0][0], prediction[0][1], prediction[0][2] )
        if recording:
            framecounter+=1
            if framecounter%5==0:
                cv2.imwrite(f'D:/Documenten/Thomasmore/AI/self_driving/data/newdata/images/s_{settings.counter}_image.png', printscreen)
                file = open("./data/newdata/inputs.csv", "a")
                print(f'{settings.counter}_image.png,{udp.steer}, {udp.accel}, {udp.brake}')
                file.write('s_'+str(settings.counter) + "_image.png" + "," + str(udp.speed) + "," + str(udp.steer) + "," + str(udp.accel) + "," + str(udp.brake) + "\n")
                settings.counter+=1
                file.close()


        k = cv2.waitKey(25)
        if  k == ord('g') or keyboard.is_pressed('g'):
            settings.run_loops = False
            cv2.destroyAllWindows()
            break
        elif k == ord('v') or keyboard.is_pressed('v') :
            resetkey()
            recording = False
            autopilot = not autopilot
            print(f'autopilot {autopilot}')
        elif k == ord('f') or keyboard.is_pressed('f'):
            showFps = not showFps
        elif k == ord('r') or keyboard.is_pressed('r'):
            autorecord = not autorecord
            print(f'Autorecord: {autorecord}')
        elif (k == ord('w') or keyboard.is_pressed('w') or keyboard.is_pressed('d') or keyboard.is_pressed('a')) and autorecord : 
            autopilot = False
            if not recording:
                recording = True
                print('Stop autopilot, start recording')
        
if __name__ == '__main__':
    print("Prepare to drive!")
    resetkey()
    dsout = DSOutput()
    t1 = Thread(target = partial(run, dsout))
    t2 = Thread(target = partial(datastream,dsout))
    t1.start()
    t2.start()