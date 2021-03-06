#! /usr/bin/python3

from bs4 import BeautifulSoup
import os
import re
import urllib.request
from datetime import date
from pathlib import Path
import urllib.request

# Strings for 4chan threads
thread_title = None
board_name = None

# Regular expression patterns and engines
PATTERN_TITLE = r"\/(?P<board>\w+)\/ - (?P<title>\w+(\s+\w+)*)"
RE_TITLE = re.compile(PATTERN_TITLE)

PATTERN_FILENAME = r"(?P<filename>\d+\.\w+)$"   # will be set later
RE_LINK_FILENAME = None

PATTERN_FOURCHAN_URL = r'(https?:\/\/)?boards.4chan.org\/(?P<board>\w+)\/thread\/(?P<thread_id>\d+)'
RE_FOURCHAN_URL = None

PATTERN_MEDIA_URL = r'i\.4cdn\.org\/\w+\/\w+\.\w+'
RE_MEDIA_URL = None

# For downloading the URL page
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:53.0) Geckp/20100101 Firefox/53.0"
HEADERS = {"User-Agent": USER_AGENT}


DOWNLOADS_FOLDER = "downloaded"
DOWNLOAD_ANYTHING = True
# folder_name = ""

thread_id = ""
folder_name_autogenerated = False


def main():
    # compile regexp engines
    global RE_FOURCHAN_URL
    RE_FOURCHAN_URL = re.compile(PATTERN_FOURCHAN_URL)
    global RE_MEDIA_URL
    RE_MEDIA_URL = re.compile(PATTERN_MEDIA_URL)
    global RE_LINK_FILENAME
    RE_LINK_FILENAME = re.compile(PATTERN_FILENAME)

    url = prompt_url()
    webpage = download_url_as_string(url)

    # important for autogenerating folder names
    global board_name
    board_name = retrieve_board_name(url)
    global thread_id
    thread_id = retrieve_thread_id(url)
    print("Thread board:", board_name)
    print("Thread ID:", thread_id)

    soup = BeautifulSoup(webpage, "lxml")

    media_links = []
    for media in soup.find_all(has_image_or_vid):
        media_links.append(get_media_url(media["href"]))

    print("There are", len(media_links), "media files found")
    print("Media Links:")
    print('\n'.join(media_links))

    if DOWNLOAD_ANYTHING:
        # create downloads folder if not exist yet (first ever run)
        if not (os.path.exists(DOWNLOADS_FOLDER)):
            os.makedirs(DOWNLOADS_FOLDER)

        combine = False # rename this to 'download'
        folder_name = ""
        folder_exists = False
        while combine == False and len(folder_name) < 1:
            folder_name = prompt_folder_name()
            path = os.path.join(".", DOWNLOADS_FOLDER, folder_name)

            if os.path.exists(path):
                print("FOLDER EXISTS")
                folder_exists = True
                if folder_name_autogenerated == False:
                    combine = prompt_combine_folders()
                else:
                    combine = True
            else:
                # combine regardless, even if folder does not exist
                # so we can download
                combine = True
                os.makedirs(path)

        if combine:
            download_links = None
            download = True
            if folder_exists:
                # find files that have not been downloaded yet
                download_links = subtract_links_paths(media_links, path)
                if len(download_links) > 0:
                    print("Found", len(download_links), "files that have not been downloaded")
                else:
                    print("Everything up to date")
                    download = False
            else:
                download_links = media_links

            if download:
                print("Downloading to", folder_name)
                download_media_links(download_links, folder_name)
        else:
            print("Will not download")

        print("Program finished!")


def has_image_or_vid(tag):
    if tag.name == "a" and tag.has_attr("class"):
        for classVal in tag["class"]:
            if classVal == "fileThumb":
                return True
    return False

def retrieve_thread_title(soup):
    title_text = soup.title.get_text()
    print(title_text)

    title = ""
    if title_text is not None:
        matches = RE_TITLE.search(title_text)
        if matches is not None:
            title = title_match.group("title")
    return title

def retrieve_board_name(url):
    board = ""
    if url is not None:
        board_match = RE_FOURCHAN_URL.search(url)

        if board_match is not None:
            board = board_match.group("board")
    return board

def retrieve_thread_id(url):
    tid = ""
    if url is not None:
        matches = RE_FOURCHAN_URL.search(url)

        if matches is not None:
            tid = matches.group("thread_id")
    return tid

def prompt_url():
    urlretrieved = None
    urlvalid = False
    while not urlvalid:
        userin = input("Enter the URL you want to download from: ")
        matches = RE_FOURCHAN_URL.match(userin)
        if matches is not None:
            if len(matches.groups()) > 0:
                urlvalid = True
                urlretrieved = matches.group()
    return urlretrieved

def prompt_folder_name():
    global folder_name_autogenerated
    folder_name = ""
    userin = input("Enter folder name for files to download (empty = autogenerated name):")
    if len(userin) > 0:
        folder_name_autogenerated = False
        folder_name = userin.strip()
    else:
        folder_name_autogenerated = True
        today = date.today()
        folder_name = today.strftime("%y%m%d") + board_name + thread_id
    return folder_name

def prompt_combine_folders():
    repeat_prompt = True
    combine = False
    while repeat_prompt == True:
        userin = input("Do you want to combine downloads with this folder? (Y/N):")
        userin = userin.lower()
        if 'y' in userin:
            combine = True
            repeat_prompt = False
        elif 'n' in userin:
            combine = False
            repeat_prompt = False
        else:
            repeat_prompt = True

    return combine


def download_media_links(links, foldername):
    num_links = len(links)
    for i in range(num_links):
        link = links[i]
        save_as_filename = None
        if foldername is not None:
            save_as_filename = os.path.join(DOWNLOADS_FOLDER, foldername, get_filename_from_link(link))
        else:
            save_as_filename = os.path.join(DOWNLOADS_FOLDER, get_filename_from_link(link))

        if not link.startswith("http://"):
            link = "http://" + link
            # avoid errors with downloading

        print("Downloading file", i + 1, "of", num_links, link + "...", end=' ')
        urllib.request.urlretrieve(link, save_as_filename)
        print("done!")
    print("=====Finished downloading!=====")



"""
 Subtract filename lists by filenames of path.
"""
def subtract_links_paths(links, path):
    existing_files = []
    folder_path = Path(path)
    for p in folder_path.iterdir():
        if not p.is_dir():
            existing_files.append(str(p))

    media_links = list(links)

    for i in range(len(media_links) - 1, -1, -1):
        link_ref = media_links[i]
        media_fn = get_filename_from_link(link_ref)
        for o in range(len(existing_files) - 1, -1, -1):
            existing_ref = existing_files[o]
            existing_fn = get_filename_from_link(existing_files[o])
            if media_fn == existing_fn:
                media_links.remove(link_ref)
                existing_files.remove(existing_ref)
                break

    return media_links

def get_filename_from_link(link):
    m = RE_LINK_FILENAME.search(link)
    return m.group("filename")

def get_media_url(link):
    m = RE_MEDIA_URL.search(link)
    return m.group()

# Retrieves specified URL (url) as a string (UTF-8)
def download_url_as_string(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request) as response:
        html = response.read().decode("utf-8")
    return html










if __name__ == "__main__":
    main()
