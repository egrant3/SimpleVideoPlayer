import cv2
import traceback
import numpy as np
import screeninfo
import time
import os

import tkinter as tk
from tkinter import filedialog

VP_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video_player_config.txt')

class SimpleVideoPlayer:
    def __init__(self, path=None):
        self.path = path if path is not None else self.open_file_dialog()
        self.load_video(self.path)

        for m in self.monitors():
            if m.is_primary:
                self.monitor = m

        self.paused = False
        self.should_quit = False
        self.show_text = True
        self.is_fullscreen = False
        self.should_load_new = False

    def __del__(self):
        try:
            self._reader.release()
        except:
            pass

    @classmethod
    def read_player_default_path(cls):
        if os.path.exists(VP_CONFIG):
            with open(VP_CONFIG, 'r') as f:
                line = f.readline().strip()
                return line
        return None

    @classmethod
    def set_player_default_path(cls, val):
        with open(VP_CONFIG, 'w') as f:
            f.write(f'{val}\n')

    def load_video(self, video_path):
        try:
            self._reader.release()
            del self._reader
        except:
            pass

        self._reader = cv2.VideoCapture(video_path)
        if not self._reader.isOpened():
            raise Exception('VideoPlayer failed to open video at specified path')
        self._frame_pos = 0
        self._wait_time_ms = int(round(1000.0 / self.fps()))
        self.path = video_path
        self.set_player_default_path(os.path.dirname(video_path))

        print(f'\nSuccessfully loaded video from \n\t{video_path}\nWith properties:\n\t' + \
              f'Resolution: {self.height()} x {self.width()}\n\t' + \
              f'Duration: {self.frame_count() / self.fps():0.2f}s ({self.frame_count()} frames)\n\t' + \
              f'FPS: {self.fps()}\n')  

    def open_file_dialog(self):
        base_path = self.read_player_default_path()        
        root = tk.Tk()
        root.withdraw()
        return filedialog.askopenfilename(initialdir=base_path, title="Select a file")        

    def __len__(self):
        return int(self._reader.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def width(self):
        return int(self._reader.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    def height(self):
        return int(self._reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    def fps(self):
        return int(self._reader.get(cv2.CAP_PROP_FPS))
    
    def frame_count(self):
        return int(self._reader.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def set_frame_pos(self, frame):
        self._frame_pos = frame
        self._reader.set(cv2.CAP_PROP_POS_FRAMES, frame)        

    def read(self):
        success, frame = self._reader.read()
        self._frame_pos += 1
        return success, frame

    def overlay_text(self, img, text, origin=(20, 20)):
        font = cv2.FONT_HERSHEY_SIMPLEX
        fontScale = 1
        color = (255,255,255)
        thickness = 2

        (tw, th), baseline = cv2.getTextSize(text, font, fontScale, thickness)
        origin = (origin[0], origin[1] + th)

        return cv2.putText(img, text, origin, font, fontScale, color, thickness, cv2.LINE_AA, False)
    
    def create_window(self, name, flags):
        cv2.namedWindow(name, flags)
        # cv2.setWindowProperty(name,cv2.WND_PROP_TOPMOST, 1)
    
    @classmethod
    def monitors(cls):
        # winname = 'Fullscreen Test'
        # cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
        # cv2.setWindowProperty(winname, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        monitors = screeninfo.get_monitors()
        # for m in reversed(monitors):
        #     print(m)
        return monitors

    def play(self):
        while not self.should_quit:
            self.__play()
            if self.should_load_new:
                new_path = self.open_file_dialog()
                self.load_video(new_path)
                self.should_load_new = False
                
    def __play(self):

        window_name = self.path
        window_mode = None

        fs_H = self.monitor.height
        fs_W = self.monitor.width

        FPS_duration = 1.0 / self.fps()

        # Compute needed params to show fullscreen without stretching
        if self._reader.isOpened():
            success = False
            while not success:
                success, frame = self.read()
                
            self.set_frame_pos(self._frame_pos-1)
            scale = (float(fs_H) / float(frame.shape[0]), float(fs_W) / float(frame.shape[1]))


            dim2pad = int(0 + 1 * (np.abs(1 - scale[0]) >= np.abs(1 - scale[1])))
            scale = scale[dim2pad]

            new_H = int(frame.shape[0] * scale)
            new_W = int(frame.shape[1] * scale)

            x_offset = (self.monitor.width  - new_W) // 2
            y_offset = (self.monitor.height - new_H) // 2

            blank_frame = np.zeros((self.monitor.height, self.monitor.width, 3), dtype=np.uint8)

        # cv2.namedWindow(window_name, window_mode)
        if not self.is_fullscreen:
            self.create_window(window_name, window_mode)
        else:
            self.create_window(window_name, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, 1)

        start_time = time.perf_counter()

        while(self._reader.isOpened() and not self.should_quit and not self.should_load_new):
            # Read in new frame
            success, frame = self.read()         

            if success:

                if self.is_fullscreen:
                    frame_fullscreen = np.copy(blank_frame)
                    frame = cv2.resize(frame, (new_W, new_H))
                    frame_fullscreen[y_offset:y_offset+new_H, x_offset:x_offset+new_W] = frame
                    frame = frame_fullscreen
                
                frame2show = np.copy(frame)
                frame_text = self.overlay_text(np.copy(frame), f'frame: {self._frame_pos-1} / {len(self)-1}')

                if self.show_text:
                    frame2show = frame_text

                while True:
                    if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) == 0:    
                        # Window won't be destroyed if minimized, closed, or otherwise made invisible. Only ESC and "Q" keys will close it                    
                        self.create_window(window_name, window_mode)                        

                    # print(f'showing {self._frame_pos-1}')
                    if (time.perf_counter() - start_time) >= FPS_duration:       
                        cv2.imshow(window_name, frame2show)
                        start_time = time.perf_counter()

                    key_full = cv2.waitKey(1)#self._wait_time_ms)
                    key = key_full & 0xFF

                    # if key_full >= 0:
                    #     print(f'key_full: {key_full}, key: {key}')

                    # No input, continue
                    if key_full == -1 and not self.paused:
                        break
                    
                    # 'O' key to open a new video
                    if key in [ord('o'), ord('O')]:
                        self.should_load_new = True
                        break

                    # 'Q' or ESC key to quit / close player
                    if  key in [ord('q'), ord('Q')] or key == 27:                        
                        self.should_quit = True
                        break
                    
                    # 'T' key to toggle framenum text overlay
                    if key in [ord('t'),ord('T')]:
                        self.show_text = not self.show_text

                        if self.show_text:
                            frame2show = frame_text
                        else:
                            frame2show = frame

                        if not self.paused:
                            break

                    if key in [ord('f'), ord('F')]:
                        self.is_fullscreen = not self.is_fullscreen
                        cv2.destroyWindow(window_name)
                        if self.is_fullscreen:
                            self.create_window(window_name, cv2.WINDOW_NORMAL)
                            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, 1)

                        if self.paused and self._frame_pos > 0:
                            self._frame_pos -= 1

                        break


                    # Number key to scrub through video in 10% increments
                    if key >= 48 and key <= 57:
                        # numeric entry
                        self.set_frame_pos(np.floor((float(key - 48) / 10.0) * self.frame_count()).astype(int))
                        break

                    # 'A' to step backward one frame when paused
                    if key in [ord('a'), ord('A')] and self.paused:
                        new_frame = (self._frame_pos - 2) % self.frame_count()
                        if self._frame_pos - 2 < 0:
                            print('NEGATIVE FRAME NUMBER INPUT... LOOPING TO END OF VIDEO')
                        self.set_frame_pos(new_frame)

                        break
                    
                    # 'D' to step forward one frame when paused
                    if key in [ord('d'), ord('D')] and self.paused:
                        break

                    # 'S' to toggle paused state
                    if key in [ord('s'), ord('S')]:
                        self.paused = not self.paused
                    
            else:
                if self._frame_pos >= self.frame_count():
                    self.set_frame_pos(0)
                    print('END REACHED... LOOPING!')
                else:
                    break
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        vp = SimpleVideoPlayer()
        vp.play()

    except Exception as e:
        stack_trace = traceback.format_exc()
        print(stack_trace)

    finally:        
        if 'vp' in locals():
            del vp
        print('Exited cleanly, done!')
