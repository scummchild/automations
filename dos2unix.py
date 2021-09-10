
def dos2unix(file_path):
    """This is copied from Stack Overflow pretty much as is
    Opens a file, converts the line endings to unix, and
    then overwrites the file.

    """
    # replacement strings
    WINDOWS_LINE_ENDING = b'\r\n'
    UNIX_LINE_ENDING = b'\n'

    with open(file_path, 'rb') as open_file:
        content = open_file.read()

    content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)

    with open(file_path, 'wb') as open_file:
        open_file.write(content)
