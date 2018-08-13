#!/home/battleman/Programs/anaconda3/bin/python
# -*- coding: utf-8 -*-
"""
This module allows to easily watermark an image with a given text.
This is useful to credit the website/creator of an image

Credits to http://www.thecodingcouple.com/watermark-images-python-pillow-pil/
"""
from PIL import Image, ImageDraw, ImageFont


def add_watermark(image, text, screen_size):
    """
    Add a watermark to an image

    Positional Arguments:
        input: absolute path to the image
        text: text to display
        output: absolute path to the output image
    """
    image = image.convert('RGBA')
    image_height = image.height
    _, screen_height = screen_size
    margin = 5
    text_color = "#BBB"
    watermark_size = (image_height, image_height)

    text_canvas = Image.new('RGBA', watermark_size, (0, 0, 0, 170))
    text_draw = ImageDraw.Draw(text_canvas)
    font = ImageFont.truetype('FreeMono', 12)
    text_width, text_height = text_draw.textsize(text, font)
    x_coord = (image_height-text_width)/2  # width - textWidth - margin
    y_coord = text_height//4  # height - textHeight - margin
    text_draw.text((x_coord, y_coord), text, text_color, font)
    text_canvas = text_canvas.rotate(90)

    watermark_canvas = Image.new('RGBA',
                                 (text_height+2*margin, text_width+2*margin),
                                 (0, 0, 0, 0))
    watermark_canvas.paste(
        text_canvas,
        (0, -(image_height-text_width)//2 + margin))

    image.paste(watermark_canvas,
                (margin, (screen_height-text_width)//2),
                watermark_canvas)
    return image.convert("RGB")


def resize_image(image, screen_size=(1920, 1080)):
    """
    Takes an image and new dimensions, and return the image resized
    accordingly. If one of the dimensions is None, it will be resized to
    keep current proportions
    """
    width, height = screen_size
    image_width, image_height = image.size
    if image_width/image_height > 16/9:
        # Too tall
        image_height = (image_height * width) // image_width
        image_width = width
    elif image_width/image_height < 16/9:
        # too wide
        image_width = (image_width * height) // image_height
        image_height = height
    else:
        # good ratio
        image_width = width
        image_height = height
    resized = image.resize(
        (int(image_width), int(image_height)), Image.ANTIALIAS)
    canvas = Image.new("RGB", screen_size)
    canvas.paste(resized,
                 ((width-image_width)//2 if width != image_width else 0,
                 (height-image_height)//2 if height != image_height else 0))

    return canvas


def test():
    """
    This module is here to present an example of use
    """
    image = Image.open("image.jpeg")
    resized = resize_image(image)
    watermarked = add_watermark(
        resized,
        "That is a watermark, probably not the best tho",
        (1920, 1080))
    watermarked.save('output.jpeg')


if __name__ == "__main__":
    test()