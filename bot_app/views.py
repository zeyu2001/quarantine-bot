from django.shortcuts import render
import requests
from twilio.twiml.messaging_response import MessagingResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import datetime
import emoji
import random
import json

@csrf_exempt
def index(request):
    if request.method == 'POST':
        # retrieve incoming message from POST request in lowercase
        incoming_msg = request.POST['Body'].lower()

        # create Twilio XML response
        resp = MessagingResponse()
        msg = resp.message()

        responded = False

        if incoming_msg == 'hello':
            response = emoji.emojize("""
*Hi! I am the Quarantine Bot* :wave:
Let's be friends :wink:

You can give me the following commands:
:black_small_square: *'quote':* Hear an inspirational quote to start your day! :rocket:
:black_small_square: *'cat'*: Who doesn't love cat pictures? :cat:
:black_small_square: *'dog'*: Don't worry, we have dogs too! :dog:
:black_small_square: *'meme'*: The top memes of today, fresh from r/memes. :hankey:
:black_small_square: *'news'*: Latest news from around the world. :newspaper:
:black_small_square: *'recipe'*: Searches Allrecipes.com for the best recommended recipes. :fork_and_knife:
:black_small_square: *'recipe <query>'*: Searches Allrecipes.com for the best recipes based on your query. :mag:
:black_small_square: *'get recipe'*: Run this after the 'recipe' or 'recipe <query>' command to fetch your recipes! :stew:
:black_small_square: *'statistics <country>'*: Show the latest COVID19 statistics for each country. :earth_americas:
:black_small_square: *'statistics <prefix>'*: Show the latest COVID19 statistics for all countries starting with that prefix. :globe_with_meridians:
""", use_aliases=True)
            msg.body(response)
            responded = True

        elif incoming_msg == 'quote':
            # returns a quote
            r = requests.get('https://api.quotable.io/random')

            if r.status_code == 200:
                data = r.json()
                quote = f'{data["content"]} ({data["author"]})'

            else:
                quote = 'I could not retrieve a quote at this time, sorry.'

            msg.body(quote)
            responded = True

        elif incoming_msg == 'cat':
            # return a cat pic
            msg.media('https://cataas.com/cat')
            responded = True

        elif incoming_msg == 'dog':
            # return a dog pic
            r = requests.get('https://dog.ceo/api/breeds/image/random')
            data = r.json()
            msg.media(data['message'])
            responded = True

        elif incoming_msg.startswith('recipe'):

            # search for recipe based on user input (if empty, return featured recipes)
            search_text = incoming_msg.replace('recipe', '')
            search_text = search_text.strip()
            
            data = json.dumps({'searchText': search_text})
            
            result = ''
            # updates the Apify task input with user's search query
            r = requests.put('https://api.apify.com/v2/actor-tasks/o7PTf4BDcHhQbG7a2/input?token=qTt3H59g5qoWzesLWXeBKhsXu&ui=1', data = data, headers={"content-type": "application/json"})
            if r.status_code != 200:
                result = 'Sorry, I cannot search for recipes at this time.'

            # runs task to scrape Allrecipes for the top 5 search results
            r = requests.post('https://api.apify.com/v2/actor-tasks/o7PTf4BDcHhQbG7a2/runs?token=qTt3H59g5qoWzesLWXeBKhsXu&ui=1')
            if r.status_code != 201:
                result = 'Sorry, I cannot search Allrecipes.com at this time.'

            if not result:
                result = "I am searching Allrecipes.com for the best _{}_ recipes.".format(search_text)
                result += "\nPlease wait for a few moments before typing 'get recipe' to get your recipes!"
            msg.body(result)
            responded = True

        elif incoming_msg == 'get recipe':
            # get the last run details
            r = requests.get('https://api.apify.com/v2/actor-tasks/o7PTf4BDcHhQbG7a2/runs/last?token=qTt3H59g5qoWzesLWXeBKhsXu')
            
            if r.status_code == 200:
                data = r.json()

                # check if last run has succeeded or is still running
                if data['data']['status'] == "RUNNING":
                    result = 'Sorry, your previous query is still running.'
                    result += "\nPlease wait for a few moments before typing 'get recipe' to get your recipes!"

                elif data['data']['status'] == "SUCCEEDED":

                    # get the last run dataset items
                    r = requests.get('https://api.apify.com/v2/actor-tasks/o7PTf4BDcHhQbG7a2/runs/last/dataset/items?token=qTt3H59g5qoWzesLWXeBKhsXu')
                    data = r.json()

                    if data:
                        result = ''

                        for recipe_data in data:
                            url = recipe_data['url']
                            name = recipe_data['name']
                            rating = recipe_data['rating']
                            rating_count = recipe_data['ratingcount']
                            prep = recipe_data['prep']
                            cook = recipe_data['cook']
                            ready_in = recipe_data['ready in']
                            calories = recipe_data['calories']

                            result += """
*{}*
_{} calories_

Rating: {:.2f} ({} ratings)
Prep: {}
Cook: {}
Ready in: {}
Recipe: {}
""".format(name, calories, float(rating), rating_count, prep, cook, ready_in, url)

                    else:
                        result = 'Sorry, I could not find any results for {}'.format(search_text)

                else:
                    result = 'Sorry, your previous search query has failed. Please try searching again.'

            else:
                result = 'I cannot retrieve recipes at this time. Sorry!'

            msg.body(result)
            responded = True

        elif incoming_msg == 'news':
            r = requests.get('https://newsapi.org/v2/top-headlines?sources=bbc-news,the-washington-post,the-wall-street-journal,cnn,fox-news,cnbc,abc-news,business-insider-uk,google-news-uk,independent&apiKey=3ff5909978da49b68997fd2a1e21fae8')
            
            if r.status_code == 200:
                data = r.json()
                articles = data['articles'][:5]
                result = ''
                
                for article in articles:
                    title = article['title']
                    url = article['url']
                    if 'Z' in article['publishedAt']:
                        published_at = datetime.datetime.strptime(article['publishedAt'][:19], "%Y-%m-%dT%H:%M:%S")
                    else:
                        published_at = datetime.datetime.strptime(article['publishedAt'], "%Y-%m-%dT%H:%M:%S%z")
                    result += """
*{}*
Read more: {}
_Published at {:02}/{:02}/{:02} {:02}:{:02}:{:02} UTC_
""".format(
    title,
    url, 
    published_at.day, 
    published_at.month, 
    published_at.year, 
    published_at.hour, 
    published_at.minute, 
    published_at.second
    )

            else:
                result = 'I cannot fetch news at this time. Sorry!'

            msg.body(result)
            responded = True

        elif incoming_msg.startswith('statistics'):
            # runs task to aggregate data from Apify Covid-19 public actors
            requests.post('https://api.apify.com/v2/actor-tasks/5MjRnMQJNMQ8TybLD/run-sync?token=qTt3H59g5qoWzesLWXeBKhsXu&ui=1')
            
            # get the last run dataset items
            r = requests.get('https://api.apify.com/v2/actor-tasks/5MjRnMQJNMQ8TybLD/runs/last/dataset/items?token=qTt3H59g5qoWzesLWXeBKhsXu')
            
            if r.status_code == 200:
                data = r.json()

                country = incoming_msg.replace('statistics', '')
                country = country.strip()
                country_data = list(filter(lambda x: x['country'].lower().startswith(country), data))

                if country_data:
                    result = ''

                    for i in range(len(country_data)):
                        data_dict = country_data[i]
                        last_updated = datetime.datetime.strptime(data_dict.get('lastUpdatedApify', None), "%Y-%m-%dT%H:%M:%S.%fZ")

                        result += """
Statistics for country {}:
Infected: {}
Tested: {}
Recovered: {}
Deceased: {}
Last updated: {:02}/{:02}/{:02} {:02}:{:02}:{:03} UTC
""".format(
    data_dict['country'], 
    data_dict.get('infected', 'NA'), 
    data_dict.get('tested', 'NA'), 
    data_dict.get('recovered', 'NA'), 
    data_dict.get('deceased', 'NA'),
    last_updated.day,
    last_updated.month,
    last_updated.year,
    last_updated.hour,
    last_updated.minute,
    last_updated.second
    )
                else:
                    result = "Country not found. Sorry!"
            
            else:
                result = "I cannot retrieve statistics at this time. Sorry!"

            msg.body(result)
            responded = True

        elif incoming_msg.startswith('meme'):
            r = requests.get('https://www.reddit.com/r/memes/top.json?limit=20?t=day', headers = {'User-agent': 'your bot 0.1'})
            
            if r.status_code == 200:
                data = r.json()
                memes = data['data']['children']
                random_meme = random.choice(memes)
                meme_data = random_meme['data']
                title = meme_data['title']
                image = meme_data['url']

                msg.body(title)
                msg.media(image)
            
            else:
                msg.body('Sorry, I cannot retrieve memes at this time.')

            responded = True

        if not responded:
             msg.body("Sorry, I don't understand. Send 'hello' for a list of commands.")

        return HttpResponse(str(resp))