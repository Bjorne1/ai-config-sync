import subprocess
import sys


def hidden_subprocess_kwargs() -> dict[str, object]:
    if sys.platform != "win32":
        return {}
    kwargs: dict[str, object] = {}
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if create_no_window:
        kwargs["creationflags"] = create_no_window
    startup_info_cls = getattr(subprocess, "STARTUPINFO", None)
    startf_use_show_window = getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    if startup_info_cls and startf_use_show_window:
        startup_info = startup_info_cls()
        startup_info.dwFlags |= startf_use_show_window
        startup_info.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startup_info
    return kwargs
