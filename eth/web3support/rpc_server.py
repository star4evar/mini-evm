import json
import traceback
from cgi import parse_header, parse_multipart
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

from eth.chains.base import Chain
from eth.web3support.local import LocalWeb3Provider


class Web3RPCServer:
    def __init__(self, chain: Chain):
        global local_provider
        self.chain = chain

    def start(self, port):
        server_address = ('', port)

        server = HTTPServer(server_address, RequestHandler)
        RequestHandler.local_provider = LocalWeb3Provider(self.chain)

        print("starting server at:", port)
        server.serve_forever()



class RequestHandler(BaseHTTPRequestHandler):
    local_provider = None

    def do_GET(self, *args):
        try:
            handle_request("GET", self, self.local_provider)
        except:
            traceback.print_exc()

    def do_POST(self):
        try:
            handle_request("POST", self, self.local_provider)
        except:
            traceback.print_exc()

    # disable log
    def log_message(self, format, *args):
        return



def handle_request(method, request, local_provider):

    req_info = parse_POST(request)

    print("handle request: ", req_info)
    request.send_response(200)
    request.send_header('Content-type', 'application/json')
    request.end_headers()

    if req_info is None:
        request.wfile.write(b'')
        request.send_response()
    else:
        result = local_provider.make_request(req_info["method"], req_info["params"])
        # print(f"method: {method} result: {result!r}")
        value = json.dumps(result)
        # print("result value:", value)
        request.wfile.write(bytes(value, "utf-8"))



def parse_POST(request):
    ctype, pdict = parse_header(request.headers['content-type'])

    if ctype == 'multipart/form-data':
        postvars = parse_multipart(request.rfile, pdict)
    elif ctype == 'application/x-www-form-urlencoded':
        length = int(request.headers['content-length'])
        postvars = parse_qs(
            request.rfile.read(length),
            keep_blank_values=1)
    elif ctype == 'application/json':
        length = int(request.headers['content-length'])
        content = request.rfile.read(length).decode()
        postvars = None
        try:
            postvars = json.loads(content)
        except:
            # print("content:", content)
            postvars = None
    else:
        postvars = {}

    return postvars