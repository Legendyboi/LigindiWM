import re
from typing import Tuple

class XEvent:
    def __init__(self, event_type: int, **kwargs):
        self.type = event_type
        for key, value in kwargs.items():
            setattr(self, key, value)

def ToString(e: XEvent) -> str:
    X_EVENT_TYPE_NAMES = [
        "",
        "",
        "KeyPress",
        "KeyRelease",
        "ButtonPress",
        "ButtonRelease",
        "MotionNotify",
        "EnterNotify",
        "LeaveNotify",
        "FocusIn",
        "FocusOut",
        "KeymapNotify",
        "Expose",
        "GraphicsExpose",
        "NoExpose",
        "VisibilityNotify",
        "CreateNotify",
        "DestroyNotify",
        "UnmapNotify",
        "MapNotify",
        "MapRequest",
        "ReparentNotify",
        "ConfigureNotify",
        "ConfigureRequest",
        "GravityNotify",
        "ResizeRequest",
        "CirculateNotify",
        "CirculateRequest",
        "PropertyNotify",
        "SelectionClear",
        "SelectionRequest",
        "SelectionNotify",
        "ColormapNotify",
        "ClientMessage",
        "MappingNotify",
        "GeneralEvent",
    ]

    if e.type < 2 or e.type >= len(X_EVENT_TYPE_NAMES):
        return f"Unknown ({e.type})"

    properties = []
    if e.type == 17:  # CreateNotify
        properties.extend([
            ("window", ToString(e.xcreatewindow.window)),
            ("parent", ToString(e.xcreatewindow.parent)),
            ("size", Size(e.xcreatewindow.width, e.xcreatewindow.height).ToString()),
            ("position", Position(e.xcreatewindow.x, e.xcreatewindow.y).ToString()),
            ("border_width", str(e.xcreatewindow.border_width)),
            ("override_redirect", str(bool(e.xcreatewindow.override_redirect))),
        ])
    elif e.type == 18:  # DestroyNotify
        properties.append(("window", ToString(e.xdestroywindow.window)))
    elif e.type == 19:  # MapNotify
        properties.extend([
            ("window", ToString(e.xmap.window)),
            ("event", ToString(e.xmap.event)),
            ("override_redirect", str(bool(e.xmap.override_redirect))),
        ])
    elif e.type == 20:  # UnmapNotify
        properties.extend([
            ("window", ToString(e.xunmap.window)),
            ("event", ToString(e.xunmap.event)),
            ("from_configure", str(bool(e.xunmap.from_configure))),
        ])
    elif e.type == 22:  # ConfigureNotify
        properties.extend([
            ("window", ToString(e.xconfigure.window)),
            ("size", Size(e.xconfigure.width, e.xconfigure.height).ToString()),
            ("position", Position(e.xconfigure.x, e.xconfigure.y).ToString()),
            ("border_width", str(e.xconfigure.border_width)),
            ("override_redirect", str(bool(e.xconfigure.override_redirect))),
        ])
    elif e.type == 21:  # ReparentNotify
        properties.extend([
            ("window", ToString(e.xreparent.window)),
            ("parent", ToString(e.xreparent.parent)),
            ("position", Position(e.xreparent.x, e.xreparent.y).ToString()),
            ("override_redirect", str(bool(e.xreparent.override_redirect))),
        ])
    elif e.type == 20:  # MapRequest
        properties.append(("window", ToString(e.xmaprequest.window)))
    elif e.type == 23:  # ConfigureRequest
        properties.extend([
            ("window", ToString(e.xconfigurerequest.window)),
            ("parent", ToString(e.xconfigurerequest.parent)),
            ("value_mask", XConfigureWindowValueMaskToString(e.xconfigurerequest.value_mask)),
            ("position", Position(e.xconfigurerequest.x, e.xconfigurerequest.y).ToString()),
            ("size", Size(e.xconfigurerequest.width, e.xconfigurerequest.height).ToString()),
            ("border_width", str(e.xconfigurerequest.border_width)),
        ])
    elif e.type == 4 or e.type == 5:  # ButtonPress or ButtonRelease
        properties.extend([
            ("window", ToString(e.xbutton.window)),
            ("button", str(e.xbutton.button)),
            ("position_root", Position(e.xbutton.x_root, e.xbutton.y_root).ToString()),
        ])
    elif e.type == 6:  # MotionNotify
        properties.extend([
            ("window", ToString(e.xmotion.window)),
            ("position_root", Position(e.xmotion.x_root, e.xmotion.y_root).ToString()),
            ("state", str(e.xmotion.state)),
            ("time", str(e.xmotion.time)),
        ])
    elif e.type == 2 or e.type == 3:  # KeyPress or KeyRelease
        properties.extend([
            ("window", ToString(e.xkey.window)),
            ("state", str(e.xkey.state)),
            ("keycode", str(e.xkey.keycode)),
        ])

    properties_string = ", ".join(f"{key}: {value}" for key, value in properties)
    return f"{X_EVENT_TYPE_NAMES[e.type]} {{ {properties_string} }}"

