from django.shortcuts import render
import requests
from twilio.twiml.messaging_response import MessagingResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import datetime
import emoji

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
Hi! I am the Quarantine Bot :wave:
Let's be friends :wink:

You can give me the following commands:
:black_small_square: 'quote': Hear an inspirational quote to start your day!
:black_small_square: 'cat': Who doesn't love cat pictures?
:black_small_square: 'statistics <country>': Show the latest COVID19 statistics for each country.
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

        elif incoming_msg.startswith('statistics'):
            # runs task to aggregate data from Apify Covid-19 public actors
            requests.post('https://api.apify.com/v2/actor-tasks/5MjRnMQJNMQ8TybLD/run-sync?token=qTt3H59g5qoWzesLWXeBKhsXu&ui=1')
            
            # get the last run dataset items
            r = requests.get('https://api.apify.com/v2/actor-tasks/5MjRnMQJNMQ8TybLD/runs/last/dataset/items?token=qTt3H59g5qoWzesLWXeBKhsXu')
            
            if r.status_code == 200:
                data = r.json()

                country = incoming_msg.replace('statistics ', '')
                country_data = list(filter(lambda x: x['country'].lower() == country, data))

                if country_data:
                    data_dict = country_data[0]
                    last_updated = datetime.datetime.strptime(data_dict['lastUpdatedApify'], "%Y-%m-%dT%H:%M:%S.%fZ")

                    result = """
Statistics for country {}:
Infected: {}
Tested: {}
Recovered: {}
Deceased: {}
Last updated: {:02}/{:02}/{:02} {:02}:{:02}:{:03} UTC
""".format(
    data_dict['country'], 
    data_dict['infected'], 
    data_dict['tested'], 
    data_dict['recovered'], 
    data_dict['deceased'],
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
                
        if not responded:
             msg.body("Sorry, I don't understand.")

        return HttpResponse(str(resp))