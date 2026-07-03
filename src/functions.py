import shutil
import zipfile
import os
import sys
from PySide6.QtGui import QFontDatabase, QFont


def zip_folder(source_folder, output_filename):
    """
    Zips a specified folder into a new zip archive.

    Args:
        source_folder (Path): The path to the folder to be zipped.
        output_filename (str): The desired name for the output zip file (without .zip extension).
    """
    try:
        # Create the zip archive
        # The 'zip' format means it will create a .zip file
        # base_dir is the directory to start archiving from
        shutil.make_archive(output_filename[:-4], 'zip', source_folder)
        print(f"Successfully created '{output_filename}.zip' from '{source_folder}'")
    except Exception as e:
        print(f"Error zipping folder: {e}")


def unzip_file(zip_filepath, extract_to_dir):
    """
    Unzips a specified .zip file to a target directory.

    Args:
        zip_filepath (str): The full path to the .zip file to be unzipped.
        extract_to_dir (str): The path to the directory where the contents
                              of the .zip file will be extracted.
    """
    if not os.path.exists(extract_to_dir):
        os.makedirs(extract_to_dir)

    with zipfile.ZipFile(zip_filepath, 'r') as zf:
        zf.extractall(extract_to_dir)


def get_folder_names(directory_path):
    """
    Returns a list of names of all immediate subfolders in a given directory.
    """
    folder_names = []
    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)
        if os.path.isdir(item_path):
            folder_names.append(item)
    return folder_names


def clear_folder(folder_path):
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except OSError as e:
                    print(f"Error deleting {file_path}: {e}")
    else:
        print(f"Folder not found or is not a directory: {folder_path}")


def get_font(file_name):
    try:
        font_id = QFontDatabase.addApplicationFont(file_name)

        if font_id == -1:
            return "Could not load custom font."

        families = QFontDatabase.applicationFontFamilies(font_id)

        if not families:
            return "Could not load custom font."

        family_name = families[0]

        return QFont(family_name, 12)

    except Exception as e:
        return "Could not load custom font."


def get_words(dictionary, flag="C"):
    words = []

    for word in dictionary:
        if flag == "C":
            words.append(word["conlang"])
        elif flag == "E":
            words.append(word["english"])

    return words


def process_font(path):
    font_id = QFontDatabase.addApplicationFont(path)

    families = QFontDatabase.applicationFontFamilies(font_id)

    try:
        return families[0]

    except Exception as e:
        return None


def get_correct_path(relative_path):
    """Gets the absolute path to a file, whether running as a script or a packaged .exe"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        # We are running as a normal Python script in an IDE
        # Get the current working directory
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
