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
# Constants
###
ALPHACODERS_API_URL = "https://wall.alphacoders.com/api2.0/get.php"
IMGUR_API_URL = "https://api.imgur.com/3/album/"

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
    if 'type' in json:
        # extension should be 'image/jpeg' or 'image/png' or...
        extension = json['type'].split('/')[1]
    elif 'file_type' in json:
        extension = json['file_type']
    else:
        extension = 'unknown'
    return extension


class RandomImgurDesktop():
    """
        Define basic functions
    """

    def __init__(self):
        self.source = dict()
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
        self.imgur_client_id = config['imgur_client_id']
        self.alphacoders_api_key = config['alphacoders_api_key']
        self.cache_size = config['default_cache_size']
        self.cache_dir = config['default_cache_dir'].replace(
            '<USERNAME>', user)
        self.alphacoders_categories,\
            self.alphacoders_cat_ids = self.get_alphacoders_categories()

    def get_json_imgur(self, album_hash):
        """
        Query the given url, and return a
        json-interpreted version of the content
        """
        payload = {"Authorization": "Client-ID " + self.imgur_client_id}
        response = requests.get(
            IMGUR_API_URL + str(album_hash),
            headers=payload).json()

        if response['success']:
            # print("Data was successfully loaded")
            return response['data']

        print(
            "Error querying:",
            response['status'],
            response['data']['error'])
        return False

    def get_json_alphacoders(self, category):
        """
        Query alphacoders to return images in a given category
        """
        # print(category)
        if category == "All":
            spec_params = {
                "method": "random",
                "count": 1,
            }
        else:
            # May need to get count of images ?
            # count_params = {
            #     "auth": self.alphacoders_api_key,
            #     "method": "category_count",
            #     "id": self.alphacoders_categories.index(category)+1
            # }
            # count = requests.get(ALPHACODERS_API_URL,
            #                      params=count_params).json()
            # print(count)
            spec_params = {
                "method": "category",
                "id": self.alphacoders_cat_ids[
                    self.alphacoders_categories.index(category)],
                "page": random.randint(1, 1000),
                "check_last": 1
            }
        params = {
            "auth": self.alphacoders_api_key,
            "info_level": 2,
        }
        params.update(spec_params)
        # print(params)
        response = requests.get(
            ALPHACODERS_API_URL,
            params=params).json()
        if response['success']:
            return response
        return False

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

        # print("Background modified")

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

    def check_image_conditions_json(self, image_metadata):
        """
        Checks if a given image metadata pass all the required tests (sfw,
        size,...)
        """
        if self.sfw and image_metadata['nsfw']:
            # user wants sfw, image is not
            return False
        return True

    def download_random_image(self):
        """
        Picks a random source and downloads one image from there (at random)

        Chooses a source, one picks one element at random, downloads it
        save it and return the absolute path to the cached image

        Keyword argument
            --album_data: A list of json. Each entry is the
                metadata of one image
        """
        # print("Trying a random image")
        website = random.sample(list(self.source), 1)[0]
        # print(website)
        random_source = random.sample(self.source[website], 1)[0]
        # print(random_source)
        if website == "Imgur":
            album_data = self.get_json_imgur(random_source)
            random_image_metadata = random.choice(album_data['images'])
            link_key = 'link'
        elif website == "Alphacoders":
            album_data = self.get_json_alphacoders(random_source)
            link_key = 'url_image'
            if not album_data or not album_data['wallpapers']:
                # print(album_data)
                return False
            # print(album_data)
            random_image_metadata = random.choice(album_data['wallpapers'])
        if not self.check_image_conditions_json(random_image_metadata):
            return False

        image = download_from_url(random_image_metadata[link_key])
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

    def add_imgur_album(self, album):
        """
        add the hash of an album to the directory of albums
        """
        # imgur
        regex = re.compile(r"^https://imgur.com/a/(\w+)\s*$")
        if regex.match(album):
            album = regex.sub(r"\1", album)
            if 'Imgur' not in self.source:
                self.source['Imgur'] = set()
            self.source['Imgur'].add(album)
            return True
        print("This is not a valid Imgur album url:", album)
        return False

    def add_alphacoders_categories(self, categories):
        """
        Add all the asked categories to the list of sources to pick from
        """
        for cat in categories:
            if cat not in self.alphacoders_categories:
                print("Category", cat, "Not a real category...")
                return False
            if 'Alphacoders' not in self.source:
                self.source['Alphacoders'] = set()
            self.source['Alphacoders'].add(cat)

    def read_source_file(self, filename):
        """
        iterates through a file to add the url to the directory of albums.
        Lets add_album handle the parsing and checking
        """
        if os.path.isfile(filename):
            with open(filename, "r") as file:
                for line in file.readlines():
                    # print("Trying to add line", line.replace('\n', ''))
                    self.add_imgur_album(line)
            return True
        print("Non existing file \""+filename+"\"")
        return False

    def get_alphacoders_categories(self):
        """
        Return all the current categories at alphacoders
        """
        parameters = {
            'auth': self.alphacoders_api_key,
            'method': "category_list"
        }
        try:
            ac_req = requests.get(ALPHACODERS_API_URL,
                                  params=parameters).json()
        except requests.ConnectionError:
            print("No connection to alphacoders")
            return False, False
        # print(ac_req)
        if not ac_req['success']:
            print(ac_req['error'])
            return False, False

        names = [elem['name'] for elem in ac_req['categories']]
        names += ['All']
        ids = [elem['id'] for elem in ac_req['categories']]
        return names, ids


