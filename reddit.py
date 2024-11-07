import random
import requests
import subprocess
import os
from dotenv import load_dotenv, dotenv_values


def getData(SUBREDDITS):
    load_dotenv(".env")

    # Global variables-----------------------------------------------------
    CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
    SECRET_KEY = os.getenv('REDDIT_SECRET_KEY')

    # Basic initializations-------------------------------------------------
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, SECRET_KEY)

    data = {
        'grant_type': 'password',
        'username': os.getenv('REDDIT_USERNAME'),
        'password': os.getenv('REDDIT_PASSWORD')
    }

    headers = {'User-agent': 'MyAPI/0.0.1'}
    res = requests.post('https://www.reddit.com/api/v1/access_token',
                        auth=auth, data=data, headers=headers)

    TOKEN = res.json()['access_token']
    headers['Authorization'] = f"bearer {TOKEN}"

    # Reddit work(pulling data from the above declared subreddits)--------------------------------------------
    read_posts = []
    see_posts = []

    for subreddit in SUBREDDITS:
        res = requests.get(f'https://oauth.reddit.com/r/{subreddit}/hot?raw_json=1', headers=headers).json()

        for data in res['data']['children'][1:]:  # Skip the first post
            post = {
                'title': data['data']['title'],
                'body': data['data']['selftext'],
                'media_url': None,  # Default to None if no media is found
                'upvotes': data['data']['ups'],
                'downvotes': data['data']['ups'] - data['data']['score'],  # Calculate downvotes
                'comments': [],
            }

            # Fetch comments for the post using its ID
            post_id = data['data']['id']
            subreddit_name = data['data']['subreddit']
            comments_res = requests.get(f'https://oauth.reddit.com/r/{subreddit_name}/comments/{post_id}?limit=5?raw_json=1',
                                        headers=headers).json()

            # Extract top-level comments (you can adjust this as needed)
            if isinstance(comments_res, list) and len(comments_res) > 1:
                for comment in comments_res[1]['data']['children']:
                    if comment['kind'] == 't1':  # t1 denotes a comment
                        post['comments'].append(comment['data']['body'])

            # Check for Reddit videos
            if data['data'].get('secure_media') and 'reddit_video' in data['data']['secure_media']:
                media_url = {
                    'video_url': data['data']['secure_media']['reddit_video']['fallback_url'],
                    'audio_url': "https://v.redd.it/" +
                                 data['data']['secure_media']['reddit_video']['fallback_url'].split("/")[3] +
                                 "/DASH_AUDIO_128.mp4"
                }
                post['media_url'] = media_url
                see_posts.append(post)

            # Check for GIFs
            elif ('preview' in data['data'] and
                  'images' in data['data']['preview'] and
                  'variants' in data['data']['preview']['images'][0] and
                  'gif' in data['data']['preview']['images'][0]['variants']):
                post['media_url'] = data['data']['preview']['images'][0]['variants']['gif']['source']['url']
                see_posts.append(post)

            # Check for images
            elif ('preview' in data['data'] and
                  'images' in data['data']['preview']):
                post['media_url'] = data['data']['preview']['images'][0]['source']['url']
                see_posts.append(post)

            # If the post is just text
            else:
                read_posts.append(post)

    return see_posts