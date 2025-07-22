import datetime
from overlay import OverlayWindow, QApp

for i in range(1):
    print('hello', i)

    with open('bliss.jpg', 'rb') as f:
        b = f.read()
        overlay = OverlayWindow(b)
        overlay.show()
        before = datetime.datetime.now()
        QApp.exec()
        after = datetime.datetime.now()
        diff = after - before
        print(diff)

    print('dello', i)