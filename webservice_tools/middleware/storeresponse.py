from webservice_tools.models import StoredResponse


class StoreResponse(object):
    
    def process_response(self, request, response):
        import pydevd;pydevd.settrace('127.0.0.1')
        if request.META.get('HTTP_STORE_RESPONSE'):
            handler_id = request.META.get('HTTP_HANDLER_ID')
            stored_response = StoredResponse.objects.get_or_create(handler_id=handler_id)[0]
            import pydevd;pydevd.settrace('127.0.0.1')