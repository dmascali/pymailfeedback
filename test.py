from pymailfeedback import sendstatus, sendbeacon, sendmsg
import time

@sendstatus("danielemascali@gmail.com", verbose=2)
def hello(word):
    #sendmsg(subject='subject', message='fdasdfa')
    time.sleep(0)
    print(word)

hello('Hello World')
