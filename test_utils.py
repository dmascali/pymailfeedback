from pymailfeedback import sendbeacon
import time

def func_that_does_something():
    start_time = time.time()
    for i in range(0,25):
        print(f"{i} Elapsed time: {time.time()-start_time}")
        sendbeacon(delta_time_minutes=1)
        time.sleep(5)

    return b