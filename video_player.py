import cv2
import traceback
import numpy as np
import screeninfo
import time
import os

import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog

VP_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'video_player_config.txt')

class SimpleVideoPlayer:
    def __init__(self, path=None):

        self._init_tk()

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
        self._wait_time_ms = int(round(1000.0 / self.fps()))
        self.path = video_path
        self.set_player_default_path(os.path.dirname(video_path))

        print(f'\nSuccessfully loaded video from \n\t{video_path}\nWith properties:\n\t' + \
              f'Resolution: {self.height()} x {self.width()}\n\t' + \
              f'Duration: {self.frame_count() / self.fps():0.2f}s ({self.frame_count()} frames)\n\t' + \
              f'FPS: {self.fps()}\n')  

    def _init_tk(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def open_file_dialog(self):
        base_path = self.read_player_default_path()        
        file = filedialog.askopenfilename(initialdir=base_path, title="Select a file")     
        return file   

    def get_user_input(self, label=None):

        def on_enter(event):            
            # Retrieve input
            self.user_input = entry.get()
            # Destroy / Close popup window
            self.root.quit()
            popup.destroy()

        # Create popup user input window
        popup = tk.Toplevel(self.root)
        popup.title("User Input")

        # Label it... (optional)
        if label is not None:
            popup_label = tk.Label(popup, text=label)
            popup_label.pack(pady=5, padx=10)

        # Create entry widget
        entry = tk.Entry(popup)
        entry.pack(pady=10, padx=10)
        
        # Make sure user can immediately type in entry field
        entry.focus_force()

        # Bind Enter key to the on_enter function above
        entry.bind('<Return>', on_enter)

        self.root.mainloop()

        return self.user_input

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
        
    def get_frame_pos(self):
        return int(self._reader.get(cv2.CAP_PROP_POS_FRAMES))
    
    def set_frame_pos(self, frame):
        frame = frame % self.frame_count()
        self._reader.set(cv2.CAP_PROP_POS_FRAMES, frame)

    def set_frame_pos_relative(self, n):
        self.set_frame_pos(self.get_frame_pos() + n)

    def read(self):

        for attempt in [0, 1]:
            success, frame = self._reader.read()

            if success:
                return frame

            self.set_frame_pos(self.get_frame_pos())
        
        raise Exception(f'Reader failed to read frame {self.get_frame_pos()}')                

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

            frame = self.read()
                
            self.set_frame_pos_relative(-1)
            scale = (float(fs_H) / float(frame.shape[0]), float(fs_W) / float(frame.shape[1]))

            dim2pad = int(0 + 1 * (np.abs(1 - scale[0]) >= np.abs(1 - scale[1])))
            scale = scale[dim2pad]

            fullscreen_H = int(frame.shape[0] * scale)
            fullscreen_W = int(frame.shape[1] * scale)

            x_offset = (self.monitor.width  - fullscreen_W) // 2
            y_offset = (self.monitor.height - fullscreen_H) // 2

            blank_fullscreen_frame = np.zeros((self.monitor.height, self.monitor.width, 3), dtype=np.uint8)

        # cv2.namedWindow(window_name, window_mode)
        if not self.is_fullscreen:
            self.create_window(window_name, window_mode)
        else:
            self.create_window(window_name, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, 1)

        start_time = time.perf_counter() - FPS_duration

        req_new_frame = True
        draw_now = True
        while(self._reader.isOpened() and not self.should_quit and not self.should_load_new):

            if req_new_frame:                

                # Read in new frame
                frame = self.read()

                if self.is_fullscreen:
                    frame_fullscreen = np.copy(blank_fullscreen_frame)
                    frame = cv2.resize(frame, (fullscreen_W, fullscreen_H))
                    frame_fullscreen[y_offset:y_offset+fullscreen_H, x_offset:x_offset+fullscreen_W] = frame
                    frame = frame_fullscreen
                
                frame2show = np.copy(frame)
                frame_text = self.overlay_text(np.copy(frame), f'frame: {self.get_frame_pos()-1} / {len(self)-1}')

                if self.show_text:
                    frame2show = frame_text

                req_new_frame = False

            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) == 0:    
                # Window won't be destroyed if minimized, closed, or otherwise made invisible. Only ESC and "Q" keys will close it                    
                self.create_window(window_name, window_mode)                        

            if self.paused:
                start_time = time.perf_counter()

            draw_now = draw_now or (time.perf_counter() - start_time) >= FPS_duration

            if draw_now:
                draw_now = False
                start_time = time.perf_counter()
                cv2.imshow(window_name, frame2show)
                req_new_frame = True
                
            key_full = cv2.waitKey(1)
            key = key_full & 0xFF

            # if key_full >= 0:
            #     print(f'key_full: {key_full}, key: {key}')

            # No input, continue
            if key_full == -1:
                continue
            
            # 'O' key to open a new video
            if key in [ord('o'), ord('O')]:
                self.should_load_new = True
                continue

            # 'Q' or ESC key to quit / close player
            if  key in [ord('q'), ord('Q')] or key == 27:                        
                self.should_quit = True
                continue             
            
            # 'T' key to toggle framenum text overlay
            if key in [ord('t'),ord('T')]:
                draw_now = True
                req_new_frame = True           
                self.show_text = not self.show_text
                if self.paused:
                    self.set_frame_pos_relative(-3)
                
            if key in [ord('f'), ord('F')]:
                self.is_fullscreen = not self.is_fullscreen
                cv2.destroyWindow(window_name)
                if self.is_fullscreen:
                    self.create_window(window_name, cv2.WINDOW_NORMAL)
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, 1)

                if self.paused:
                    self.set_frame_pos_relative(-2)

                req_new_frame = True
                draw_now = True
                continue

            # Number key to scrub through video in 10% increments
            if key >= 48 and key <= 57:
                # numeric entry
                self.set_frame_pos(np.floor((float(key - 48) / 10.0) * self.frame_count()).astype(int))
                req_new_frame = True
                draw_now = True
                continue

            # 'E' to manually enter frame number to which player should jump
            if key in [ord('e'), ord('E')]:
                self.paused = True
                input = self.get_user_input(label="Enter Frame Number...")
                try:
                    input = int(input)
                    if input >= 0 and input < self.frame_count():
                        self.set_frame_pos(input)
                        req_new_frame = True
                        draw_now = True
                except:
                    pass

            # 'A' to step backward one frame when paused
            if key in [ord('a'), ord('A')] and self.paused:
                self.set_frame_pos_relative(-3)
                req_new_frame = True
                draw_now = True
                continue
            
            # 'D' to step forward one frame when paused
            if key in [ord('d'), ord('D')] and self.paused:                
                draw_now = True
                continue

            # 'S' to toggle paused state
            if key in [ord('s'), ord('S')]:
                self.paused = not self.paused
        
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