def arguments_parsing(random_imgur):
    """
    Parses the arguments for the command line call
    """
    ###
    # Creation of arguments parser
    ###
    parser = argparse.ArgumentParser(
        description="Utility to have a random wallpaper from various sources.",
        prog='RandomImgurDesktop',
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog, max_help_position=10, width=200)
    )

    parser.add_argument("-ac", "--alphacoders",
                        metavar="category",
                        nargs="*",
                        choices=random_imgur.alphacoders_categories,
                        help="you can fill one or more categories, each\
                        between quotes and space separated like this:\
                        'category1' 'category2' 'category3'. Categories may\
                        be from the following:" +
                        ', '.join(
                            map(
                                str,
                                random_imgur.alphacoders_categories)))
    parser.add_argument(
        "-i", "--imgur",
        metavar="Imgur url",
        type=str,
        help="Specify a unique imgur album where to pick the images.")

    parser.add_argument(
        "-I", "--imgur-file",
        metavar="Imgur File",
        help="Specify a file where to find all the Imgur albums\
            you would like to pick from. Only specify absolute path.")

    parser.add_argument(
        "-cS", "--cache-size",
        metavar="size",
        type=int,
        help="Specify the number of images to\
            keep in cache. Default to 10. 0 means no limit")
    parser.add_argument(
        "-cD", "--cache-directory",
        metavar="cache-directory",
        type=str,
        help="Specify where you wish to keep your cached images.\
        No relative path.\
        Default to /home/<username>/.cache/random-imgur-image/")

    parser.add_argument(
        "-s", "--safe-for-work", action="store_true",
        help="Don't download pictures marked as NSFW ('not safe wor work',\
        that is images with potentially adult content)"
    )

    args = parser.parse_args()

    ####
    # Take actions according to arguments
    ###

    if not (args.alphacoders or args.album or args.imgur_file):
        print("You need at least one source")
    if args.alphacoders:
        random_imgur.add_alphacoders_categories(args.alphacoders)
    if args.imgur:
        random_imgur.add_imgur_album(args.imgur)
    if args.imgur_file:
        imgur_file = args.imgur_file
        if "../" in imgur_file:
            print("No backward relative path in file containing imgur albums!")
            return -1
        if not random_imgur.read_source_file(imgur_file):
            print("Impossible to read file. Exiting.")
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
                random_imgur.cache_size = cache_size

    if args.cache_directory:
        galleries = args.galleries
        if "../" in galleries:
            print("No backward relative path in galleries !")
            return -1
        random_imgur.cache_dir = args.cache_directory

    random_imgur.sfw = args.safe_for_work


def main():
    """
    Main of the script
    """
    sleeptime = 3
    try:
        random_imgur = RandomImgurDesktop()
    except OSError:
        return -1

    arguments_parsing(random_imgur)

    random_imgur.init_cache()

    while True:
        loop_start = time.time()
        try:
            conn = requests.head("http://www.imgur.com")
        except requests.exceptions.ConnectionError:
            # no internet connection
            # print("No internet :( trying to use local cache...")
            if not random_imgur.no_internet():
                print("No internet and cache is empty, quitting")
                return -1
        else:
            if conn.ok:
                # print("Connection ok, going normal")
                image_filename = random_imgur.download_random_image()
                while not image_filename:
                    image_filename = random_imgur.download_random_image()

                random_imgur.update_background(image_filename)
            else:
                # imgur is not accessible
                # print("Imgur not accessible ? trying to use local cache...")
                if not random_imgur.no_internet():
                    print("Imgur not accessible and cache is empty, quitting")
                    return -1
        finally:
            # If we lost time to find the picture, don't sleep too much
            time.sleep(sleeptime-(loop_start-time.time()))
    return 0


if __name__ == '__main__':
    main()
