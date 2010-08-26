
from webservice_tools.response_util import ResponseObject
import sys
class WebServiceException():
    """
    Override django's exception mechanism with just the bare minimum
    of what we need, make sure client doesn't receive a bunch of HTML when they are expecting JSON
    """

    def process_exception(self, request, exception):
        
        response = ResponseObject()
        exc_info = sys.exc_info()
        exType, exValue, tb = exc_info
        # we just want the last frame, (the one the exception was thrown from)
        lastframe = self.get_traceback_frames(tb)[-1]
        location = "%s in %s, line: %s" %(lastframe['filename'], lastframe['function'], lastframe['lineno'])
        response.addErrors([exception.message, location])
        return response.send()
    
    
    def get_traceback_frames(self, tb):
        """
        Coax the line number, function data out of the traceback we got from the exc_info() call
        """
        frames = []
        while tb is not None:
            # support for __traceback_hide__ which is used by a few libraries
            # to hide internal frames.
            if tb.tb_frame.f_locals.get('__traceback_hide__'):
                tb = tb.tb_next
                continue
            frames.append({
                'filename': tb.tb_frame.f_code.co_filename,
                'function': tb.tb_frame.f_code.co_name,
                'lineno': tb.tb_lineno,
            })
            tb = tb.tb_next

        if not frames:
            frames = [{
                'filename': '&lt;unknown&gt;',
                'function': '?',
                'lineno': '?',
                'context_line': '???',
            }]

        return frames
