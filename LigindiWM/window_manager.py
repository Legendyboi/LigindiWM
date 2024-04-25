import Xlib
import Xlib.Xutil
import logging
import threading

class WindowManager:
    wm_detected = False
    wm_detected_mutex = threading.Lock()

    @staticmethod
    def Create(display_str):
        # 1. Open X display.
        display_c_str = display_str if display_str else None
        display = Xlib.display.Display(display_c_str)
        if not display:
            logging.error("Failed to open X display %s", display_c_str)
            return None
        # 2. Construct WindowManager instance.
        return WindowManager(display)

    def __init__(self, display):
        self.display = display
        self.root = self.display.screen().root
        self.WM_PROTOCOLS = self.display.intern_atom("WM_PROTOCOLS", False)
        self.WM_DELETE_WINDOW = self.display.intern_atom("WM_DELETE_WINDOW", False)
        self.clients = {}

    def __del__(self):
        self.display.close()

    def Run(self):
        # 1. Initialization.
        #   a. Select events on root window. Use a special error handler so we can
        #   exit gracefully if another window manager is already running.
        with WindowManager.wm_detected_mutex:
            WindowManager.wm_detected = False
            self.display.set_error_handler(self.OnWMDetected)
            self.root.change_attributes(event_mask=Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask)
            self.display.sync()
            if WindowManager.wm_detected:
                logging.error("Detected another window manager on display %s", self.display.display)
                return
        #   b. Set error handler.
        self.display.set_error_handler(self.OnXError)
        #   c. Grab X server to prevent windows from changing under us.
        self.display.grab_server()
        #   d. Reparent existing top-level windows.
        #     i. Query existing top-level windows.
        (returned_root, returned_parent, top_level_windows) = self.root.query_tree()
        #     ii. Frame each top-level window.
        for w in top_level_windows:
            self.Frame(w, True)
        #     iii. Free top-level window array.
        self.display.xfree(top_level_windows)
        #   e. Ungrab X server.
        self.display.ungrab_server()

        # 2. Main event loop.
        while True:
            # 1. Get next event.
            e = self.display.next_event()
            logging.info("Received event: %s", e)

            # 2. Dispatch event.
            if e.type == Xlib.X.CreateNotify:
                self.OnCreateNotify(e)
            elif e.type == Xlib.X.DestroyNotify:
                self.OnDestroyNotify(e)
            elif e.type == Xlib.X.ReparentNotify:
                self.OnReparentNotify(e)
            elif e.type == Xlib.X.MapNotify:
                self.OnMapNotify(e)
            elif e.type == Xlib.X.UnmapNotify:
                self.OnUnmapNotify(e)
            elif e.type == Xlib.X.ConfigureNotify:
                self.OnConfigureNotify(e)
            elif e.type == Xlib.X.MapRequest:
                self.OnMapRequest(e)
            elif e.type == Xlib.X.ConfigureRequest:
                self.OnConfigureRequest(e)
            elif e.type == Xlib.X.ButtonPress:
                self.OnButtonPress(e)
            elif e.type == Xlib.X.ButtonRelease:
                self.OnButtonRelease(e)
            elif e.type == Xlib.X.MotionNotify:
                # Skip any already pending motion events.
                while self.display.check_pending():
                    e = self.display.next_event()
                    if e.type != Xlib.X.MotionNotify or e.window != e.window:
                        break
                self.OnMotionNotify(e)
            elif e.type == Xlib.X.KeyPress:
                self.OnKeyPress(e)
            elif e.type == Xlib.X.KeyRelease:
                self.OnKeyRelease(e)
            else:
                logging.warning("Ignored event")

    def Frame(self, w, was_created_before_window_manager):
        # Visual properties of the frame to create.
        BORDER_WIDTH = 3
        BORDER_COLOR = 0xff0000
        BG_COLOR = 0x0000ff

        # We shouldn't be framing windows we've already framed.
        if w in self.clients:
            return

        # 1. Retrieve attributes of window to frame.
        x_window_attrs = w.get_attributes()

        # 2. If window was created before window manager started, we should frame
        # it only if it is visible and doesn't set override_redirect.
        if was_created_before_window_manager:
            if x_window_attrs.override_redirect or x_window_attrs.map_state != Xlib.X.IsViewable:
                return

        # 3. Create frame.
        frame = Xlib.X.create_simple_window(
            self.display,
            self.root,
            x_window_attrs.x,
            x_window_attrs.y,
            x_window_attrs.width,
            x_window_attrs.height,
            BORDER_WIDTH,
            BORDER_COLOR,
            BG_COLOR)
        # 4. Select events on frame.
        frame.change_attributes(event_mask=Xlib.X.SubstructureRedirectMask | Xlib.X.SubstructureNotifyMask)
        # 5. Add client to save set, so that it will be restored and kept alive if we
        # crash.
        self.display.add_to_save_set(w)
        # 6. Reparent client window.
        w.reparent(frame, 0, 0)  # Offset of client window within frame.
        # 7. Map frame.
        frame.map()
        # 8. Save frame handle.
        self.clients[w] = frame
        # 9. Grab universal window management actions on client window.
        #   a. Move windows with alt + left button.
        w.grab_button(
            1,
            Xlib.X.Mod1Mask,
            1,
            Xlib.X.GrabModeAsync,
            Xlib.X.GrabModeAsync,
            Xlib.X.NONE,
            Xlib.X.NONE)
        #   b. Resize windows with alt + right button.
        w.grab_button(
            3,
            Xlib.X.Mod1Mask,
            1,
            Xlib.X.GrabModeAsync,
            Xlib.X.GrabModeAsync,
            Xlib.X.NONE,
            Xlib.X.NONE)
        #   c. Kill windows with alt + f4.
        w.grab_key(
            self.display.keysym_to_keycode(Xlib.XK_F4),
            Xlib.X.Mod1Mask,
            1,
            Xlib.X.GrabModeAsync,
            Xlib.X.GrabModeAsync)
        #   d. Switch windows with alt + tab.
        w.grab_key(
            self.display.keysym_to_keycode(Xlib.XK_Tab),
            Xlib.X.Mod1Mask,
            1,
            Xlib.X.GrabModeAsync,
            Xlib.X.GrabModeAsync)

        logging.info("Framed window %s [%s]", w, frame)

    def Unframe(self, w):
        if w not in self.clients:
            return

        # We reverse the steps taken in Frame().
        frame = self.clients[w]
        # 1. Unmap frame.
        frame.unmap()
        # 2. Reparent client window.
        w.reparent(self.root, 0, 0)  # Offset of client window within root.
        # 3. Remove client window from save set, as it is now unrelated to us.
        self.display.remove_from_save_set(w)
        # 4. Destroy frame.
        frame.destroy()
        # 5. Drop reference to frame handle.
        del self.clients[w]

        logging.info("Unframed window %s [%s]", w, frame)

    def OnCreateNotify(self, e):
        pass

    def OnDestroyNotify(self, e):
        pass

    def OnReparentNotify(self, e):
        pass

    def OnMapNotify(self, e):
        pass

    def OnUnmapNotify(self, e):
        # If the window is a client window we manage, unframe it upon UnmapNotify. We
        # need the check because we will receive an UnmapNotify event for a frame
        # window we just destroyed ourselves.
        if e.window not in self.clients:
            logging.info("Ignore UnmapNotify for non-client window %s", e.window)
            return

        # Ignore event if it is triggered by reparenting a window that was mapped
        # before the window manager started.
        #
        # Since we receive UnmapNotify events from the SubstructureNotify mask, the
        # event attribute specifies the parent window of the window that was
        # unmapped. This means that an UnmapNotify event from a normal client window
        # should have this attribute set to a frame window we maintain. Only an
        # UnmapNotify event triggered by reparenting a pre-existing window will have
        # this attribute set to the root window.
        if e.event == self.root:
            logging.info("Ignore UnmapNotify for reparented pre-existing window %s", e.window)
            return

        self.Unframe(e.window)

    def OnConfigureNotify(self, e):
        pass

    def OnMapRequest(self, e):
        # 1. Frame or re-frame window.
        self.Frame(e.window, False)
        # 2. Actually map window.
        e.window.map()

    def OnConfigureRequest(self, e):
        changes = {
            'x': e.x,
            'y': e.y,
            'width': e.width,
            'height': e.height,
            'border_width': e.border_width,
            'sibling': e.above,
            'stack_mode': e.detail
        }
        if e.window in self.clients:
            frame = self.clients[e.window]
            frame.configure(**changes)
            logging.info("Resize [%s] to %s", frame, (e.width, e.height))
        e.window.configure(**changes)
        logging.info("Resize %s to %s", e.window, (e.width, e.height))

    def OnButtonPress(self, e):
        if e.window not in self.clients:
            return
        frame = self.clients[e.window]

        # 1. Save initial cursor position.
        self.drag_start_pos = (e.x_root, e.y_root)

        # 2. Save initial window info.
        (returned_root, x, y, width, height, border_width, depth) = frame.get_geometry()
        self.drag_start_frame_pos = (x, y)
        self.drag_start_frame_size = (width, height)

        # 3. Raise clicked window to top.
        frame.configure(stack_mode=Xlib.X.Above)

    def OnButtonRelease(self, e):
        pass

    def OnMotionNotify(self, e):
        if e.window not in self.clients:
            return
        frame = self.clients[e.window]
        drag_pos = (e.x_root, e.y_root)
        delta = (drag_pos[0] - self.drag_start_pos[0], drag_pos[1] - self.drag_start_pos[1])

        if e.state & Xlib.X.Button1Mask:
            # alt + left button: Move window.
            dest_frame_pos = (self.drag_start_frame_pos[0] + delta[0], self.drag_start_frame_pos[1] + delta[1])
            frame.configure(x=dest_frame_pos[0], y=dest_frame_pos[1])
        elif e.state & Xlib.X.Button3Mask:
            # alt + right button: Resize window.
            # Window dimensions cannot be negative.
            size_delta = (max(delta[0], -self.drag_start_frame_size[0]), max(delta[1], -self.drag_start_frame_size[1]))
            dest_frame_size = (self.drag_start_frame_size[0] + size_delta[0], self.drag_start_frame_size[1] + size_delta[1])
            # 1. Resize frame.
            frame.configure(width=dest_frame_size[0], height=dest_frame_size[1])
            # 2. Resize client window.
            e.window.configure(width=dest_frame_size[0], height=dest_frame_size[1])

    def OnKeyPress(self, e):
        if e.state & Xlib.X.Mod1Mask and e.keycode == self.display.keysym_to_keycode(Xlib.XK_F4):
            # alt + f4: Close window.
            #
            # There are two ways to tell an X window to close. The first is to send it
            # a message of type WM_PROTOCOLS and value WM_DELETE_WINDOW. If the client
            # has not explicitly marked itself as supporting this more civilized
            # behavior (using XSetWMProtocols()), we kill it with XKillClient().
            supported_protocols = e.window.get_wm_protocols()
            if self.WM_DELETE_WINDOW in supported_protocols:
                logging.info("Gracefully deleting window %s", e.window)
                # 1. Construct message.
                msg = Xlib.protocol.event.ClientMessage(
                    window=e.window,
                    client_type=self.WM_PROTOCOLS,
                    data=(32, [self.WM_DELETE_WINDOW, Xlib.X.CurrentTime]))
                # 2. Send message to window to be closed.
                e.window.send_event(msg)
            else:
                logging.info("Killing window %s", e.window)
                self.display.kill_client(e.window)
        elif e.state & Xlib.X.Mod1Mask and e.keycode == self.display.keysym_to_keycode(Xlib.XK_Tab):
            # alt + tab: Switch window.
            # 1. Find next window.
            i = iter(self.clients)
            while next(i) != e.window:
                pass
            try:
                next_window = next(i)
            except StopIteration:
                next_window = next(iter(self.clients))
            # 2. Raise and set focus.
            next_frame = self.clients[next_window]
            next_frame.configure(stack_mode=Xlib.X.Above)
            self.display.set_input_focus(next_window, Xlib.X.RevertToPointerRoot, Xlib.X.CurrentTime)

    def OnKeyRelease(self, e):
        pass

    def OnXError(self, display, e):
        error_text = display.protocol_event_error_string(e.error_code)
        logging.error("Received X error:\n"
                      "    Request: %d - %s\n"
                      "    Error code: %d - %s\n"
                      "    Resource ID: %d",
                      e.request_code, Xlib.X.request_code_to_name(e.request_code),
                      e.error_code, error_text,
                      e.resourceid)
        # The return value is ignored.
        return 0

    def OnWMDetected(self, display, e):
        # In the case of an already running window manager, the error code from
        # XSelectInput is BadAccess. We don't expect this handler to receive any
        # other errors.
        assert e.error_code == Xlib.X.BadAccess
        # Set flag.
        with WindowManager.wm_detected_mutex:
            WindowManager.wm_detected = True
        # The return value is ignored.
        return 0
