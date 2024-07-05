import sys, os
import socket 
import ssl
import urllib.parse

class URL:
    def __init__(self, url):
        try:
            self.scheme, url = url.split("://", 1)
            possible_schemes = {
                "http": 80,
                "https": 443,
                "file": 0,
            }
            assert self.scheme in possible_schemes
            self.port = possible_schemes[self.scheme]

            # parsing URL address
            if "/" not in url:
                url = url + "/"
            self.host, url = url.split("/", 1)
            self.path = "/" + url
            if ":" in self.host:
                self.host, port = self.host.split(":", 1)
                self.port = int(port)
        except:
            if url.startswith("data"):
                self.scheme, url = url.split("/", 1)
                media_types, self.data = url.split(",", 1)

    def request(self):
        if self.scheme in ["http", "https"]:
            s = socket.socket(
                family=socket.AF_INET, 
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP
            )

            s.connect((self.host, self.port))

            if self.scheme == "https":
                # create context and wrap socket
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)

            # craft request headers
            request_headers = {
                "Host": self.host,
                "Connection": "close",
                "User-Agent": "Yeltsin/1.0 (Boris from Russia)"
            }
            request = f"GET {self.path} HTTP/1.1\r\n"
            for req, val in request_headers.items():
                request += f"{req}: {val}\r\n"
            request += "\r\n"

            s.send(request.encode("utf8")) # encode into bytes

            # parse all received bytes
            response = s.makefile("r", encoding="utf8", newline="\r\n")
            statusline = response.readline()
            version, status, explanation = statusline.split(" ", 2)

            response_headers = dict()
            while True:
                line = response.readline()
                if line == "\r\n":
                    break 
                header, value = line.split(":", 1)
                response_headers[header.casefold()] = value.strip()

            print(response_headers)

            # ensure regularity in headers
            assert "transfer-encoding" not in response_headers 
            assert "content-encoding" not in response_headers 

            content = response.read()
            s.close()

        elif self.scheme == "file":
            content = open(self.path, "r")
            content = "".join(content.readlines())

        elif self.scheme.startswith("data"):
            content = urllib.parse.unquote(self.data, encoding='utf-8')
            
        return content


def show(body):
    """
    Print all text (without tags).
    """
    in_tag = False 
    for c in body:
        if c == "<":
            in_tag = True 
        elif c == ">":
            in_tag = False 
        elif not in_tag:
            print(c, end="")

def load(url):
    body = url.request()
    show(body)

if __name__ == "__main__":
    load(URL(sys.argv[1]))