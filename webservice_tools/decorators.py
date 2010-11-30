from functools import wraps
from response_util import ResponseObject

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
