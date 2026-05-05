import socket
import ssl
import certifi
import os
import time

sockets = {}
cache = {}

class URL:
    def __init__(self, url):
        self.parse_url(url)

    def parse_url(self, url):
        # Special Case, handling data urls
        dataScheme = "data:text/html"
        if url.startswith(dataScheme):
            self.scheme = "data"
            _, self.path = url.split(",", 1)
            return
        # Handling View Source
        viewSourceString = "view-source:"
        self.viewSource = False
        if url.startswith("view-source:"):
            _, url = url.split(viewSourceString, 1)
            self.viewSource = True

        # Extract the relevant pieces from the url step by step
        # <scheme://hostname/path>
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file"]

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if self.scheme != "file": 
            if "/" not in url:
                url = url + "/"
            self.host, url = url.split("/", 1)
            self.path = "/" + url
            if ":" in self.host:
                self.host, port = self.host.split(":", 1)
                self.port = int(port)
        else:
            self.path = url


    def cache_content(self, content, response_headers, url):
        cache_control_params = list(map(str.strip, response_headers["cache-control"].split(",")))
        # any header other than max_age, don't
        if len(cache_control_params) == 1:
            if list(cache_control_params)[0].startswith("max-age"):
                max_age = int(list(map(str.strip, list(cache_control_params)[0].split("=", 1)))[1])
                cache[url] = {"content": content, "max_age": max_age, "time": time.time()}

    def internet_request(self, headers=[], redirect_limit=4):
        # using the given url, make an http request to it

        # First check that a cached socket exists
        if self.host in sockets:
            s = sockets[self.host]
        else:
            s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )

        url = self.host + self.path
        if url in cache:
            # Check timestamp against max_age. Make sure it didn't expire
            if (time.time() <= cache[url]["time"] + cache[url]["max_age"]):
                return cache[url]["content"]

        # Every piece of this is relevant to the HTTP format
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        # Necessary in 1.1, otherwise it's keep alive and browser hangs waiting 
        # for further responses
        request += "Connection: keep-alive\r\n"
        request += "User-Agent: python-browser\r\n"
        for header in headers:
            request += "{}\r\n".format(header)
        request += "\r\n"

        # turn the string into bytes, request needs to be in bytes
        # try/catch in case cached socket is now stale
        try:
            s.send(request.encode("utf8"))
        except OSError:
            s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
            s.connect((self.host, self.port))
            if self.scheme == "https":
                ctx = ssl.create_default_context(cafile=certifi.where())
                s = ctx.wrap_socket(s, server_hostname=self.host)
            s.send(request.encode("utf8"))
        

        # Turn the response into a file-like object
        response = s.makefile("rb", encoding="utf8", newline="\r\n")

        # Decompose response
        statusline = response.readline().decode("utf8")
        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        if status.startswith("3") and redirect_limit > 0:
            # redirect request
            # get location header
            redirect_url = response_headers["location"]
            # check if it's just a local redirect
            if redirect_url.startswith("/"):
                self.path = redirect_url
            else:
                self.parse_url(redirect_url)
            content = self.internet_request(redirect_limit = redirect_limit - 1)
            if "cache-control" in response_headers and status == "301":
                # Cache
                self.cache_content(content, response_headers, url)
                
            return content

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read(int(response_headers["content-length"])).decode("utf8")
        sockets[self.host] = s

        if (self.viewSource):
            content = "view-source:" + content

        # Should we cache
        if "cache-control" in response_headers and (status == '200' or status == '404'):
            self.cache_content(content, response_headers, url)

        return content

    def request(self, headers=[]):
        if ("http" in self.scheme):
            return self.internet_request()
        
        # File Request
        if (self.scheme == "file"):
            f = open(self.path)
            return f.read()

        # Data Request
        if (self.scheme == "data"):
            return self.path
        

def show(body):
    in_tag = False
    if (body.startswith("view-source:")):
        print(body)
        return
    output = ""
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            output += c
    output = output.replace("&lt;", "<")
    output = output.replace("&gt;", ">")
    print(output)
        
def load(url):
    body = url.request()
    show(body)    


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        load(URL(sys.argv[1]))
    else:
        load(URL("file://./welcome.txt"))
    

