from pathlib import Path

PATH_TO_DATA = Path('data')

# Files with input data for DB (name, autoincrement)
#  if "autoincrement" then the ID (first field) should be skipped: [1:]
FILES = [('Dirs.txt', 1),
         ('VirtDirs.txt', 0),
         ('Files.txt', 1),
         ('VirtFiles.txt', 0),
         ('Comments.txt', 1),
         ('Extensions.txt', 1),
         ('ExtGroups.txt', 1),
         ('FileAuthor.txt', 0),
         ('Tags.txt', 1),
         ('FileTag.txt', 0),
         ]


