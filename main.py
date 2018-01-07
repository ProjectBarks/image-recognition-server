import os
import tornado.httpserver
import tornado.ioloop
import tornado.web

import json
import re
import base64

from nltk.corpus import wordnet
from PIL import Image
from io import BytesIO
import grequests

print('Loading Nouns...')
NOUNS = {x.name().split('.', 1)[0] for x in wordnet.all_synsets('n')}
print('Loaded!')

BANNED_WORDS = ['red', 'blue', 'green', 'white', 'yellow', 'orange', 'brown', 'black', 'gray', 'grey']

BASE_URL = 'https://westcentralus.api.cognitive.microsoft.com/vision/v1.0/analyze'
HEADERS = {'Content-Type': 'application/octet-stream', 'Ocp-Apim-Subscription-Key': 'fb4716ed10714097b83eee1544ba4d94'}


class MainHandler(tornado.web.RequestHandler):
    def post(self):

        def image_to_binary(to_binary):
            output = BytesIO()
            to_binary.save(output, format='JPEG')
            output.seek(0)
            return output

        try:
            image_data = re.sub('^data:image/.+;base64,', '', self.request.body.decode('utf-8'))
            img = Image.open(BytesIO(base64.b64decode(image_data)))

            columns, rows, min_confidence = 5, 2, 0.5
            width, height = int(img.size[0] / columns), int(img.size[1] / rows)
            keys, requests = [], []
            requests.append(grequests.post(
                url=BASE_URL,
                headers=HEADERS,
                params={'visualFeatures': 'Tags,Description', 'language': 'en'},
                data=image_to_binary(img)
            ))
            for x in range(0, columns):
                for y in range(0, rows):
                    data = image_to_binary(img.crop((
                        x * width,
                        y * height,
                        (x * width) + width,
                        (y * height) + height
                    )))

                    keys.append({'x': x, 'y': y})
                    requests.append(grequests.post(
                        url=BASE_URL,
                        params={'visualFeatures': 'Tags', 'language': 'en'},
                        headers=HEADERS,
                        data=data
                    ))
            request_data = grequests.map(requests)
            values = []
            for idx, old_word_list in enumerate(list(map(lambda z: z.json().get("tags", {}), request_data[1:]))):
                new_word_list = []
                for word in old_word_list:
                    if word['confidence'] < min_confidence:
                        continue
                    if word['name'] in BANNED_WORDS:
                        continue
                    if word['name'] not in NOUNS:
                        continue
                    new_word_list.append(word['name'])
                values.append({ 'tags': new_word_list, 'position': keys[idx]})

            self.write(json.dumps({'meta': request_data[0].json().get('description', {}), 'blocks': values}))

        except Exception as e:
            self.write('Invalid Image!' + '\n' + str(e))
            self.send_error(400)
            raise e


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