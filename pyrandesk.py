# -*- coding: utf-8 -*-
"""
This is a good code
"""
import argparse
import fnmatch
import getpass
import glob
import json
import logging
import logging.config
import os
import random
import re
import stat
import subprocess
import sys
import time
from io import BytesIO
from math import log as mlog

import requests
import yaml
from PIL import Image, ImageFile

from watermarking import add_watermark, resize_image

####
# Constants
###
LOCATION = "/storage/Documents/Programming/Python/Pyrandesk/"

####
# Helpers
###


def setup_logging(default_path='logging.yaml',
                  default_level=logging.INFO,
                  env_key='PYLOG_CFG'):
    """
    Setup logging configuration.
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value

    if os.path.exists(path):
        with open(path) as log_file:
            config = yaml.safe_load(log_file.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def open_yaml(config_file, logger):
    """
    Open as yaml file and returns it loaded
    """
    if os.path.isfile(config_file):
        with open(config_file) as file:
            config = yaml.load(file)
    else:
        logger.critical(
            "Error reading config file. Please ensure the file '%s' exists",
            config_file)
        sys.exit()
    return config


def read_source_file(filename, logger):
    """
    Iterates through a file to add the url to the directory of albums.
    Lets add_album handle the parsing and checking
    """

    if not os.path.isabs(filename):
        logger.error("The filename '%s' is wrong or relative. Make sure you"
                     "specify an existing absolute path to the file", filename)
        return []

    with open(filename, "r") as file:
        return [line for line in file.readlines()]


def limited_connection():
    """Check Whether or not a connection is marked as 'Limited' (limit
    data usage)

    Returns:
        Boolean -- True if connection is marked 'limited', False otherwise
    """

    connection_name = subprocess.check_output(
        "nmcli -t -f GENERAL.CONNECTION --mode tabular device show".split(" "))
    connection_name = connection_name.strip().decode('utf-8').split("\n")[0]
    if connection_name == '':
        return False
    metered = subprocess.check_output(
        "nmcli -f connection.metered connection show {}".format(
            connection_name).split(" "))
    metered = metered.strip().decode('utf-8').split(" ")[-1]
    if metered == "yes":
        return True
    return False


class Website():
    """
    Defines parents and general functions for a generic website
    """

    def __init__(self, human_name, address, auth_yaml_key):
        self.logger = logging.getLogger(__name__)
        config = open_yaml(LOCATION+'config.yaml', self.logger)
        self.api_address = address
        self.authentication = config[auth_yaml_key]
        self.source = set()
        self.human_name = human_name
        self.url_key = None  # please redefine this for your website

    def download_image(self, json_info, key):
        """
        Given an url, download binary image

        This method does not use any API. The J

        Keyword arguments:
            json: dictionnary containing the address of the raw image.
            key: key to identify the url in the dictionnary
        """
        link = json_info[key]
        logger = logging.getLogger(__name__)
        logger.info("Downloading %s", link)
        try:
            req = requests.get(link)
            if not req.ok:
                self.logger.error("Failed to get %s." +
                                  " Reason: HTTP code %s, '%s'",
                                  link, req.status_code, req.reason)
                return False
        except requests.exceptions.MissingSchema as exception:
            self.logger.error("Invalid URL schema: %s", format(exception))
            return False
        except requests.exceptions.ConnectionError as exception:
            self.logger.error("Connection error: %s", format(exception))
            return False
        return req.content

    def get_group_json(self, identifier):
        """
        Get the json for an album/category,... including a list of images
        """
        pass

    def check_conditions(self, image_meta, conditions):
        """
        Given some metadata of the file and conditions, ensure the conditions
        are fullfilled by the image.
        """
        pass

    def get_random_image(self):
        """
        Yields a random image (json)
        """
        pass

    def get_mimetype(self, json_info):
        """
        Returns the type of the file
        """
        pass

    def check_connection(self):
        """
        Verifies the connection to the API of the website is functional.
        """
        try:
            requests.get(self.api_address)
        except requests.ConnectionError:
            return False
        return True

    def get_watermark_text(self):
        """
        Yields the text that should watermark the image
        (that is the source/creator of the image).
        If none, no watermark will be added
        """
        return "Unknown"


class Imgur(Website):
    """
    Defines all functions and attributes linked to Imgur
    """

    def __init__(self, human_name, address, auth_yaml_key):
        super().__init__(human_name, address, auth_yaml_key)
        self.albums_hash = []
        self.url_key = 'link'

    def get_group_json(self, album_hash):
        """
        Query for a given album hash, and return a
        json-interpreted version of the content
        """
        super().get_group_json(album_hash)
        payload = {"Authorization": "Client-ID " + self.authentication}
        try:
            response = requests.get(
                self.api_address + str(album_hash),
                headers=payload).json()
        except json.decoder.JSONDecodeError as err:
            self.logger.error("Error decoding Json: %s", err)
            return False

        if not response['success']:
            self.logger.error(
                "Error querying Imgur; status: %s | %s",
                response['status'],
                response['data']['error'])
            return False

        return response['data']

    def add_album(self, album):
        """
        add the hash of an album to the directory of albums
        """
        # imgur
        regex = re.compile(r"^https://imgur.com/a/(\w+)\s*$")
        if regex.match(album):
            album = regex.sub(r"\1", album)
            self.albums_hash.append(album)
            return True
        self.logger.error("This is not a valid Imgur album url: %s", album)
        return False

    def input_albums_file(self, file):
        """
        Reads the file in argument and considers every line as an album.
        Adds them to the potential sources.
        """
        albums = read_source_file(file, self.logger)
        if not albums:
            return False
        for album in albums:
            if not self.add_album(album):
                return False
        return True

    def check_conditions(self, image_meta, conditions):
        super().check_conditions(image_meta, conditions)
        if conditions['sfw'] and image_meta['nsfw']:
            # user wants sfw, image i not
            return False
        return True

    def get_random_image(self):
        """
        Yields a random image (json)
        """
        if not self.albums_hash:
            self.logger.error("No stored album for Imgur")
            return False

        album_hash = random.choice(self.albums_hash)
        album_meta = self.get_group_json(album_hash)
        if not album_meta:
            return False
        random_image = random.choice(album_meta['images'])
        return random_image

    def get_mimetype(self, json_info):
        return json_info['type'].split('/')[1]

    def get_watermark_text(self, json_info):
        # url = json_info['link']
        username = json_info['account_url']
        if username == 'null':
            username = 'Anonymous'
        text = "Imgur | {}".format(username)
        return text


class Alphacoders(Website):
    """
    Defines all functions and attributes linked to Alphacoders
    """

    def __init__(self, human_name, address, auth_yaml_key):
        super().__init__(human_name, address, auth_yaml_key)
        self.selected_categories = set()
        self.url_key = 'url_image'
        self.cached_categories = "categories.txt"
        self.all_categories, self.categories_ids = self.get_all_categories(
            "/home/battleman/.cache/pyrandesk/")

    def get_group_json(self, category):
        """
        Query alphacoders to return images in a given category
        """
        super().get_group_json(category)
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
            spec_params = {
                "method": "category",
                "id": self.categories_ids[
                    self.all_categories.index(category)],
                "page": random.randint(1, 1000),
                "check_last": 1
            }
        params = {
            "auth": self.authentication,
            "info_level": 2
        }
        params.update(spec_params)
        response = requests.get(
            self.api_address,
            params=params).json()
        if response['success']:
            return response
        return False

    def add_categories(self, categories):
        """
        Add all the asked categories to the list of sources to pick from
        """
        for cat in categories:
            if cat not in self.all_categories:
                self.logger.warning(
                    "Category '%s' is not a real category...", cat)
                return False
            if cat == 'All':
                self.selected_categories = [cat]
                return True
            self.selected_categories.add(cat)
        self.selected_categories = list(self.selected_categories)
        return True

    def get_all_categories(self, cache_location, nameonly=False):
        """
        Return all the current categories at alphacoders
        """
        names = []
        ids = []
        parameters = {
            'auth': self.authentication,
            'method': "category_list"
        }
        try:
            ac_req = requests.get(self.api_address,
                                  params=parameters).json()
        except requests.ConnectionError:
            self.logger.warning("No connection to alphacoders")
            try:
                with open(cache_location+self.cached_categories, 'r') as cache:
                    for line in cache.readlines():
                        split_line = line[:-1].split(',')
                        names.append(split_line[0])
                        ids.append(split_line[1])
            except FileNotFoundError:
                self.logger.warning("Error reading cached categories.")
                names, ids = [[], []]

        else:
            if not ac_req['success']:
                self.logger.warning(ac_req['error'])
                return False
            names = [elem['name'] for elem in ac_req['categories']]
            ids = [elem['id'] for elem in ac_req['categories']]
            with open(cache_location+self.cached_categories, 'w') as cache:
                for cat, cat_id in zip(names, ids):
                    line = "{},{}\n".format(cat, cat_id)
                    cache.write(line)
        names += ['All']
        if nameonly:
            return names
        return names, ids

    def check_conditions(self, image_meta, conditions):
        super().check_conditions(self, image_meta)
        return True

    def get_random_image(self):
        category = random.choice(self.selected_categories)
        cat_meta = self.get_group_json(category)
        if not cat_meta['wallpapers']:  # empty list
            return {}
        random_image = random.choice(cat_meta['wallpapers'])
        return random_image

    def get_mimetype(self, json):
        return json['file_type']

    def get_watermark_text(self, json):
        username = json['user_name']
        text = "Alphacoders | {}".format(username)
        return text


class PyRanDesk():
    """
        Define basic functions
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        config = open_yaml(LOCATION+'config.yaml', self.logger)
        self.logger.info("Init pyrandesk instance")
        self.image_counter = 0
        user = getpass.getuser()
        self.cache_size = config['default_cache_size']
        self.cache_dir = config['default_cache_dir'].replace(
            '<USERNAME>', user)

        self.imgur = Imgur("Imgur", "https://api.imgur.com/3/album/",
                           "imgur_client_id")
        self.alpha = Alphacoders("Alphacoders",
                                 "https://wall.alphacoders.com/api2.0/get.php",
                                 "alphacoders_api_key")
        # self.example = Example("Example",
        #                        "https://example.com/api/",
        #                        "example_api_key")

        self.alphacoders_categories = self.alpha.get_all_categories(
            cache_location=self.cache_dir, nameonly=True)
        self.websites = set()
        self.accessible_websites = set()
        self.conditions = {}
        self.resolution = (1920, 1080)

    def init_cache(self):
        """
        Ensures cache folder exists and that the cache is not too full
        at startup

        Checks there are less files in cache than specified size.
        If too many, removes oldest ones to have fitting size.
        """
        self.logger.info("Initializing cache with size %d at %s",
                         self.cache_size, self.cache_dir)
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except OSError as error:
                self.logger.critical(
                    "Error creating cache folder:", exec_info=True)
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
                        self.logger.info(
                            "Cache too full, cleaning file %s", entry[1])
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

    def set_cache_size(self, cache_size):
        """
        Setter for the cache size (in number of images).
        Ensures it is a positive integer.
        """
        try:
            size = int(cache_size)
        except ValueError:
            self.logger.error(
                "Cache size must be an integer. Using default value.")
        else:
            if size < 0:
                self.logger.error(
                    "Cache size must be greater or equal to 0."
                    " Using default value (%d)", self.cache_size)
            else:
                self.cache_size = size

    def set_cache_location(self, location):
        """
        Verifies the passed location is correct, and updates the target of
        the cache.
        """
        if not isinstance(location, str):
            self.logger.critical(
                "Parameter 'location' should be str, not %s", type(location))
            return False
        if not os.path.isabs(location):
            self.logger.critical(
                "No relative location for the cache. Only absolute. ")
            return False
        self.cache_dir = location
        return True

    def get_cached_image(self):
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
        if not file_list:
            return False
        random_cached_file = file_list[random.randint(0, len(file_list)-1)]
        # self.logger.INFO()
        return random_cached_file

    def download_random_image(self):
        """
        Picks a random source and downloads one image from there (at random)

        Chooses a source, one picks one element at random, downloads it
        save it and return the absolute path to the cached image
        """
        website = random.choice(list(self.accessible_websites))

        random_image_meta = website.get_random_image()
        if not (random_image_meta and
                website.check_conditions(random_image_meta, self.conditions)):
            return False

        extension = website.get_mimetype(random_image_meta)
        image = website.download_image(random_image_meta, website.url_key)

        filename = self.save_image(
            image, extension, website.get_watermark_text(random_image_meta))
        return filename

    def save_image(self, binary, extension, watermark):
        """
        Save an image with given extension to the cache directory of the object

        Keyword arguments:
            binary: the binary image (raw from the GET request)
        """
        max_num_files = int(mlog(self.cache_size, 10)//1 + 1)
        filename_mini = "image_%0*d" % (max_num_files, self.image_counter)
        filename_path = self.cache_dir + filename_mini
        filename = filename_path + "." + extension
        filename_orig = filename_path + "_orig." + extension
        self.logger.info("Saving to %s", filename)
        for to_remove in glob.glob(filename_path+"*.*"):
            os.remove(to_remove)

        image = Image.open(BytesIO(binary))
        image_resized = resize_image(image, self.resolution)
        self.logger.info("Resizing to resolution %s", self.resolution)
        image_watermarked = add_watermark(
            image_resized,
            watermark,
            self.resolution)

        try:
            image_watermarked.save(filename)
            image.save(filename_orig)
        except FileNotFoundError:
            self.logger.critical("Impossible to save at location %s, "
                                 "ensure the folder exists.", filename)
            return False
        except PermissionError:
            self.logger.critical("Permission to write at location %s "
                                 "was denied, ensure you have correct"
                                 " rights.", filename)
            return False

        self.image_counter += 1
        if self.image_counter == self.cache_size:
            self.logger.info("Reached max cache size (%s), "
                             "starting to overwrite",
                             self.cache_size)
            self.image_counter = 0

        return filename

    def test_internet(self):
        """
        For each selected entry, test if there is internet access to the
        API. If not, remove from the source list. Returns whether there is
        still at least one entry in the list.

        Return value:
            True if at least one given website is accessible.
            False otherwise.
        """
        if limited_connection():
            self.logger.info("Limited background data usage")
            return False
        self.accessible_websites = self.websites.copy()
        for web in self.websites:
            if not web.check_connection():
                self.logger.warning("No connection to %s", web)
                self.accessible_websites.remove(web)
        return len(self.accessible_websites) > 0

    def update_background(self, filename):
        """
        Use dconf to update the background.

        Keywords:
            -- filename: Absolute path to the image
        """
        if not filename or not isinstance(filename, str):
            self.logger.error("Filename is empty? Not changing background")
            return

        key = "/org/gnome/desktop/background/picture-uri"
        value = "'file://"+filename+"'"
        subprocess.Popen([
            "dconf", "write", key, value
        ])

        ######
        # personal need for my conky.
        # You can probably safely delete this.
        # subprocess.Popen([
        #     "feh", "--bg-fill", filename
        # ])
        #####


def arguments_parsing(pyrandesk, logger):
    """
    Parses the arguments for the command line call
    """
    ###
    # Creation of arguments parser
    ###
    parser = argparse.ArgumentParser(
        description="Utility to have a random wallpaper from various sources.",
        prog='pyrandesk',
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog, max_help_position=10, width=200))

    parser.add_argument("-ac", "--alphacoders",
                        metavar="category",
                        nargs="*",
                        choices=pyrandesk.alphacoders_categories,
                        help="you can fill one or more categories, each\
                        between quotes and space separated like this:\
                        'category1' 'category2' 'category3'. Categories\
                        may be from the following: " +
                        ', '.join(map(str, pyrandesk.alphacoders_categories)))
    parser.add_argument("-i", "--imgur",
                        metavar="Imgur url",
                        type=str,
                        help="Specify a unique imgur album where to pick" +
                        "the images.")
    parser.add_argument("-I", "--imgur-file",
                        metavar="Imgur File",
                        help="Specify a file where to find all the Imgur" +
                        "albums you would like to pick from." +
                        " Only specify absolute path.")
    parser.add_argument("-cS", "--cache-size",
                        metavar="size",
                        type=int,
                        help="Specify the number of images to\
            keep in cache. Default to 10. 0 means no limit")
    parser.add_argument("-cD", "--cache-directory",
                        metavar="cache-directory",
                        type=str,
                        help="Specify where you wish to keep your cached " +
                        "images. No relative path.Default to " +
                        "/home/<username>/.cache/pyrandesk")
    parser.add_argument("-s", "--safe-for-work",
                        action="store_true",
                        help="Don't download pictures marked as " +
                        "NSFW ('not safe wor work', that is images with " +
                        "potentially adult content)")
    parser.add_argument("-v", "--verbose", action='store_true',
                        help="Toggle verbosity")
    args = parser.parse_args()

    ####
    # Take actions according to arguments
    ###

    # if not (args.alphacoders or args.imgur or args.imgur_file):
    #     LOGGER.critical('No input source specified')
    #     sys.exit("You need at least one source")
    #     return False

    # If source is Alphacoders-related
    if args.alphacoders:
        pyrandesk.websites.add(pyrandesk.alpha)
        if not pyrandesk.alpha.add_categories(args.alphacoders):
            sys.exit("Can't add all the categories.")

    # If source is Imgur-related
    if args.imgur:
        if pyrandesk.imgur.add_album(args.imgur):
            pyrandesk.websites.add(pyrandesk.imgur)
        else:
            logger.error("Can't add the album %s", args.imgur)
    if args.imgur_file:
        imgur_file = args.imgur_file
        if pyrandesk.imgur.input_albums_file(imgur_file):
            pyrandesk.websites.add(pyrandesk.imgur)
        else:
            logger.error("Error with file %s", imgur_file)

    if not pyrandesk.websites:
        logger.critical("No valid source, stopping")
        return False

    if args.cache_size:
        pyrandesk.set_cache_size(args.cache_size)

    if args.cache_directory:
        pyrandesk.set_cache_location(args.cache_directory)

    pyrandesk.conditions['sfw'] = args.safe_for_work
    return True


def main():
    """
    Main of the script
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    sleeptime = 60*5
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        pyrandesk = PyRanDesk()
    except OSError as error:
        logger.critical("Error initializing main class: %s", error)
        sys.exit()

    if not arguments_parsing(pyrandesk, logger):
        logger.critical("Error parsing arguments")
        sys.exit()

    pyrandesk.init_cache()

    while True:
        loop_start = time.time()
        image_filename = None
        internet = pyrandesk.test_internet()
        if internet:
            while not image_filename:
                image_filename = pyrandesk.download_random_image()
        else:  # no internet, trying local cache
            logger.info("No internet, trying cache")
            image_filename = pyrandesk.get_cached_image()
            if not image_filename:  # cache is empty
                logger.critical("No internet and cache is empty, quitting")
                sys.exit()

        pyrandesk.update_background(image_filename)

        # If we lost time to find the picture, don't sleep too much
        spent_time = time.time()-loop_start
        logger.debug("Time spent in loop: %d", spent_time)
        time.sleep(max(sleeptime-spent_time, 0))

    return


if __name__ == '__main__':
    main()
