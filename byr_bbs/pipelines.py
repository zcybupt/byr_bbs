# -*- coding: utf-8 -*-
import json
import re

import merge


# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html


class ByrBbsPipeline(object):
    def __init__(self):
        self.id = 0
        self.url_set = set()
        self.data_dict = dict()

    def process_item(self, item, spider):
        item_dict = dict(item)
        results = re.findall('https://bbs.byr.cn/#!article/(.*?)/(\d+)', item['url'])
        item_id = results[0][0] + results[0][1]
        if item['url'] not in self.url_set:
            self.url_set.add(item['url'])
            self.data_dict[item['url']] = merge.merge(item_dict, item_dict)
            self.id += 1
        else:
            old = self.data_dict[item_dict['url']]
            self.data_dict[item['url']] = merge.merge(old, item_dict)

        if (self.id % 1000 == 0):
            self.save_data()

        return item

    def save_data(self):
        with open("byr_data.json", "a") as outfile:
            for value in self.data_dict.values():
                outfile.write(json.dumps(value, ensure_ascii=False) + "\n")
        self.data_dict.clear()

    def close_spider(self, spider):
        self.save_data()
        print("close_spider")
