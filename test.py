from pymailfeedback import sendstatus, sendbeacon, sendmsg
import time
from test_utils import func_that_does_something

import os
print(os.getenv("PYMAIL_SENDER_EMAIL"))       # Dovrebbe stampare la tua mail
print(os.getenv("PYMAIL_SENDER_PASSWORD"))

@sendstatus()
def hello(word):
    #a = func_that_does_something()
    #sendmsg(subject='subject', message='fdasdfa')
    return b
    time.sleep(0)
    print(word)

hello('Hello World')
