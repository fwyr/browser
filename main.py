import sys, os
import socket 
import ssl
import urllib.parse
import tkinter

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 8, 18
SCROLL_STEP = 100

def lex(body):
    """
    Parse all text (without tags, with entities).
    """
    text = ""
    in_tag = False 
    for c in body:
        if c == "<":
            in_tag = True 
        elif c == ">":
            in_tag = False 
        elif not in_tag:
            text += c

    # convert entities to text
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    return text

def layout(text):
    """
    Compute and store the position of each character.
    """
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP 
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP or c == "\n":
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )

        self.canvas.pack()
        self.scroll = 0 # how far you've scrolled
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.scrollmouse)

    def load(self, url):
        body = url.request()
        text = lex(body)
        self.display_list = layout(text)
        self.draw()

    def draw(self):
        """
        Loop through `display_list` and draw each character
        """
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: 
                continue
            if y + VSTEP < self.scroll: 
                continue
            self.canvas.create_text(x, y - self.scroll, text=c)

    def scrolldown(self, e):
        """
        Called when down key is pressed.
        Increments `y` and redraws canvas.
        """
        self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self, e):
        """
        Called when up key is pressed.
        Decrements `y` and redraws canvas. 
        """
        if self.scroll - SCROLL_STEP > 0:
            self.scroll -= SCROLL_STEP 
            self.draw()

    def scrollmouse(self, e):
        """ 
        Scrolls based on mouse action.
        """
        print(e.delta)
        if e.delta > 0:
            self.scroll += SCROLL_STEP / 2
            self.draw()
        elif e.delta < 0:
            if self.scroll - (SCROLL_STEP/2) * (-e.delta) > 0:
                self.scroll -= SCROLL_STEP / 2
                self.draw()


class URL:
    def __init__(self, url):
        self.view_source = False
        try:
            self.scheme, url = url.split("://", 1)
            possible_schemes = {
                "http": 80,
                "https": 443,
                "file": 0,
            }
            if self.scheme.startswith("view-source:"):
                self.view_source = True
                self.scheme = self.scheme.split(":", 1)[1]
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
            else:
                self.scheme = "about:blank"

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

        elif self.scheme == "about:blank":
            content = ""

        if status == "301":
            redirect_url = response_headers["location"]
            if redirect_url.startswith("/"):
                redirect_url = f"{self.scheme}://{self.host}{redirect_url}"
            content = URL(redirect_url).request()
            
        if self.view_source:
            content = content.replace("<", "&lt;")
            content = content.replace(">", "&gt;")

        return content

if __name__ == "__main__":
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()