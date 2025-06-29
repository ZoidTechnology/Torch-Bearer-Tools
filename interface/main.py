import atexit
import colour
import numpy as np
import queue
import signal
import sys
import threading
import time
from protocol import *
from serial import Serial
from matplotlib import pyplot as plt

class RefreshableSpectralPlot:
    def __init__(self, initial_sd, update_interval=0.1, refresh_func=None):
        self.sd = initial_sd
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        self.fig = None
        self.ax = None
        self.update_queue = queue.Queue()
        self.cursor_dot = None
        self.cursor_dot2 = None
        self.cursor_text = None
        self.last_mouse_pos = None  # Store last mouse position
        self.cursor_visible = False  # Track cursor visibility state
        self.refresh_func = refresh_func

    def start_plot(self):
        # Create initial plot in main thread
        self.fig, self.ax = colour.plotting.plot_single_sd(self.sd, show=False)
        self._setup_cursor()
        plt.ion()
        plt.show(block=False)
        self.fig.canvas.draw()

        # Start background data generation
        self.running = True
        self.thread = threading.Thread(target=self._data_loop, daemon=True)
        self.thread.start()

        # Main thread handles GUI updates
        try:
            while self.running:
                # Check for new data
                try:
                    new_sd = self.update_queue.get_nowait()
                    self._update_plot(new_sd)
                except queue.Empty:
                    pass

                # Safely handle matplotlib events
                try:
                    plt.pause(0.1)
                except Exception as e:
                    # Catch any matplotlib/Tkinter exceptions during shutdown
                    if self.running:  # Only print if we're not shutting down
                        print(f"Matplotlib error: {e}")
                    break

        except (KeyboardInterrupt, SystemExit):
            self.stop()
        finally:
            self.stop()

    def _data_loop(self):
        """Background thread that generates new data"""
        while self.running:
            try:
                time.sleep(self.update_interval)
                new_data = self.refresh_func() if self.refresh_func else None
                if new_data is not None:
                    self.update_queue.put(new_data)
            except Exception:
                # If we can't get new data, just continue
                if self.running:
                    break

    def _update_plot(self, new_sd):
        """Update plot in main thread"""
        try:
            self.sd = new_sd
            # Clear the existing axes instead of the whole figure
            self.ax.clear()
            # Plot directly to the existing axes
            colour.plotting.plot_single_sd(self.sd, axes=self.ax, show=False)
            # Re-setup cursor after clearing
            self._setup_cursor()
            # Restore cursor state if it was visible
            if self.cursor_visible and self.last_mouse_pos:
                self._update_cursor_position(self.last_mouse_pos[0], self.last_mouse_pos[1])
            self.fig.canvas.draw()
        except Exception as e:
            if self.running:  # Only print if we're not shutting down
                print(f"Plot update error: {e}")

    def _setup_cursor(self):
        """Setup cursor tracking"""
        try:
            # Create cursor dot
            self.cursor_dot = self.ax.plot([], [], 'ro', markersize=6, alpha=0.8, visible=False)[0]
            self.cursor_dot2 = self.ax.plot([], [], 'ro', markersize=4, alpha=0.8, visible=False)[0]
            # Create text annotation
            self.cursor_text = self.ax.annotate('', xy=(0, 0), xytext=(20, 20),
                                              textcoords="offset points",
                                              bbox=dict(boxstyle="round", fc="white", alpha=0.8),
                                              arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
                                              visible=False)

            # Connect mouse motion event
            self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
            self.fig.canvas.mpl_connect('axes_enter_event', self._on_axes_enter)
            self.fig.canvas.mpl_connect('axes_leave_event', self._on_axes_leave)
        except Exception:
            # Ignore cursor setup errors during shutdown
            pass

    def _update_cursor_position(self, x_pos, y_pos):
        """Update cursor position and visibility"""
        try:
            if x_pos is not None and self.cursor_dot and self.cursor_text:
                # Find closest wavelength
                wavelengths = np.array(self.sd.wavelengths)
                values = np.array(self.sd.values)

                # Find the closest point
                idx = np.argmin(np.abs(wavelengths - x_pos))
                closest_wl = wavelengths[idx]
                closest_val = values[idx]

                # Determine text position based on cursor location
                x_range = self.ax.get_xlim()
                x_mid = (x_range[0] + x_range[1]) / 2
                text_offset = (-100, 20) if closest_wl > x_mid else (20, 20)

                # Update cursor position
                self.cursor_dot.set_data([closest_wl], [closest_val])
                self.cursor_dot.set_color('white')
                self.cursor_dot.set_visible(self.cursor_visible)

                self.cursor_dot2.set_data([closest_wl], [closest_val])
                self.cursor_dot2.set_color('black')
                self.cursor_dot2.set_visible(self.cursor_visible)

                # Update text annotation
                self.cursor_text.xy = (closest_wl, closest_val)
                self.cursor_text.set_text(f'λ: {closest_wl:.1f}nm\nValue: {closest_val:.4f}')
                self.cursor_text.set_position(text_offset)
                self.cursor_text.set_visible(self.cursor_visible)
        except Exception:
            # Ignore cursor update errors during shutdown
            pass

    def _on_mouse_move(self, event):
        """Handle mouse movement"""
        try:
            if event.inaxes == self.ax:
                self.last_mouse_pos = (event.xdata, event.ydata)  # Store position
                self._update_cursor_position(event.xdata, event.ydata)
                if self.fig and self.fig.canvas:
                    self.fig.canvas.draw_idle()
        except Exception:
            # Ignore mouse events during shutdown
            pass

    def _on_axes_enter(self, event):
        """Show cursor when entering axes"""
        try:
            self.cursor_visible = True
            if self.cursor_dot:
                self.cursor_dot.set_visible(True)
            if self.cursor_dot2:
                self.cursor_dot2.set_visible(True)
            if self.cursor_text:
                self.cursor_text.set_visible(True)
        except Exception:
            pass

    def _on_axes_leave(self, event):
        """Hide cursor when leaving axes"""
        try:
            self.cursor_visible = False
            if self.cursor_dot:
                self.cursor_dot.set_visible(False)
            if self.cursor_dot2:
                self.cursor_dot2.set_visible(False)
            if self.cursor_text:
                self.cursor_text.set_visible(False)
            if self.fig and self.fig.canvas:
                self.fig.canvas.draw_idle()
        except Exception:
            pass

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)  # Don't wait forever

        # Safely close matplotlib figure
        try:
            if self.fig:
                plt.close(self.fig)
                self.fig = None
        except Exception:
            pass  # Ignore errors during figure cleanup

