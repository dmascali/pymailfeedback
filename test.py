from pymailfeedback import sendstatus, sendbeacon, sendmsg
import time
from test_utils import func_that_does_something

import os
import sys
print(os.getenv("PYMAIL_SENDER_EMAIL"))
print(os.getenv("PYMAIL_SENDER_PASSWORD"))


@sendstatus(['danielemascali@gmail.com'])
def hello_world(word):
    a = func_that_does_something()
    #sendmsg(subject='subject', message='fdasdfa')
    time.sleep(6)
    print(word)

hello_world('Hello World')
