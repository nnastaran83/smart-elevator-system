from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import face_recognition
import numpy as np
import cv2
from app.model.mongo_db import Model
from voice_assistant import VoiceAssistant
from concurrent.futures import ThreadPoolExecutor


class KivyCamera(Image):
    """
    kivy camera - gets open-cv video capture as argument and integrates it into kivy camera.
                - when the "Verify" button is pressed, the _identity_check method whill be invoked.
    """

    def __init__(self, **kwargs):
        super(KivyCamera, self).__init__(**kwargs)
        self.executor = ThreadPoolExecutor(1)

        self.identification_event = None
        self.frame = None
        self.ret = None
        self._load_data()
        self.capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.fps = 33.
        self.voice_assistant = VoiceAssistant()
        self._set_action_performance()
        Clock.schedule_interval(self._update, 1.0 / self.fps)

    def _update(self, dt):
        """
        updates the captured video from open-cv each 30 sec
        """
        self.ret, self.frame = self.capture.read()

        if self.ret:
            # convert it to texture
            buf1 = cv2.flip(self.frame, 0)
            buf = buf1.tobytes()
            image_texture = Texture.create(size=(self.frame.shape[1], self.frame.shape[0]), colorfmt='bgr')
            image_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            # display image from the texture
            self.texture = image_texture

    def _load_data(self):
        """
        Loads the necessary data for the application to run
        :return: None
        """

        # Load a sample picture and learn how to recognize it.

        # Model.add_user(name="Nas", face_encoding=list(self.obama_face_encoding), floor_number=3)

        # Load a second sample picture and learn how to recognize it.
        self.biden_image = face_recognition.load_image_file("app/model/images/NastaranMotiee.jpg")
        self.biden_face_encoding = face_recognition.face_encodings(self.biden_image)[0]

        # get all face_encodings from DB
        known_face_encodings_from_mongo = Model.get_all_face_encodings()
        self.known_face_encodings = []
        for face_encoding_dict in known_face_encodings_from_mongo:
            self.known_face_encodings.append(np.array(face_encoding_dict["face_encoding"]))

        self.known_face_names = [
            "Nastaran Motiee",
            "Joe Biden"
        ]

        # Initialize some variables
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_this_frame = True

    def _identity_check(self, dt):

        """
        checks the identity of the person which is in front of the camera
        if the person is recognized - shows the name of the person
        else - shows unknown
        """
        # Only process every other frame of video to save time
        if self.process_this_frame:
            # Resize frame of video to 1/4 size for faster face recognition processing
            small_frame = cv2.resize(self.frame, (0, 0), fx=0.25, fy=0.25)

            # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
            self.rgb_small_frame = small_frame[:, :, ::-1]

            # Find all the faces and face encodings in the current frame of video
            self.face_locations = face_recognition.face_locations(self.rgb_small_frame)
            self.face_encodings = face_recognition.face_encodings(self.rgb_small_frame, self.face_locations)

            face_names = []

            for face_encoding in self.face_encodings:
                # See if the face is a match for the known face(s)
                self.matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                name = "Unknown"

                # # If a match was found in known_face_encodings, just use the first one.
                # if True in matches:
                #     first_match_index = matches.index(True)
                #     name = known_face_names[first_match_index]

                # Or instead, use the known face with the smallest distance to the new face
                self.face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                self.best_match_index = np.argmin(self.face_distances)
                if self.matches[self.best_match_index]:
                    name = self.known_face_names[self.best_match_index]

                face_names.append(name)

                print(face_names)

                if len(face_names) != 0:
                    self.identification_event.cancel()

                    self.executor.submit(self.voice_assistant.hello, name)

                    return False

    def _verify_button_action(self, action_listener):
        """
        -Schedules identification
        -used when verify button is pressed
        :param action_listener: btn_obj
        :return: None
        """
        self.identification_event = Clock.schedule_interval(self._identity_check, 1.0 / 30.0)

    def _set_action_performance(self):
        """
        sets the actions performances for KivyCamera Class widgets
        """
        self.ids.KivyCamera_verify_btn.bind(on_press=self._verify_button_action)

    def stop(self):
        self.capture.release()