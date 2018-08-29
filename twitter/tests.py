import requests
from bs4 import BeautifulSoup

url = 'https://twitter.com/Cat55Grumpy/status/1027165193133084672'
b = BeautifulSoup(requests.get(url).content,'html.parser')
permalink_tweet = b.find('div', class_='permalink-tweet-container')
print(permalink_tweet.prettify())
iframe = permalink_tweet.find('iframe')
print(iframe)