def XConfigureWindowValueMaskToString(value_mask: int) -> str:
    masks = []
    if value_mask & 1:
        masks.append("X")
    if value_mask & 2:
        masks.append("Y")
    if value_mask & 4:
        masks.append("Width")
    if value_mask & 8:
        masks.append("Height")
    if value_mask & 16:
        masks.append("BorderWidth")
    if value_mask & 32:
        masks.append("Sibling")
    if value_mask & 64:
        masks.append("StackMode")
    return "|".join(masks)

def XRequestCodeToString(request_code: int) -> str:
    X_REQUEST_CODE_NAMES = [
        "",
        "CreateWindow",
        "ChangeWindowAttributes",
        "GetWindowAttributes",
        "DestroyWindow",
        "DestroySubwindows",
        "ChangeSaveSet",
        "ReparentWindow",
        "MapWindow",
        "MapSubwindows",
        "UnmapWindow",
        "UnmapSubwindows",
        "ConfigureWindow",
        "CirculateWindow",
        "GetGeometry",
        "QueryTree",
        "InternAtom",
        "GetAtomName",
        "ChangeProperty",
        "DeleteProperty",
        "GetProperty",
        "ListProperties",
        "SetSelectionOwner",
        "GetSelectionOwner",
        "ConvertSelection",
        "SendEvent",
        "GrabPointer",
        "UngrabPointer",
        "GrabButton",
        "UngrabButton",
        "ChangeActivePointerGrab",
        "GrabKeyboard",
        "UngrabKeyboard",
        "GrabKey",
        "UngrabKey",
        "AllowEvents",
        "GrabServer",
        "UngrabServer",
        "QueryPointer",
        "GetMotionEvents",
        "TranslateCoords",
        "WarpPointer",
        "SetInputFocus",
        "GetInputFocus",
        "QueryKeymap",
        "OpenFont",
        "CloseFont",
        "QueryFont",
        "QueryTextExtents",
        "ListFonts",
        "ListFontsWithInfo",
        "SetFontPath",
        "GetFontPath",
        "CreatePixmap",
        "FreePixmap",
        "CreateGC",
        "ChangeGC",
        "CopyGC",
        "SetDashes",
        "SetClipRectangles",
        "FreeGC",
        "ClearArea",
        "CopyArea",
        "CopyPlane",
        "PolyPoint",
        "PolyLine",
        "PolySegment",
        "PolyRectangle",
        "PolyArc",
        "FillPoly",
        "PolyFillRectangle",
        "PolyFillArc",
        "PutImage",
        "GetImage",
        "PolyText8",
        "PolyText16",
        "ImageText8",
        "ImageText16",
        "CreateColormap",
        "FreeColormap",
        "CopyColormapAndFree",
        "InstallColormap",
        "UninstallColormap",
        "ListInstalledColormaps",
        "AllocColor",
        "AllocNamedColor",
        "AllocColorCells",
        "AllocColorPlanes",
        "FreeColors",
        "StoreColors",
        "StoreNamedColor",
        "QueryColors",
        "LookupColor",
        "CreateCursor",
        "CreateGlyphCursor",
        "FreeCursor",
        "RecolorCursor",
        "QueryBestSize",
        "QueryExtension",
        "ListExtensions",
        "ChangeKeyboardMapping",
        "GetKeyboardMapping",
        "ChangeKeyboardControl",
        "GetKeyboardControl",
        "Bell",
        "ChangePointerControl",
        "GetPointerControl",
        "SetScreenSaver",
        "GetScreenSaver",
        "ChangeHosts",
        "ListHosts",
        "SetAccessControl",
        "SetCloseDownMode",
        "KillClient",
        "RotateProperties",
        "ForceScreenSaver",
        "SetPointerMapping",
        "GetPointerMapping",
        "SetModifierMapping",
        "GetModifierMapping",
        "NoOperation",
    ]
    return X_REQUEST_CODE_NAMES[request_code]

class Size(Tuple[int, int]):
    def __new__(cls, width: int, height: int):
        return super().__new__(cls, (width, height))

    def ToString(self) -> str:
        return f"{self[0]}x{self[1]}"

class Position(Tuple[int, int]):
    def __new__(cls, x: int, y: int):
        return super().__new__(cls, (x, y))

    def ToString(self) -> str:
        return f"({self[0]}, {self[1]})"
