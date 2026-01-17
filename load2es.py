# -*- coding: utf-8 -*-
import json
import re
import time

from elasticsearch import Elasticsearch, helpers


def get_mapping():
    return {
        "mappings": {
            "properties": {
                "articles": {
                    "properties": {
                        "article_contents": {
                            "type": "text",
                            "analyzer": "ik_smart",
                            "fields": {
                                "keyword": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                }
                            }
                        },
                        "id": {
                            "type": "keyword"
                        },
                        "pos": {
                            "type": "long"
                        },
                        "time": {
                            "type": "keyword"
                        },
                        "user_name": {
                            "type": "keyword"
                        },
                        "votedown_count": {
                            "type": "long"
                        },
                        "voteup_count": {
                            "type": "long"
                        }
                    }
                },
                "gid": {
                    "type": "long"
                },
                "poster": {
                    "type": "keyword"
                },
                "reply_count": {
                    "type": "long"
                },
                "reply_time": {
                    "type": "keyword"
                },
                "title": {
                    "type": "text",
                    "analyzer": "ik_smart",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                },
                "url": {
                    "type": "keyword"
                }
            }
        }
    }


class LoadEs(object):
    def __init__(self):
        self.es = Elasticsearch(hosts="http://localhost:9200")
        self.tmp_set = set()
        if not self.es.indices.exists(index='byr_articles'):
            self.es.indices.create(index='byr_articles', body=get_mapping())

    def process_item(self, fileName, batch_size=1000):
        i = 0
        actions = []
        start_time = time.time()
        for line in open(fileName, "r", encoding="utf-8"):
            i += 1
            try:
                item = json.loads(line.strip())
                results = re.findall('https://bbs.byr.cn/#!article/(.*?)/(\d+)', item['url'])
                if not results:
                    continue
                item_id = results[0][0] + results[0][1]
                self.tmp_set.add(item['url'])

                action = {
                    "_index": "byr_articles",
                    "_id": item_id,
                    "_source": item
                }
                actions.append(action)

                if len(actions) >= batch_size:
                    helpers.bulk(self.es, actions)
                    actions.clear()
                    print(f"已插入 {i} 条，唯一 URL 数量：{len(self.tmp_set)}", i / (time.time() - start_time))

            except Exception as e:
                print("解析失败的行：", line)
                print("异常：", e)

        if actions:
            helpers.bulk(self.es, actions)
            print(f"插入最后一批，总计 {i} 条记录")

        print(f"所有数据导入完成，去重后 URL 数量：{len(self.tmp_set)}")


def doLoadEs(fileName='byr_data.json'):
    load = LoadEs()
    load.process_item(fileName)


if __name__ == '__main__':
    doLoadEs(fileName='byr_data_merge.json')
