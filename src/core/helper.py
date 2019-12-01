# helper.py

from collections import namedtuple

from PyQt5.QtGui import QFontDatabase

# Shared things
# immutable
EXT_ID_INCREMENT = 100000
Fields = namedtuple('Fields', 'fields headers indexes')
# fields: str  - tuple of fields (in table Files) to be displayed in the view filesList
# headers: str - tuple of headers in the view filesList
# indexes: int - order of fields

REAL_FOLDER, VIRTUAL_FOLDER, REAL_FILE, VIRTUAL_FILE = range(4)
MimeTypes = ["application/x-folder-list",
             "application/x-folder-list/virtual",
             "application/x-file-list",
             "application/x-file-list/virtual"]

DROP_NO_ACTION, DROP_COPY_FOLDER, DROP_MOVE_FOLDER, DROP_COPY_FILE, DROP_MOVE_FILE = (0, 1, 2, 4, 8)


# mutable
Shared = {'AppFont': QFontDatabase.systemFont(QFontDatabase.GeneralFont),
          'AppWindow': None,
          'Controller': None,
          'DB choice dialog': None,
          'DB connection': None,
          'DB utility': None}


def get_file_extension(file_name):
    if file_name.rfind('.') > 0:
        return str.lower(file_name.rpartition('.')[2])
    return ''

def show_message(message, time=3000):
    Shared['AppWindow'].ui.statusbar.showMessage(message, time)
