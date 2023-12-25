# runvlc.py
import contextlib
from urllib.parse import unquote
from typing import Any
import wx  # pylint: disable=E0401 # type: ignore
import vlc
from setup_logger import l
from pathlib import Path
import subprocess


class VLCMediaPlayerGUI(wx.Frame):
    def __init__(self, parent, filepath=None, title="Python VLC Media Player") -> None:
        """ Initializes the VLC Media Player object.
        Args: parent: The parent object.
              filepath (optional): The path to the media file to be loaded.
              title (str): The title of the media player window."""
        super().__init__(parent, title=title)
        self.init_ui()
        self.instance = vlc.Instance("--quiet")
        self.previous_volume = 0
        self.player: Any = self.instance.media_player_new()  # type: ignore
        if filepath:
            self.load_media(filepath=filepath)
            self.on_play(event=None)
        self.set_initial_position()
        self.Show()

    def init_ui(self) -> None:
        self.setup_ui_components()
        self.bind_event_handlers()
        self.set_window_size()
        # self.create_video_panel()

    def setup_ui_components(self) -> None:
        """ Set up the UI components for the VLC player. This method initializes and configures the various UI components such as panels, sliders, buttons, and timers."""
        self.pnlVideo: Any = wx.Panel(self)
        self.sldPosition: Any = wx.Slider(self, value=0, minValue=0, maxValue=1000)
        self.btnPlay: Any = wx.Button(self, label="Play")
        self.btnStop: Any = wx.Button(self, label="Stop")
        self.btnMute: Any = wx.Button(self, label="Mute")
        self.btnExit: Any = wx.Button(self, label="Exit")
        self.btnBrowse: Any = wx.Button(self, label="Browse")
        self.sldVolume: Any = wx.Slider(self, value=0, minValue=0, maxValue=100)
        self.timer: Any = wx.Timer(self)
        self.layout_components()

    def layout_components(self) -> None:
        """ Arrange the components in the user interface layout. This method creates and arranges the various components of the user interface layout using wxPython's sizers.
        It adds the video panel, position slider, play/stop/mute buttons, volume slider, and exit button to the main sizer. """
        sizer: Any = wx.BoxSizer(wx.VERTICAL)
        btnSizer: Any = wx.BoxSizer(wx.HORIZONTAL)
        controlSizer: Any = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.pnlVideo, 1, wx.EXPAND)
        sizer.Add(self.sldPosition, 0, wx.EXPAND)

        btnSizer.Add(self.btnPlay)
        btnSizer.AddSpacer(100)
        btnSizer.Add(self.btnStop)
        btnSizer.AddSpacer(150)
        btnSizer.Add(self.btnBrowse)
        btnSizer.AddSpacer(150)
        btnSizer.Add(self.btnMute)
        btnSizer.AddSpacer(300)
        btnSizer.Add(self.btnExit)

        controlSizer.Add(btnSizer, 1, wx.EXPAND)
        controlSizer.Add(self.sldVolume, 0, wx.ALIGN_BOTTOM)
        sizer.Add(controlSizer, 0, wx.EXPAND)
        self.SetSizer(sizer)

    def set_window_size(self) -> None:
        """ Set the size of the window to half of the screen width. """
        screen_width: Any = wx.GetDisplaySize()[0]
        self.SetSize((screen_width // 2, screen_width // 2))

    def on_browse(self, event) -> None:
        """ Open the directory where the video is being played from in the file explorer. """
        mrl: Any = self.media.get_mrl()
        if mrl:
            # Decode the URL-encoded string, remove the 'file:///' prefix, and replace forward slashes with backslashes
            filepath: str = unquote(string=mrl).replace('file:///', '').replace('/', '\\')
            directory: Path = Path(filepath).parent
            if directory.is_dir():
                subprocess.Popen(args=f'explorer "{directory}"')
                l.info(msg=f"Browse to: {directory}")
            else:
                l.error(msg=f"Directory does not exist: {directory}")
        else:
            l.error(msg="No media loaded.")

    def set_initial_position(self) -> None:
        """ Set the initial position of the window. This method sets the size and position of the window to occupy the left half of the screen,
        above the taskbar. """
        client_area: Any = wx.GetClientDisplayRect()  # Get the client area excluding the taskbar
        screen_width: Any = client_area.width
        screen_height: Any = client_area.height
        self.SetSize((screen_width // 2, screen_height))
        self.SetPosition((client_area.x, client_area.y))  # Position on the left side, above taskbar

    def bind_event_handlers(self) -> None:
        """ The function "bind_event_handlers" binds event handlers to various buttons, sliders, and timers in a wxPython application. """
        self.Bind(wx.EVT_BUTTON, self.on_play, self.btnPlay)
        self.Bind(wx.EVT_BUTTON, self.on_stop, self.btnStop)
        self.Bind(wx.EVT_BUTTON, self.on_mute, self.btnMute)
        self.Bind(wx.EVT_BUTTON, self.on_exit, self.btnExit)
        self.Bind(wx.EVT_BUTTON, self.on_browse, self.btnBrowse)
        self.Bind(wx.EVT_SLIDER, self.on_set_volume, self.sldVolume)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel_volume, self.sldVolume)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel_position, self.sldPosition)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.Bind(wx.EVT_CLOSE, self.on_exit)
        self.Bind(wx.EVT_SLIDER, self.on_seek, self.sldPosition)

    # def load_media(self, filepath) -> None:
    #     """ The function `load_media` loads a media file, sets it as the player's media, and plays it while logging information about the media.
    #     :param filepath: The `filepath` parameter is a string that represents the path to the media file that you want to load. It should be the absolute or relative path to the file, including the file name and extension """
    #     try:
    #         self.media: Any = self.instance.media_new(filepath)  # type:ignore
    #         self.player.set_media(self.media)
    #         self.player.set_hwnd(self.pnlVideo.GetHandle())
    #         # cp.print("#" * 10 + f" [{sY}]Playing: -->[/] [{sR}]{filepath}[/] " + "#" * 10, style="blue italic", end="\n")
    #         self.player.play()  # Play to get video size
    #         wx.CallLater(1000, self.log_media_info)  # Delay logging to ensure media is playing
    #     except Exception as e:
    #         l.error(msg=f"Error loading media: {e}")

    def load_media(self, filepath):
        """Load and play media."""
        try:
            # self.create_video_panel()  # Ensure pnlVideo is available
            self.media: Any = self.instance.media_new(filepath)  # type:ignore
            self.player.set_media(self.media)
            self.player.set_hwnd(self.pnlVideo.GetHandle())
            # cp.print("#" * 10 + f" [{sY}]Playing: -->[/] [{sR}]{filepath}[/] " + "#" * 10, style="blue italic", end="\n")
            self.player.play()  # Play to get video size
            wx.CallLater(1000, self.log_media_info)  # Delay logging to ensure media is playing
        except Exception as e:
            l.error(msg=f"Error loading media: {e}")

    def create_video_panel(self):
        """Create or recreate the video panel."""
        if self.pnlVideo:
            self.pnlVideo.Destroy()
        self.pnlVideo = wx.Panel(self)  # Recreate the panel
        # Any additional setup for pnlVideo goes here

    def log_media_info(self) -> None:
        width, height = self.player.video_get_size()
        quality: str = self.calculate_video_quality()  # noqa: F841
        # cp.print("*" * 20 + f" [{sY}]Height:[/][{sW}] {height} [/] | [{sY}]Width:[/][{sW}] {width} [/] | [{sY}]Quality:[/][{sWB}] {quality} [/] " + "*" * 20, style="blue underline", end="\n")

    def calculate_video_quality(self) -> str:
        width, height = self.player.video_get_size()
        if (width, height) >= (3840, 2160):
            return "4K"
        elif (width, height) >= (1920, 1080):
            return "Full HD"
        elif (width, height) >= (1280, 720):
            return "HD"
        elif (width, height) >= (720, 480):
            return "SD"
        else:
            return "Low Quality"

    def on_seek(self, event) -> None:
        new_time: int = int(self.sldPosition.GetValue() * self.player.get_length() / 1000)
        self.player.set_time(new_time)

    def on_open(self, event) -> None:
        with wx.FileDialog(self, "Open Video File", wildcard="Video files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:  # pylint: disable=C0301
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            filepath: Any = fileDialog.GetPath()
            self.load_media(filepath=filepath)

    def on_play(self, event) -> None:
        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.play()
            self.timer.Start(100)

    def on_exit(self, event) -> None:
        self.player.stop()
        self.timer.Stop()
        self.Destroy()

    def on_stop(self, event) -> None:
        self.player.stop()
        self.timer.Stop()
        self.btnPlay.SetLabel("Play")

    def on_mute(self, event) -> None:
        """ The `on_mute` function toggles the mute state of the player and adjusts the volume accordingly.
        :param event: The `event` parameter is an object that represents the event that triggered the `on_mute` method. """
        is_muted: Any = self.player.audio_get_mute()
        self.player.audio_set_mute(not is_muted)
        if is_muted:
            self.sldVolume.SetValue(self.previous_volume)  # Restore previous volume
        else:
            self.previous_volume = self.sldVolume.GetValue()  # Save current volume
            self.sldVolume.SetValue(0)

    def on_timer(self, event) -> None:
        """ Event handler for the timer event. This method is called periodically by a timer to update the position of the slider based on the current playback time.
        Args: event: The timer event object. """
        if self.player.is_playing():
            length: Any = self.player.get_length()
            time: Any = self.player.get_time()
            self.sldPosition.SetValue(int(time * 1000 / length))
        else:
            self.on_play(event=None)  # Loop the video

    def on_set_volume(self, event) -> None:
        """ Sets the volume of the player and toggles mute if volume is 0.
        Args: event: The event object triggered by the volume change. """
        volume: Any = self.sldVolume.GetValue()
        self.player.audio_set_volume(volume)
        if volume == 0:
            self.player.audio_set_mute(True)
        else:
            self.player.audio_set_mute(False)

    def on_mouse_wheel_volume(self, event) -> None:
        """ Adjusts the volume of the player based on the mouse wheel rotation.
        Args: event: The mouse wheel event. """
        rotation = event.GetWheelRotation()
        if rotation > 0:
            new_volume: int = max(0, self.sldVolume.GetValue() - 1)
        else:
            new_volume: int = min(100, self.sldVolume.GetValue() + 1)
        self.sldVolume.SetValue(new_volume)
        self.player.audio_set_volume(new_volume)

    def on_mouse_wheel_position(self, event) -> None:
        """ Adjusts the position of the slider and the player based on the mouse wheel rotation.
        Args: event: The mouse wheel event."""
        rotation = event.GetWheelRotation()
        if rotation > 0:
            new_position: int = max(0, self.sldPosition.GetValue() - 1)
        else:
            new_position: int = min(100, self.sldPosition.GetValue() + 1)
        self.sldPosition.SetValue(new_position)
        self.player.set_position(new_position / 100)

    def on_remove(self) -> None:
        """Remove the currently loaded media from the player."""
        with contextlib.suppress(Exception):
            if self.player:
                self.player.stop()
                self.player.set_media(None)
                # l.info("Media player has been stopped.")

    # def on_remove(self):
    #     """Remove the currently loaded media from the player."""
    #     try:
    #         if self.player:
    #             self.player.stop()
    #             self.player.set_media(None)
    #             # l.info("Media player has been stopped.")
    #     except Exception as e:
    #         l.error(f"Error during media player removal: {e}")


if __name__ == '__main__':
    app: Any = wx.App(False)
    frame = VLCMediaPlayerGUI(parent=None)
    app.MainLoop()
