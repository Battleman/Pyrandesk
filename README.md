# PyRanDesk
## Tests
<!-- [![Build Status](https://travis-ci.org/Battleman/Pyrandesk.svg?branch=master)](https://travis-ci.org/Battleman/Pyrandesk) -->
## General goal
This python script intends to dynamically modify the desktop regularly, based on one or more Imgur albums. I write this for my current distribution, that is debian testing (so far buster), with GNOME3. I can't promise this will work on any other system.


## Requirements

* Python Modules. You can install then with pip or conda, using the name in parenthesis.
    * PIL (`pillow`)
    * Yaml (`yaml`/`pyyaml`)
        * apparently, using `conda install yaml` or `pip install yaml` does not work. Only `pip install pyyaml` does...
    * Requests (`requests`)

## Notes and thanks
The watermarking module was made mainly with the help of [the blog of thecodingcouple](http://www.thecodingcouple.com/watermark-images-python-pillow-pil/) [and their github](https://github.com/townsean/image-marker)
It was mainly copy-pasted, but I'm planning on improving it in the near future. Anyway, big up !

