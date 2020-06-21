from time import time
from contextlib import contextmanager


def get_time(funct):
    def timed_funct(*args, **kwargs):
        with get_time_cm(funct.__name__):
            result = funct(*args, **kwargs)
        return result
    return timed_funct


@contextmanager
def get_time_cm(name):
    bef = time()
    yield
    aft = time()
    print("The section", name, "takes", aft - bef, 'seconds to be executed.')


times = {}
def count_calls(funct):
    def wrapper(*args, **kwargs):
        if times.get(funct.__name__) is not None:
            times[funct.__name__] += 1
        else:
            times[funct.__name__] = 1
        print(times)
        return funct(*args, **kwargs)
    return wrapper


chrono = {}
def cumulated_time(funct):
    def wrapper(*args, **kwargs):
        bef = time()
        result = funct(*args, **kwargs)
        aft = time()
        if chrono.get(funct.__name__) is not None:
            chrono[funct.__name__] += aft - bef
        else:
            chrono[funct.__name__] = aft - bef
        print(chrono)
        return result
    return wrapper
