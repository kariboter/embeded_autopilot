import numpy as np
import cv2

import threading


import _thread
from multiprocessing import Process
from collections import deque


from socketserver import ThreadingMixIn
import socketserver
import logging
from http import server
import io
from threading import Condition


def putBText(img, text, text_offset_x=20, text_offset_y=20, vspace=10, hspace=10, font_scale=1.0,
             background_RGB=(228, 225, 222), text_RGB=(1, 1, 1), font=cv2.FONT_HERSHEY_DUPLEX, thickness=2, alpha=0.6,
             gamma=0):
    """
    Inputs:
    img: cv2 image img
    text_offset_x, text_offset_x: X,Y location of text start
    vspace, hspace: Vertical and Horizontal space between text and box boundries
    font_scale: Font size
    background_RGB: Background R,G,B color
    text_RGB: Text R,G,B color
    font: Font Style e.g. cv2.FONT_HERSHEY_DUPLEX,cv2.FONT_HERSHEY_SIMPLEX,cv2.FONT_HERSHEY_PLAIN,cv2.FONT_HERSHEY_COMPLEX
          cv2.FONT_HERSHEY_TRIPLEX, etc
    thickness: Thickness of the text font
    alpha: Opacity 0~1 of the box around text
    gamma: 0 by default

    Output:
    img: CV2 image with text and background
    """
    R, G, B = background_RGB[0], background_RGB[1], background_RGB[2]
    text_R, text_G, text_B = text_RGB[0], text_RGB[1], text_RGB[2]
    (text_width, text_height) = cv2.getTextSize(text, font, fontScale=font_scale, thickness=thickness)[0]
    x, y, w, h = text_offset_x, text_offset_y, text_width, text_height
    crop = img[y - vspace:y + h + vspace, x - hspace:x + w + hspace]
    white_rect = np.ones(crop.shape, dtype=np.uint8)
    b, g, r = cv2.split(white_rect)
    rect_changed = cv2.merge((B * b, G * g, R * r))

    res = cv2.addWeighted(crop, alpha, rect_changed, 1 - alpha, gamma)
    img[y - vspace:y + vspace + h, x - hspace:x + w + hspace] = res

    cv2.putText(img, text, (x, (y + h)), font, fontScale=font_scale, color=(text_B, text_G, text_R),
                thickness=thickness)
    return img






class Streamer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class StreamProps(server.BaseHTTPRequestHandler):

    def set_Page(self, PAGE):
        self.PAGE = PAGE

    def set_Capture(self, capture):
        self.capture = capture

    def set_Quality(self, quality):
        self.quality = quality

    def set_Mode(self, mode):
        self.mode = mode

    def set_Output(self, output):
        self.output = output

    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = self.PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            if self.mode == 'cv2':
                try:
                    while True:
                        res, img = self.capture.read()
                        frame = cv2.imencode('.JPEG', img, [cv2.IMWRITE_JPEG_QUALITY, self.quality])[1].tobytes()
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                except Exception as e:
                    logging.warning(
                        'Removed streaming client %s: %s',
                        self.client_address, str(e))
            if self.mode == 'picamera':
                try:
                    while True:
                        with self.output.condition:
                            self.output.condition.wait()
                            frame = self.output.frame
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                except Exception as e:
                    logging.warning(
                        'Removed streaming client %s: %s',
                        self.client_address, str(e))

        else:
            self.send_error(404)
            self.end_headers()