if __name__ == "__main__":
    port = Serial(sys.argv[1], 115200, timeout=0.1)
    buffer = b""

    def send_message(type, data=b""):
        port.write(build_message(type, data))


    def read_message(message_type=None):
        global buffer

        while True:
            (buffer, messages) = parse_messages(buffer + port.read())

            if messages:
                message = messages[0]

                if message_type and message["message_type"] != message_type:
                    raise ValueError("Unexpected message type")

                return message


    def cleanup():
        """Cleanup function to ensure proper shutdown"""
        print("\nCleaning up...")
        try:
            send_message(MessageType.STOP)
            port.close()
            print("Cleanup completed.")
        except:
            pass  # Ignore errors during cleanup

    atexit.register(cleanup)

    # Signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\nReceived interrupt signal, shutting down gracefully...")
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    send_message(MessageType.GET_DEVICE_ID, b"\x18")
    response = read_message(MessageType.GET_DEVICE_ID)
    print("Device ID: " + response["device_id"])

    send_message(MessageType.GET_RANGE)
    response = read_message(MessageType.GET_RANGE)
    start_wavelength = response["start_wavelength"]
    print("Start wavelength: " + str(start_wavelength) + " nm")
    print("End wavelength: " + str(response["end_wavelength"]) + " nm")

    send_message(MessageType.GET_EXPOSURE_MODE)
    response = read_message(MessageType.GET_EXPOSURE_MODE)
    print("Exposure mode: " + response["exposure_mode"].name)

    def get_data():
        print("Refreshing data...")
        send_message(MessageType.GET_DATA)

        while True:
            response = read_message()

            if response["exposure_status"] == ExposureStatus.NORMAL:
                print("Exposure time: " + str(response["exposure_time"]) + " ms")
                break
            else:
                print("Exposure status not normal: " + str(response["exposure_status"]))

        print("Stopping...")
        send_message(MessageType.STOP)

        while read_message()["message_type"] != MessageType.STOP:
            pass

        return colour.SpectralDistribution(
            {
                start_wavelength + index: value
                for index, value in enumerate(response["spectrum"])
            }
        )

    plot = RefreshableSpectralPlot(get_data(), update_interval=0.5, refresh_func=get_data)
    plot.start_plot()
