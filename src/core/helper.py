# helper.py

import sys
import subprocess
import webbrowser
from collections import namedtuple


Fields = namedtuple("Fields", "fields headers indexes")
# fields: str  - tuple of fields (in table Files) to be displayed in the view filesList
# headers: str - tuple of headers in the view filesList
# indexes: int - order of fields

REAL_FOLDER, VIRTUAL_FOLDER, REAL_FILE, VIRTUAL_FILE = range(4)
MimeTypes = [
    "application/x-folder-list",
    "application/x-folder-list/virtual",
    "application/x-file-list",
    "application/x-file-list/virtual",
]

DROP_NO_ACTION, DROP_COPY_FOLDER, DROP_MOVE_FOLDER, \
    DROP_COPY_FILE, DROP_MOVE_FILE = (0, 1, 2, 4, 8,)


def open_file_or_folder(path: str):
    """
    Open file with default programm 
    or folder with default file manager
    @param: path
    """
    if sys.platform == "win32":
        return webbrowser.open(path)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        return subprocess.call([opener, path]) == 0
