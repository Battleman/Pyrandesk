#!/usr/bin/python3
"""
This is a good code
"""
import argparse
import fnmatch
import getpass
import os
import random
import re
import stat
import subprocess
import sys
import time
from io import BytesIO
from pprint import pprint

import requests
import yaml
# -*- coding: utf-8 -*-
from PIL import Image

####
# Helpers
###


def download_from_url(link):
    """
    Given an url, download binary image
    """
    try:
        req = requests.get(link)
        if not req.ok:
            print("Failed to get {}. Reason: HTTP error {}, '{}'".format(
                link, req.status_code, req.reason))
            return False
    except requests.exceptions.MissingSchema as exception:
        print("Invalid URL schema:", exception)
        return False
    except requests.exceptions.ConnectionError as exception:
        print("Connection error:", exception)
        return False
    return req.content


def get_mimetype_from_json(json):
    """
    Determines extension (jpeg, png,...) file should have

    This information exists in the metadata. We parse it to obtain the
    information
    """
    try:
        # extension should be 'image/jpeg' or 'image/png' or...
        extension = json['type'].split('/')[1]
    except KeyError:
        print("Json might be wrong:\n", json,
              "\nCheck if a 'type' field is present")
        extension = "unknown"
    return extension


class RandomImgurDesktop():
    """
        Define basic functions
    """

    def __init__(self):
        self.albums = set()
        self.image_counter = 0
        self.sfw = False
        config_file = 'config.yaml'
        if os.path.isfile(config_file):
            with open(config_file) as file:
                config = yaml.load(file)
        else:
            pprint("Error reading config file. Please ensure you have a \
                'config.yaml' file at the same location as this script.")
            sys.exit()
        user = getpass.getuser()
        self.client_id = config['client_id']
        self.clientsecret = config['client_secret']
        self.access_token = config['access_token']
        self.cache_size = config['default_cache_size']
        self.cache_dir = config['default_cache_dir'].replace(
            '<USERNAME>', user)

    def get_json(self, album_hash):
        """
        Query the given url, and return a
        json-interpreted version of the content
        """
        print(album_hash)
        payload = {"Authorization": "Client-ID " + self.client_id}
        response = requests.get(
            "https://api.imgur.com/3/album/" + str(album_hash),
            headers=payload).json()

        if response['success']:
            # print("Data was successfully loaded")
            return response['data']

        print(
            "Error querying:",
            response['status'],
            response['data']['error'])
        return False

    def random_select_album(self):
        """
        Return a random entry in the table of albums

        Simple takes a random entry in the list of album (of the current
        object) and returns it. Entries should always be album's hashes,
        but this function does not check it.

        Return:
            A string, that is the hash of an album.
        """
        return random.sample(self.albums, 1)[0]

    def init_cache(self):
        """
        Ensures cache folder exists and that the cache is not too full
        at startup

        Checks there are less files in cache than specified size.
        If too many, removes oldest ones to have fitting size.
        """
        print("Initializing cache at", self.cache_dir)
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except OSError as error:
                print("Error creating cache folder:")
                raise error

        file_list = []
        keep_number = re.compile(r".*image_(\d+)\..{1,5}$")
        new_counter = 0
        if self.cache_size > 0:  # strict cache limit
            for filename in os.listdir(self.cache_dir):
                if fnmatch.fnmatch(filename, 'image_*'):
                    absolute = self.cache_dir+filename
                    file_list.append((os.stat(absolute)[stat.ST_MTIME],
                                      absolute))

            if file_list:  # list is not empty
                file_list.sort(key=lambda a: a[0], reverse=True)
                to_delete = len(file_list)-self.cache_size
                if to_delete > 0:
                    for entry in file_list[-to_delete:]:
                        print(
                            "Cache too full, cleaning\
                                file {}".format(entry[1]))
                        os.remove(entry[1])
                        file_list.remove(entry)
        else:
            for filename in os.listdir(self.cache_dir):
                if fnmatch.fnmatch(filename, 'image_*'):
                    absolute = self.cache_dir+filename
                    file_list.append(filename)
            if file_list:
                file_list.sort()
                last = file_list[-1]
                new_counter = int(keep_number.sub(r"\1", last))

        self.image_counter = new_counter

    def update_background(self, filename):
        """
        Use dconf to update the background
        """
        key = "/org/gnome/desktop/background/picture-uri"
        value = "'file://"+filename+"'"
        # print("Calling", "dconf", "write", key, value)
        subprocess.Popen([
            "dconf", "write", key, value
        ])

        ######
        # personal need for my conky.
        # You can probably safely delete this.
        subprocess.Popen([
            "feh", "--bg-fill", filename
        ])
        #####

        print("Background modified")

    def no_internet(self):
        """
        Called when internet is not activated or imgur is unreachable

        This method will basically comport as the original version, but will
        only use cached images
        """
        file_list = []
        for filename in os.listdir(self.cache_dir):
            if fnmatch.fnmatch(filename, 'image_*'):
                absolute = self.cache_dir+filename
                file_list.append(absolute)
        print(file_list)
        if len(file_list) < 0:
            return False
        random_cached_file = file_list[random.randint(0, len(file_list)-1)]
        self.update_background(random_cached_file)
        return True

    def download_random_image(self, album_data):
        """
        From a data response (list of json), downloads one image at random

        Takes the json data of an album (list of json, one entry per
        image), picks one element at random, downloads it, save it
        and return the absolute path to the image

        Keyword argument
            --album_data: A list of json. Each entry is the
                metadata of one image
        """
        random_image_metadata = album_data['images'][random.randint(
            0,
            len(album_data['images'])-1)]
        image = download_from_url(random_image_metadata['link'])
        extension = get_mimetype_from_json(random_image_metadata)
        filename = self.save_image(image, extension)
        return filename

    def save_image(self, binary, extension):
        """
        Save an image with given extension to the cache directory of the object
        """
        i = Image.open(BytesIO(binary))
        filename = self.cache_dir + "image_{:05}.{}".format(
            self.image_counter, extension)
        try:
            i.save(filename)
        except FileNotFoundError:
            print("Impossible to save at location {},".format(filename) +
                  "ensure the folder exists.")
            return False
        except PermissionError:
            print("Permission to write at location {}".format(filename) +
                  "was denied, ensure you have correct rights.")
            return False

        self.image_counter += 1
        if self.image_counter == self.cache_size:
            print("Reached max cache size ({})".format(self.cache_size) +
                  ", starting over")
            self.image_counter = 0

        return filename

    def add_album(self, album):
        """
        add the hash of an album to the directory of albums
        """
        # only hash is given
        regex = re.compile(r"^\w+$")
        if regex.match(album):
            self.albums.add(album)
            return True
        # whole URL
        regex = re.compile(r"^https://imgur.com/a/(\w+)\s*$")
        if regex.match(album):
            album = regex.sub(r"\1", album)
            # print(album)
            self.albums.add(album)
            return True

        print("This url album is not valid:", album)
        return False

    def add_multiple_albums(self, filename):
        """
        iterates through a file to add the url
        to the directory of albums. Lets add_album handle the parsing and
        checking
        """
        if os.path.isfile(filename):
            with open(filename, "r") as file:
                for line in file.readlines():
                    # print("Trying to add line", line.replace('\n', ''))
                    self.add_album(line)
            return True
        print("Non existing file \""+filename+"\"")
        return False


