"""
This module allows to easily watermark an image with a given text.
This is useful to credit the website/creator of an image

Mostly copied from http://www.thecodingcouple.com/watermark-images-python-pillow-pil/
"""
from PIL import Image, ImageDraw, ImageFont


def add_watermark(input, text, output):
    """
    Add a watermark to an image

    Positional Arguments:
        input: absolute path to the image
        text: text to display
        output: absolute path to the output image
    """
    image = Image.open(input)
    width, height = image.size

    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype('OpenSans-Regular.ttf', 42)
    textwidth, textheight = draw.textsize(text, font)

    # calculate the x,y coordinates of the text
    margin = 5
    x = width - textwidth - margin
    y = height - textheight - margin

    # draw watermark in the bottom right corner
    draw.text((width/2, y), text, font=font)

    image.save(output)
