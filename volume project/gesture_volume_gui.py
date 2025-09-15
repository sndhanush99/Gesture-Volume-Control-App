import tkinter as tk
from tkinter import Label, Button
import cv2
from PIL import Image, ImageTk
import mediapipe as mp
import numpy as np
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class GestureVolumeControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gesture Volume Control")
        self.root.geometry("800x600")

        self.label = Label(root)
        self.label.pack()

        self.status = Label(root, text="Click Start to Begin", font=("Helvetica", 14))
        self.status.pack(pady=10)

        self.start_btn = Button(root, text="Start Gesture Control", command=self.start)
        self.start_btn.pack()

        self.stop_btn = Button(root, text="Stop", command=self.stop, state=tk.DISABLED)
        self.stop_btn.pack(pady=5)

        self.running = False
        self.cap = None
        self.hands = mp.solutions.hands.Hands()
        self.mpDraw = mp.solutions.drawing_utils

        # Volume control setup
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.volume = cast(interface, POINTER(IAudioEndpointVolume))
        self.minVol, self.maxVol = self.volume.GetVolumeRange()[:2]
        self.isMuted = False
        self.cooldownCounter = 0

    def start(self):
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.cap = cv2.VideoCapture(0)
        self.update_frame()

    def stop(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        if self.cap:
            self.cap.release()
        self.label.config(image='')
        self.status.config(text="Stopped")

    def update_frame(self):
        if not self.running:
            return

        success, img = self.cap.read()
        if not success:
            self.status.config(text="Camera Error")
            return

        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.hands.process(imgRGB)

        lmList = []
        h, w, c = img.shape

        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                for id, lm in enumerate(handLms.landmark):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lmList.append([id, cx, cy])
                self.mpDraw.draw_landmarks(img, handLms, mp.solutions.hands.HAND_CONNECTIONS)

            if len(lmList) >= 21:
                x1, y1 = lmList[4][1], lmList[4][2]   # Thumb tip
                x2, y2 = lmList[8][1], lmList[8][2]   # Index tip
                x4, y4 = lmList[4][1], lmList[4][2]   # Thumb again
                x20, y20 = lmList[20][1], lmList[20][2]  # Pinky tip

                # Volume adjustment
                length = math.hypot(x2 - x1, y2 - y1)
                vol = np.interp(length, [50, 300], [self.minVol, self.maxVol])
                volPer = np.interp(length, [50, 300], [0, 100])

                if not self.isMuted:
                    self.volume.SetMasterVolumeLevel(vol, None)

                mute_dist = math.hypot(x20 - x4, y20 - y4)
                if mute_dist < 40 and self.cooldownCounter == 0:
                    self.isMuted = not self.isMuted
                    self.volume.SetMute(self.isMuted, None)
                    self.cooldownCounter = 30

                if self.cooldownCounter > 0:
                    self.cooldownCounter -= 1

                mute_text = "Muted" if self.isMuted else f"Volume: {int(volPer)} %"
                self.status.config(text=mute_text)

        # Convert image to display
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (800, 450))
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)
        self.label.imgtk = imgtk
        self.label.configure(image=imgtk)

        self.root.after(10, self.update_frame)

# Launch the app
if __name__ == "__main__":
    root = tk.Tk()
    app = GestureVolumeControlApp(root)
    root.mainloop()
