import logging
import re

import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse

TITLE_MAX_LENGTH = 30
TWITTER_USER_URL = 'https://twitter.com/{uid}'
TWITRSS_URL = 'https://twitrss.me/twitter_user_to_rss/?user={uid}'


def format_title(description):
    b = BeautifulSoup(description, 'html.parser')
    # 去除掉HTML标签
    cleaned_des = b.text.strip()
    rst = re.search(r'【(.*?)】', cleaned_des)
    if rst:
        return rst.group(1)
    # 若内容文字少则直接做为标题
    if len(cleaned_des) <= TITLE_MAX_LENGTH:
        return b.text
    # 否则取第1句的前TITLE_MAX_LENGTH个字符作为标题
    title = cleaned_des[:TITLE_MAX_LENGTH]
    sear = re.search(r'[,.!?;，。！？；\s]', title[::-1])
    if sear:
        title = title[:-sear.end()]
    return title


def convert_url(tweet_text):
    url_tags = tweet_text.find_all(lambda tag: any(attr for attr in tag.attrs if attr == 'data-expanded-url'))
    if url_tags:
        for url_tag in url_tags:
            url = url_tag.get('data-expanded-url')
            url_tag.replace_with('<a href="{url}">网页链接</a>'.format(url=url))
    return tweet_text


def format_status(url):
    bst = BeautifulSoup(requests.get(url).content, 'html.parser')
    # 推特内容
    tweet_text = bst.find('p', class_='tweet-text')
    hidden = tweet_text.find('a', class_='u-hidden')
    if hidden:
        hidden.extract()
    tweet_text = convert_url(tweet_text)
    # 去掉最外层的div，否则若是转推会有换行
    description = ''.join(map(str, tweet_text.contents))
    # 引用推特内容
    quote_author = bst.find('div', class_='QuoteTweet-originalAuthor')
    quote_text = bst.find('div', class_='QuoteTweet-text')
    if quote_author:
        quote_text = convert_url(quote_text)
        quote_author_username = quote_author.find('span', class_='username').b.text
        description += ('<div style="border-left: 3px solid gray; padding-left: 1em;">'
                        '转发@<a href={quote_author_url}>{quote_author_username}</a>：{quote_text}'
                        '</div>'
                        ).format(quote_author_url=TWITTER_USER_URL.format(uid=quote_author_username),
                                 quote_author_username=quote_author_username,
                                 quote_text=''.join(map(str, quote_text.contents)))
    description.replace(r'\n', '<br/>')
    return description


def index(request, uid):
    twitter_url = TWITRSS_URL.format(uid=uid)
    b = BeautifulSoup(requests.get(twitter_url).content, 'xml')
    feed = {
        'version': 'https://jsonfeed.org/version/1',
        'title': uid + "'s twitter",
        'description': uid + "'s twitter",
        'home_page_url': b.rss.channel.link.text,
        'items': []
    }
    for item in b.find_all('item'):
        logging.warning(item.link.text)
        item_url = item.link.text
        description = format_status(item.link.text)
        if item_url.split('/')[3] != uid:
            description = '转推：' + description
        feed_item = {
            'id': item_url,
            'url': item_url,
            'title': format_title(description),
            'content_html': description
        }
        feed['items'].append(feed_item)
    return JsonResponse(feed)
