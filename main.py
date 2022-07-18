# Load u.png from /templates/ and add text to it
import os

import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image
import schedule
import time
import tweepy
import yaml
import asyncio
from bbfcapi.lib_async import best_match


def get_line_length(line):
    UPPER_CASE_SIZE = 0.9
    LOWER_CASE_SIZE = 0.65
    W_SIZE = 1

    line_length = 0
    for char in line:
        if char.isupper():
            if char == 'W':
                line_length += W_SIZE
            else:
                line_length += UPPER_CASE_SIZE
        elif char.islower():
            line_length += LOWER_CASE_SIZE
    return line_length


def prepare_text(text):
    MAX_CHARS_PER_LINE = 30
    MAX_LINES = 7
    lines = []
    line = ''
    for char in text:
        if get_line_length(line) >= MAX_CHARS_PER_LINE - 8 and char == ' ':
            lines.append(line)
            line = ''
        if not (len(line) == 0 and char == ' '):
            line += char
    lines.append(line)
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES]
    return lines


def draw_image(title, text, rating):
    FONT_SIZE = 32
    FONT_PATH = 'font/font.otf'
    TEMPLATE_DIRECTORY = 'templates/'
    TEMPLATE_FORMAT = 'png'
    OUT_DIRECTORY = 'out/'

    # Load image
    img = cv2.imread(TEMPLATE_DIRECTORY + rating + '.' + TEMPLATE_FORMAT)

    # Load font from font/font.otf file
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    img_pil = Image.fromarray(img)

    drawn_image = ImageDraw.Draw(img_pil)

    # Draw text line by line
    y = 20
    for line in prepare_text(text):
        drawn_image.text((20, y), line,
                         font=font, fill=(255, 255, 255))
        y += 28 + 10

    # Convert back to OpenCV format
    img = np.array(img_pil)

    # Prepare title file
    title_file_path = OUT_DIRECTORY + title.replace(' ', '_').lower() + ".png"

    # Save image
    cv2.imwrite(title_file_path, img)
    return title_file_path


# Query the BBFC API for the title
def query_bbfc(title):
    return asyncio.run(best_match(title=title))


def send_tweet(image_file_path, title, rating, config):
    # Authenticate to Twitter
    oauth1_user_handler = tweepy.OAuth1UserHandler(consumer_key=config['consumer_key'],
                                                   consumer_secret=config['consumer_key_secret'],
                                                   callback="oob")
    if config.get('access_key') is None:
        # Print auth URL
        print("Authentication required! Visit: " + oauth1_user_handler.get_authorization_url())
        verifier = input("Input PIN: ")
        config["access_key"], config["access_key_secret"] = oauth1_user_handler.get_access_token(verifier)

    auth = tweepy.OAuth1UserHandler(config['consumer_key'], config['consumer_key_secret'])
    auth.set_access_token(config['access_key'], config['access_key_secret'])
    api = tweepy.API(auth)

    # Send a tweet with the tweepy v2 client saying hello world
    tweet_text = title + ' (' + rating.upper() + ')'
    api.update_status_with_media(status=tweet_text, filename=image_file_path)


def run(quote_dictionary, config):
    title = list(quote_dictionary.keys())[np.random.randint(0, len(quote_dictionary))]
    text = quote_dictionary[title]
    query_result = query_bbfc(title)
    official_title = query_result.title
    rating = query_result.age_rating.lower()
    send_tweet(draw_image(title, text, rating), official_title, rating, config)


# Fix dodgy asyncio issues
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Open quotes/bbfc_quotes.yml and pick a random quote
quote_dictionary = {}
with open('quotes/test_quotes.yml', 'r') as stream:
    try:
        parsed_yaml = yaml.safe_load(stream)
        for quote in parsed_yaml:
            title = quote
            text = parsed_yaml[quote]
            quote_dictionary[title] = text
    except yaml.YAMLError as exception:
        print(exception)

# Get Twitter API keys from environment variables
config = {
    'consumer_key': os.environ['CONSUMER_KEY'],
    'consumer_key_secret': os.environ['CONSUMER_KEY_SECRET']
}

# Run every day at 16:00
run(quote_dictionary, config)
# schedule.every().day.at('19:06').do(run, quote_dictionary, config)
# while True:
#    schedule.run_pending()
#    time.sleep(10)
