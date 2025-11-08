import shutil
import zipfile
import os

def zip_folder(source_folder, output_filename):
    """
    Zips a specified folder into a new zip archive.

    Args:
        source_folder (str): The path to the folder to be zipped.
        output_filename (str): The desired name for the output zip file (without .zip extension).
    """
    try:
        # Create the zip archive
        # The 'zip' format means it will create a .zip file
        # base_dir is the directory to start archiving from
        shutil.make_archive(output_filename, 'zip', source_folder)
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
