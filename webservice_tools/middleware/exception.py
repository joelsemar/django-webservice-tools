from simplejson import dumps
import logging
from webservice_tools import utils
from django.http import HttpResponse
import sys
class WebServiceException():
    """
    Override django's exception mechanism with just the bare minimum
    of what we need, make sure client doesn't receive a bunch of HTML when they are expecting JSON
    """

    def process_exception(self, request, exception):
        return utils.generic_exception_handler(request, exception)
