from functools import wraps
from response_util import ResponseObject
import time

def login_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        response = ResponseObject(dataFormat=kwargs.get('dataFormat', 'json'))
        try:
            request = [a for a in args if hasattr(a, 'user')][0]
        except IndexError:
            return response.send(errors="Login required method called without request object", status=500)
        if request.user.is_authenticated():
            return fn(*args, **kwargs)
        
        return response.send(errors='401 -- Unauthorized', status=401)
    
    return inner



def retry(tries=5, exceptions=None, delay=0.3, exception_raise=None):
    """
    Decorator for retrying a function if exception occurs
        
    tries -- num tries 
    exceptions -- exceptions to catch
    delay -- wait between retries
    taken from https://gist.github.com/728327
    """
    exceptions_ = exceptions or (Exception,)
    def _retry(fn):
        @wraps(fn)
        def __retry(*args, **kwargs):
            for _ in xrange(tries + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions_, e:
                    print "Retry, exception:" + str(e)
                    time.sleep(delay)
            #if no success after tries raise last exception
            if exception_raise:
                raise exception_raise
            else:
                raise
        return __retry
    return _retry
