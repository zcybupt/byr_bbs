# -*- coding: utf-8 -*-
import datetime
import json
import math
import re
from copy import deepcopy

import scrapy

import merge
from byr_bbs.items import BoardItem, ArticleItem
from .bbs_config import HEADERS, LOGIN_FORM_DATA


def normalized_time(input_time_str):
    if ("今天" in input_time_str):
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        return input_time_str.replace("今天", today_str)
    if ("分钟前" in input_time_str):
        minue = int(input_time_str[:input_time_str.find("分钟前")])
        return (datetime.datetime.now() - datetime.timedelta(minutes=minue)).strftime("%Y-%m-%d %H:%M:%S")
    if ("刚刚" in input_time_str):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return input_time_str


def check_time(input_time_str):
    if ("今天" in input_time_str):
        return False
    if ("分钟前" in input_time_str):
        return False
    if ("刚刚" in input_time_str):
        return False
    return True


def check_time_for_item(item):
    for article in item['articles']:
        if not check_time(article['time']):
            return False
    if not check_time(item['reply_time']):
        return False
    return True


def getHistory():
    data_dict = dict()

    with open("byr_data_merge.json", "r") as infile:
        method_name(data_dict, infile)
    with open("byr_data.json", "r") as infile:
        method_name(data_dict, infile)
    return data_dict


def method_name(data_dict, infile):
    for line in infile:
        item = json.loads(line)
        item_dict = dict(item)
        data_dict[item['url']] = {
            "reply_count": item["reply_count"],
            "reply_time": item["reply_time"],
            "articles": item["articles"],
        }


