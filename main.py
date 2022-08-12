from kivy.app import App
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import face_recognition
import cv2
import numpy as np

from threading import Lock, Thread


class SingletonMeta(type):
    """
    Thread-safe implementation of Singleton.
    """

    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]

class KivyCamera(Image):
    def __init__(self, capture, fps, **kwargs):
        super(KivyCamera, self).__init__(**kwargs)
        self.frame = None
        self.ret = None
        self.load_data()
        self.capture = capture
        Clock.schedule_interval(self.update, 1.0 / fps)

    def update(self, dt):
        self.ret, self.frame = self.capture.read()
        self.identity_check()
        if self.ret:
            # convert it to texture
            buf1 = cv2.flip(self.frame, 0)
            buf = buf1.tostring()
            image_texture = Texture.create(size=(self.frame.shape[1], self.frame.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            # display image from the texture
            self.texture = image_texture


    def load_data(self):
        # TODO: - make this function return true if the person was recognized, else return false.
        #       - write pydoc

        # Load a sample picture and learn how to recognize it.
        self.obama_image = face_recognition.load_image_file("images/NastaranMotiee.jpg")
        self.obama_face_encoding = face_recognition.face_encodings(self.obama_image)[0]

        # Load a second sample picture and learn how to recognize it.
        self.biden_image = face_recognition.load_image_file("images/NastaranMotiee.jpg")
        self.biden_face_encoding = face_recognition.face_encodings(self.biden_image)[0]

        # Create arrays of known face encodings and their names
        self.known_face_encodings = [
            self.obama_face_encoding,
            self.biden_face_encoding
        ]
        self.known_face_names = [
            "Nastaran Motiee",
            "Joe Biden"
        ]

        # Initialize some variables
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_this_frame = True

    def identity_check(self):
        # Only process every other frame of video to save time
        if self.process_this_frame:
            # Resize frame of video to 1/4 size for faster face recognition processing
            self.small_frame = cv2.resize(self.frame, (0, 0), fx=0.25, fy=0.25)

            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            self.rgb_small_frame = self.small_frame[:, :, ::-1]

            # Find all the faces and face encodings in the current frame of video
            self.face_locations = face_recognition.face_locations(self.rgb_small_frame)
            self.face_encodings = face_recognition.face_encodings(self.rgb_small_frame, self.face_locations)

            self.face_names = []
            for self.face_encoding in self.face_encodings:
                # See if the face is a match for the known face(s)
                self.matches = face_recognition.compare_faces(self.known_face_encodings, self.face_encoding)
                name = "Unknown"

                # # If a match was found in known_face_encodings, just use the first one.
                # if True in matches:
                #     first_match_index = matches.index(True)
                #     name = known_face_names[first_match_index]

                # Or instead, use the known face with the smallest distance to the new face
                self.face_distances = face_recognition.face_distance(self.known_face_encodings, self.face_encoding)
                self.best_match_index = np.argmin(self.face_distances)
                if self.matches[self.best_match_index]:
                    name = self.known_face_names[self.best_match_index]

                self.face_names.append(name)

        self.process_this_frame = not self.process_this_frame

        # Display the results
        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(self.frame, (left, top), (right, bottom), (255, 255, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(self.frame, (left, bottom - 35), (right, bottom), (255, 255, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(self.frame, name, (left + 6, bottom - 6), font, 1.0, (0, 0, 0), 1)


class CamApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capture = None

    def build(self):
        self.capture = cv2.VideoCapture(0)
        face_recognition_camera = KivyCamera(capture=self.capture, fps=30)
        return face_recognition_camera

    def on_stop(self):
        # without this, app will not exit even if the window is closed
        self.capture.release()


if __name__ == '__main__':
    CamApp().run()
