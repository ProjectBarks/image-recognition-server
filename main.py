import os
import tornado.httpserver
import tornado.ioloop
import tornado.web
from PIL import Image
from io import BytesIO


class MainHandler(tornado.web.RequestHandler):
    def post(self):
        file_body = self.request.files['image'][0]['body']
        img = Image.open(BytesIO(file_body))
        self.write(str(img.size[0]) + ":" + str(img.size[1]))


def main():
    application = tornado.web.Application([
        (r"/", MainHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()