class BoardSpiderSpider(scrapy.Spider):
    name = 'board_spider'
    allowed_domains = ['byr.cn']
    start_urls = ['https://bbs.byr.cn/index']
    replace_dict = {
        "&nbsp;": " ",
        "<br/>": "\n",
        "<br />": "\n",
        "<br/><br/>": "\n",
        "<br>--": "",
        "&gt;": ">",
        "_&lt;": "<",
    }
    filter_pattern = re.compile('|<img border="[\S]*" src="[\S]*" alt="[\S]*" class="[\S]*" title="[\S]*"/>'
                                '|<span class="emoji" style=".*".*</span>'
                                '|<img src=".*" alt=".*" style=".*"/>')

    re_replace_dict = [
        (
            re.compile(r'<a target="_blank" href="([\S]*)">单击此查看原图(([\S]*))</a>'),
            r' https://bbs.byr.cn/\1 '
        ),
        (
            re.compile(r'<a href="(.*)" target="_blank" <font color=".*">附件.*</font>.*</a>'),
            r' https://bbs.byr.cn/\1 '
        ),
        (
            re.compile(r'<a target=".*" href="(.*)".*</a>'),
            r' \1 '
        )
    ]

    data_dict = getHistory()

    skip_count = 0

    def start_requests(self):
        try:
            yield scrapy.Request(
                url='https://bbs.byr.cn/index',
                meta={'cookiejar': 1},
                cookies=None,
                callback=self.post_login
            )
        except:
            print(">>>>>>>>>>>>>> Proxy not reachable")

    def post_login(self, response):
        yield scrapy.FormRequest.from_response(
            response,
            url='https://bbs.byr.cn/user/ajax_login.json',
            meta={'cookiejar': response.meta['cookiejar']},
            headers=HEADERS,
            formdata=LOGIN_FORM_DATA,
            callback=self.after_login
        )

    def after_login(self, response):
        yield scrapy.Request(
            url='https://bbs.byr.cn/n/b/section.json',
            meta={'cookiejar': response.meta['cookiejar']},
            callback=self.parse_board
        )

    def parse_board(self, response):
        json_dict = json.loads(response.body.decode('utf8'))
        json_boards = json_dict['data']['boards'][1:]
        # json_boards.append(json.loads('''{"name":"","children":[{"id":"IWhisper","name":"悄悄话","children":[]}]}'''))
        for json_board in json_boards:
            for child_board in json_board['children']:
                item = BoardItem()
                if len(child_board['children']) == 0:
                    item['board_name'] = child_board['name']
                    item['board_url'] = 'https://bbs.byr.cn/n/board/' + child_board['id']
                    item['parent_section'] = json_board['name']
                    yield scrapy.Request(
                        url='https://bbs.byr.cn/n/b/board/' + child_board['id'] + '.json?page=1',
                        meta={
                            'cookiejar': response.meta['cookiejar'],
                            'id': child_board['id']
                        },
                        callback=self.parse_article_url
                    )
                for grandchild_board in child_board['children']:
                    item['board_name'] = grandchild_board['name']
                    item['board_url'] = 'https://bbs.byr.cn/n/board/' + grandchild_board['id']
                    item['parent_section'] = json_board['name']
                    yield scrapy.Request(
                        url='https://bbs.byr.cn/n/b/board/' + child_board['id'] + '.json?page=1',
                        meta={
                            'cookiejar': response.meta['cookiejar'],
                            'id': child_board['id']
                        },
                        callback=self.parse_article_url
                    )

    def parse_article_url(self, response):
        json_dict = json.loads(response.body.decode('utf8'))
        total_page = json_dict['data']['pagination']['total']
        current_page = json_dict['data']['pagination']['current']
        post_list = json_dict['data']['posts']
        has_new_reply = False
        for post in post_list:
            url = 'https://bbs.byr.cn/#!article/' + json_dict['data']['name'] + '/' + str(post['gid'])
            if (url in self.data_dict
                    and post['replyCount'] <= self.data_dict[url]['reply_count']
                    and (normalized_time(post['replyTime']) <= normalized_time(self.data_dict[url]['reply_time']))
                    and check_time_for_item(self.data_dict[url])):
                self.skip_count += 1
                if (self.skip_count % 10000 == 0):
                    print("skip:", self.skip_count)
                continue
            # if url in ["https://bbs.byr.cn/#!article/Constellations/465260",
            #            "https://bbs.byr.cn/#!article/Constellations/408580",
            #            "https://bbs.byr.cn/#!article/Constellations/326533",
            #            ]:
            #     continue
            has_new_reply = True
            item = ArticleItem()
            item['title'] = post['title']
            item['poster'] = post['poster']
            item['gid'] = post['gid']
            item['url'] = url
            item['reply_time'] = normalized_time(post['replyTime'])
            item['reply_count'] = post['replyCount']
            max_page = math.ceil((1 + int(post['replyCount'])) / 10)
            yield scrapy.Request(
                url='https://bbs.byr.cn/n/b/article/' + json_dict['data']['name'] + '/'
                    + str(post['gid']) + '.json?page=' + str(max_page),
                meta={
                    'item': deepcopy(item),
                    'name': json_dict['data']['name']
                },
                callback=self.parse_articles
            )
        # 翻页
        if has_new_reply and current_page <= total_page:
            current_page += 1
            yield scrapy.Request(
                url='https://bbs.byr.cn/n/b/board/' + response.meta['id'] + '.json?page=' + str(current_page),
                meta={
                    'cookiejar': response.meta['cookiejar'],
                    'id': response.meta['id']
                },
                callback=self.parse_article_url
            )

    def parse_articles(self, response):
        try:
            json_dict = json.loads(response.body.decode('utf8'))
        except:
            return
        total_page = json_dict['data']['pagination']['total']
        current_page = json_dict['data']['pagination']['current']
        article_list = json_dict['data']['articles']
        item = response.meta['item']
        articles = []
        has_old_reply = False
        url = 'https://bbs.byr.cn/#!article/' + response.meta['name'] + '/' + str(item['gid'])
        old_article_keys = set()
        if url in self.data_dict:
            for old_article in self.data_dict[url]['articles']:
                old_article_keys.add(merge.key_exactor(old_article))

        for article in article_list:
            contents = dict()
            contents['id'] = article['poster']['id']
            contents['user_name'] = article['poster'].get('user_name', None)
            contents['time'] = normalized_time(article['time'])
            article_content = article['content']
            for old in self.replace_dict:
                new = self.replace_dict[old]
                article_content = article_content.replace(old, new)
            article_content = self.filter_pattern.sub('', article_content)
            for (old, new) in self.re_replace_dict:
                article_content = old.sub(new, article_content)
            contents['article_contents'] = article_content
            contents['voteup_count'] = article['voteup_count']
            contents['votedown_count'] = article['votedown_count']
            contents['pos'] = article['pos']
            articles.append(contents)
            if merge.key_exactor(contents) in old_article_keys:
                print("skip:", merge.key_exactor(contents))
                has_old_reply = True
        if (item.get('articles') is None):
            item['articles'] = []
        item['articles'] = item['articles'] + articles

        # 翻页
        if has_old_reply == False and current_page > 1:
            current_page -= 1
            yield scrapy.Request(
                url='https://bbs.byr.cn/n/b/article/' + response.meta['name'] + '/'
                    + str(item['gid']) + '.json?page=' + str(current_page),
                meta={
                    'item': deepcopy(item),
                    'name': response.meta['name']
                },
                callback=self.parse_articles
            )
        else:
            if url in self.data_dict:
                old = self.data_dict[url]
                item = merge.merge(old, item)
            print(json.dumps(dict(item), ensure_ascii=False))
            yield item
