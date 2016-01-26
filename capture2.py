import numpy as np
import cv2, time

cap1 = cv2.VideoCapture(0)
cap2 = cv2.VideoCapture(1)

while(True):
    # Capture frame-by-frame
    ret, frame1 = cap1.read()
    ret, frame2 = cap2.read()

    now = str(int(time.time()))

    cv2.imwrite('im' + now + 'A.png', frame1)
    cv2.imwrite('im' + now + 'B.png', frame2)
    break

    # Our operations on the frame come here
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # Display the resulting frame
    cv2.imshow('frame1',gray1)
    cv2.imshow('frame2',gray2)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap1.release()
#cap2.release()
cv2.destroyAllWindows()