def main():
    """
    Main of the script
    """
    sleeptime = 60
    try:
        random_imgur_desktop = RandomImgurDesktop()
    except OSError:
        return -1

    ###
    # Creation of arguments parser
    ###
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--album",
        help="Specify a unique album where to pick the images.\
         Incompatible with -A")

    parser.add_argument(
        "-A", "--galleries",
        help="Specify a file where to find all the galleries\
            you would like to pick from.Only specify absolute path.\
            Incompatible with -a.")

    parser.add_argument(
        "-cS", "--cache-size",
        help="Specify the number of images to\
            keep in cache. Default to 10. 0 means no limit")

    parser.add_argument(
        "-s", "--safe-for-work", action="store_true",
        help="Don't download pictures marked as NSFW ('not safe wor work',\
        that is images with potentially adult content)"
    )

    parser.add_argument(
        "-cD", "--cache-directory",
        help="Specify where you wish to keep your cached images.\
        No relative path.\
        Default to /home/<username>/.cache/random-imgur-image/")

    args = parser.parse_args()

    ####
    # Take actions according to arguments
    ###
    if args.album:
        random_imgur_desktop.add_album(args.album)
    elif args.galleries:
        galleries = args.galleries
        if "../" in galleries:
            print("No backward relative path in file containing albums!")
            return -1
        if not random_imgur_desktop.add_multiple_albums(galleries):
            print("Impossible to read file. Exiting.")
            return -1
    else:
        print("You need to specify at least one album (with -a or -A)")
        return -1

    if args.cache_size:
        cache_size = args.cache_size
        try:
            cache_size = int(cache_size)
        except ValueError:
            print("Cache size must be an integer. Using default value.")
        else:
            if cache_size < 0:
                print("Cache size must be greater or equal to 0.\
                Using default value")
            else:
                random_imgur_desktop.cache_size = cache_size

    if args.cache_directory:
        galleries = args.galleries
        if "../" in galleries:
            print("No backward relative path in galleries !")
            return -1
        random_imgur_desktop.cache_dir = args.cache_directory

    random_imgur_desktop.sfw = args.safe_for_work
    random_imgur_desktop.init_cache()

    while True:
        try:
            conn = requests.head("http://www.imgur.com")
        except requests.exceptions.ConnectionError:
            # no internet connection
            print("No internet :( trying to use local cache...")
            if not random_imgur_desktop.no_internet():
                print("No internet and cache is empty, quitting")
                return -1
        else:
            if conn.ok:
                print("Connection ok, going normal")
                album_url = random_imgur_desktop.random_select_album()
                album_json = random_imgur_desktop.get_json(album_url)
                image_filename = random_imgur_desktop.download_random_image(
                    album_json)
                random_imgur_desktop.update_background(image_filename)
            else:
                # imgur is not accessible
                print("Imgur not accessible ? trying to use local cache...")
                if not random_imgur_desktop.no_internet():
                    print("Imgur not accessible and cache is empty, quitting")
                    return -1
        finally:
            time.sleep(sleeptime)
    return 0


if __name__ == '__main__':
    main()
