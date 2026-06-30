import functools
import http.server

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=__file__.rsplit("/", 1)[0])
http.server.test(HandlerClass=handler, port=5500)
