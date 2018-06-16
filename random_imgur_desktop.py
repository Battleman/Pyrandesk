#!/usr/bin/python3
"""
This is a good code
"""
import argparse
import getpass
import random
import re
import sys
import time
from io import BytesIO
from os.path import isfile
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


def get_extension_from_json(json):
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
        self.albums = []
        self.image_counter = 0
        config_file = 'config.yaml'
        if isfile(config_file):
            with open(config_file) as file:
                config = yaml.load(file)
        else:
            pprint("Error reading config file. Please ensure you have a \
                'config.yaml' file at the same location as this script.")
            sys.exit()
        user = getpass.getuser()
        self.client_id = config['client_id']
        self.clientsecret = config['client_secret']
        self.cache_size = config['default_cache_size']
        self.cache_dir = config['default_cache_dir'].replace(
            '<USERNAME>', user)
        pprint(self.cache_dir)

    def get_json(self, album_hash):
        """
        Query the given url, and return a
        json-interpreted version of the content
        """
        payload = {"client_id": self.client_id}
        response = requests.get(
            "https://api.imgur.com/3/album/" + str(album_hash),
            params=payload).json()

        if response['success']:
            print("Data was successfully loaded")
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
        some_index = random.randint(0, len(self.albums)-1)
        return self.albums[some_index]

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
        extension = get_extension_from_json(random_image_metadata)
        filename = self.save_image(image, extension)
        return filename

    def save_image(self, binary, extension):
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
        return filename

    def add_album(self, album):
        """
        add the hash of an album to the directory of albums
        """
        # only hash is given
        regex = re.compile(r"^\w+$")
        if regex.match(album):
            self.albums.append(album)
            return True
        # whole URL
        regex = re.compile(r"^http.?://imgur.com/a/(\w+)$")
        if regex.match(album):
            album = regex.sub(r"\1", album)
            print(album)
            self.albums.append(album)
            return True

        print("This url album is not valid")
        return False

    def add_multiple_albums(self, filename):
        """
        iterates through a file to add the url
        to the directory of albums. Lets add_album handle the parsing and
        checking
        """
        if isfile(filename):
            with open(filename) as file:
                for line in file.readlines():
                    self.add_album(line)
                    return True
        print("Non existing file \""+filename+"\"")
        return False


def main():
    """
    Main of the script
    """
    sleeptime = 20
    random_imgur_desktop = RandomImgurDesktop()

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
        "-c", "--cache-size",
        help="Specify the number of images to\
            keep in cache. Default to 10")

    parser.add_argument(
        "-s", "--safe-for-work",
        help="Don't download pictures marked as NSFW ('not safe wor work',\
        that is images with potentially adult content)"
    )

    parser.add_argument(
        "-p", "--cache-directory",
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
            print("No relative path in galleries !")
            return -1
    else:
        print("You need to specify at least one album")
        return -1
    if args.cache_size:
        cache_size = args.cache_size
        try:
            cache_size = int(cache_size)
        except ValueError:
            print("Cache size must be an integer")
            return -1
        if cache_size < 0:
            print("Cache size must be greater or equal to 0")
    if args.cache_directory:
        galleries = args.galleries
        if "../" in galleries:
            print("No relative path in galleries !")
            return -1

    while True:
        album = random_imgur_desktop.random_select_album()
        # album = hash ≃ k3AMe
        json = random_imgur_desktop.get_json(album)
        # json = album metadata + list of images metadata
        image = random_imgur_desktop.download_random_image(json)
        print(image)
        time.sleep(sleeptime)
    return 0


if __name__ == '__main__':
    main()
