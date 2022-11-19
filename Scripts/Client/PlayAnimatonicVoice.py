"""
指定した音声ファイルの音量に合わせて、AniCobotの口が開閉するファイル
別スレッドを立てているので、メインのプログラムと干渉しない
"""

import threading
import pyaudio
import wave
import numpy as np
import json
from Socket_Communication import WsClientManager

class AudioManager:
    def __init__(self, name):
        self.filename = name
        self.wf = wave.open(self.filename)
        self.pyaudio = pyaudio.PyAudio()
        self.stream = self.pyaudio.open(format=pyaudio.get_format_from_width(self.wf.getsampwidth()),
                    channels=self.wf.getnchannels(),
                    rate=self.wf.getframerate(),
                    output=True)
        self.CHUNCK_SIZE = 2**10
        self.data = self.wf.readframes(self.CHUNCK_SIZE)
        self.volume = 0

    def PlaySound(self):
        self.volume = np.frombuffer(self.data,dtype="int16")/ 32768.0
        self.volume = self.volume.max()
        self.stream.write(self.data)
        self.data = self.wf.readframes(self.CHUNCK_SIZE)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pyaudio.terminate()

class MouthManager:
    def __init__(self, wsClient):
        self.wsManager = wsClient
        self.speakingState = False
        self.predata = 0

    def SetUpandRun(self, soundFile):
        self.soundFile = soundFile
        self.mouthThread = threading.Thread(target=self.MouthRun)
        self.mouthThread.start()

    def MouthRun(self):
        self.audioManager = AudioManager(self.soundFile)
        while len(self.audioManager.data) > 0:
            try:
                self.speakingState = True
                self.audioManager.PlaySound()
                self.MouthMove(self.audioManager.volume)
            except:
                print("skip")
                continue
        self.speakingState = False

    def MouthMove(self,data_raw):
        data_raw = self.mapping(data_raw, 0.0, 0.8, 0.15, 1.0)
        data = round(data_raw,1)
        if not data == self.predata:
            json_data = {}
            json_data["JawOpen"] =data
            # print(json_data)
            self.wsManager.send(json.dumps(json_data))
        self.predata = data

    def mapping(self,x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def close(self):
        self.audioManager.close()

if __name__ == "__main__":
    ws = WsClientManager(uri="ws://<ip address>")
    # ws = WsClientManager()
    mouth = MouthManager(wsClient=ws)
    mouth.SetUpandRun( soundFile='<sound file>.wav')
