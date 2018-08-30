import logging
import re

import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from hanziconv import HanziConv

TITLE_MAX_LENGTH = 30
TWITTER_URL = 'https://twitter.com/{}'
TWITTER_STATUS_URL = 'https://twitter.com/{}/status/{}'
CACHE_TTL = 60 * 60 * 24 * 3

logging.basicConfig(level=logging.INFO)

left_border = '<div style="border-left: 3px solid gray; padding-left: 1em;">{}</div>'


def format_title(description):
    b = BeautifulSoup(description, 'html.parser')
    # 去除掉HTML标签
    cleaned_des = b.text.strip()
    rst = re.search(r'【(.*?)】', cleaned_des)
    if rst:
        cleaned_des = rst.group(1)
    # 若内容文字少则直接做为标题
    if len(cleaned_des) <= TITLE_MAX_LENGTH:
        return cleaned_des
    # 否则取第1句的前TITLE_MAX_LENGTH个字符作为标题
    title = cleaned_des[:TITLE_MAX_LENGTH]
    sear = re.search(r'[,.!?;，。！？；]', title[::-1])
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


def format_status(url, max_iter):
    logging.info('正在抓取网页：' + url)
    bst = BeautifulSoup(requests.get(url).content, 'html.parser')
    permalink_tweet = bst.find('div', class_='permalink-tweet-container')
    return format_container(permalink_tweet, max_iter)


def format_container(container_tag, max_iter):
    # 推特内容
    tweet_text_tag = container_tag.find('p', class_='tweet-text')
    # 表情图片换文字
    all_emojis_tag = tweet_text_tag.find_all('img', class_='Emoji')
    if all_emojis_tag:
        for emoji_tag in all_emojis_tag:
            emoji_tag.replace_with(emoji_tag.get('alt'))
    # 删掉无用标签
    hidden_tag = tweet_text_tag.find('a', class_='u-hidden')
    if hidden_tag:
        hidden_tag.extract()
    # 隐藏所有原样显示的链接
    tweet_text_tag = convert_url(tweet_text_tag)
    # 去掉最外层的div，否则若是转推会有换行
    description = ''.join(map(str, tweet_text_tag.contents))
    # 推文中换行
    description = description.replace('\n', '<br/>')

    # 引用推特内容
    quote_author_tag = container_tag.find('div', class_='QuoteTweet-originalAuthor')
    if quote_author_tag:
        if max_iter <= 0:
            description += '<br/>' * 2 + left_border.format('！！！警告：转发层数太深，请打开网页查看！！！')
        else:
            quote_url_tag = container_tag.find('a', class_='QuoteTweet-link')
            quote_status_url = TWITTER_URL.format(quote_url_tag.get('href')[1:])
            quote_author_username = quote_author_tag.find('span', class_='username').b.text
            quote_author_fullname = quote_author_tag.find('b', class_='QuoteTweet-fullname').text
            description += '<br/>' * 2 + left_border.format(
                '转发@<a href={quote_author_url}>{username}</a>：{quote_text}'.format(
                    quote_author_url=TWITTER_URL.format(quote_author_username),
                    username=quote_author_fullname,
                    quote_text=format_status(quote_status_url, max_iter - 1)))
    # 推文后跟图片或视频
    media_tag = container_tag.find('div', class_='AdaptiveMediaOuterContainer')
    if media_tag:
        # 去掉警告信息
        ts_tag = media_tag.find('div', class_='Tombstone')
        if ts_tag:
            ts_tag.decompose()
        description += '<br/>' + str(media_tag).replace('<img', '<br/><img')
    # 繁体转简体
    description = HanziConv.toSimplified(description)
    return description


def format_twitter(uid, item):
    url = TWITTER_URL.format(item.div.get('data-permalink-path')[1:])
    # 纯转发
    uid_real = url.split('/')[3]
    if uid_real != uid:
        description = format_status(url, 4)
        fullname = item.find('strong', class_='fullname').text
        return '转发' + '<br/>' * 2 + left_border.format(
            '@<a href={url}>{fullname}</a>：{description}'.format(
                url=TWITTER_URL.format(uid_real),
                fullname=fullname,
                description=description)
        )
    else:
        container_tag = item.find('div', class_='content')
        description = format_container(container_tag, 4)
        return description


def index(request, uid):
    twitter_url = TWITTER_URL.format(uid)
    b = BeautifulSoup(requests.get(twitter_url).content, 'html.parser')
    feed = {
        'version': 'https://jsonfeed.org/version/1',
        'title': b.find('h1', class_='ProfileHeaderCard-name').text + '的推特',
        'description': b.find('p', class_='ProfileHeaderCard-bio').text,
        'home_page_url': twitter_url,
        'items': []
    }
    lis_tag = b.find_all('li', class_='js-stream-item')
    if lis_tag:
        for item_tag in lis_tag:
            item_url = TWITTER_URL.format(item_tag.div.get('data-permalink-path')[1:])
            feed_item = {
                'id': item_url,
                'url': item_url
            }
            if cache.get(item_url):
                logging.info('缓存' + item_url)
                feed_item['content_html'] = cache.get(item_url)
            else:
                logging.info(item_url)
                description = format_twitter(uid, item_tag)
                cache.set(item_url, description, CACHE_TTL)
                feed_item['content_html'] = description
            feed_item['title'] = format_title(feed_item['content_html'])
            feed['items'].append(feed_item)
    return JsonResponse(feed)


def home(request):
    url = None
    origin_url = None
    if request.method == 'POST':
        origin_url = request.POST.get('url')
        url = reverse('twitter', args=[origin_url.split('/')[3]])
    return render(request, 'twitter/home.html', {'url': url, 'origin_url': origin_url})
