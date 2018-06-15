#!/usr/bin/python3
"""
This is a good code
"""
# -*- coding: utf-8 -*-

import argparse
import getpass
import random
# import subprocess
import sys
import time
# import urllib.error
# import urllib.request as request
import requests
from os.path import isfile
from pprint import pprint

import yaml


class RandomImgurDesktop():
    """
        Define basic functions
    """

    def __init__(self):
        self.albums = []
        config_file = 'config.yaml'
        if isfile(config_file):
            with open(config_file) as file:
                config = yaml.load(file)
        else:
            pprint("Error reading config file. Please ensure you have a \
                'config.yaml' file at the same location as this script.")
            sys.exit()
        user = getpass.getuser()
        self.client_id = config['clientid']
        self.clientsecret = config['clientsecret']
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
        """
        some_index = random.randint(0, len(self.albums))
        return self.albums[some_index]

    def download_random_image(self, data):
        return

    def add_album(self, album):
        self.albums.append(album)

    def add_multiple_albums(self, filename):
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
    sleeptime = 60

    ###
    # Creation of arguments parser
    ###
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--gallery",
        help="Specify a unique gallery where to pick the images.\
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

    parser.add_argument("-p", "--cache-directory",
                        help="Specify where you wish to keep your cached\
                        images. No relative path. Default to\
                        /home/<username>/.cache/random-imgur-image/")

    args = parser.parse_args()

    ####
    # Take actions according to arguments
    ###
    if args.gallery:
        pass
    elif args.galleries:
        galleries = args.galleries
        if "../" in galleries:
            print("No relative path in galleries !")
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
    random_imgur_desktop = RandomImgurDesktop()
    # json = random_imgur_desktop.get_json("k3AMe")
    # print(json)
    random_imgur_desktop.add_multiple_albums("stupid filename")
    # while True:
    #     time.sleep(sleeptime)
    return 0

if __name__ == '__main__':
    main()
