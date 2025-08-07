import json
import re

from elasticsearch import Elasticsearch

es = Elasticsearch(hosts="http://localhost:9200")


def search_demo():
    words = ["tym"]

    dsl = {
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": [

                        ],
                        "filter": [
                            {
                                "range": {
                                    'reply_time': {
                                        # 'gte': '2025-06-01',
                                        # 'lte': '2025-07-01',
                                    }
                                }
                            }

                        ],
                    }
                },
                "functions": [
                    {
                        "script_score": {
                            "script": {
                                # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-script-score-query.html
                                "source": "Math.log10(2+(doc['articles.voteup_count'].sum()))",
                                "lang": "painless"
                            },
                        },
                        "weight": 0.1
                    },
                    {
                        "field_value_factor": {
                            "field": "reply_count",
                            "modifier": "log2p",  # ln2p，log2p
                            "factor": 0.5
                        },
                        "weight": 0.1
                    },
                ],
                "score_mode": "sum",  # functions内的组合方式
                "boost_mode": "multiply",  # query和functions的组合方式
                "max_boost": 3
            },

        },

        "sort": {
            "_score": {"order": "desc"},
            "articles.voteup_count": {
                "mode": "sum",
                "order": "desc",
            },
            "reply_count": {
                "order": "desc",
            },

        },
        "from": 0, "size": 40,

    }

    for word in words:
        condition = dsl["query"]["function_score"]["query"]["bool"]["should"]
        condition.append(
            {"match": {"title": {"query": word, "boost": 20}}})
        condition.append(
            {"match": {"articles.article_contents": {"query": word, "boost": 10}}})
        condition.append(
            {"wildcard": {"title": {"value": "*{}*".format(word), "boost": 40}}})
        condition.append(
            {"match_phrase": {"articles.article_contents": {"query": word, "boost": 30}}})
        condition.append({"wildcard": {"title.keyword": '*' + word + '*'}})

    not_use_voteup_count = False
    if not_use_voteup_count:
        dsl["query"]["function_score"]["functions"] = None

    explain = False
    if explain:
        dsl["explain"] = True
        dsl["size"] = 2
    result = es.search(index='byr_articles', body=dsl)
    if explain:
        print(json.dumps(result.body, ensure_ascii=False))

    print_content(result)


def print_content(result):
    print("总结以下内容：")
    for item in result["hits"]["hits"]:
        # print(item["_source"]["title"], item["_source"]["url"], item["_source"]["reply_time"])
        print(item["_source"]["title"], item["_source"]["reply_time"])
        key = lambda item: (int(item['voteup_count']))
        item['_source']['articles'].sort(key=key, reverse=True)
        cnt = 0
        for article in item['_source']['articles']:
            if (int(article['voteup_count']) == 0):
                break
            article['article_contents'] = exact_content(article['article_contents'])
            if "\n" in article['article_contents']:
                print(
                    article['voteup_count'] + "赞" + "\n" + "    " + "\n    ".join(
                        article['article_contents'].split("\n")))
            else:
                print(article['voteup_count'] + "赞" + " " + article['article_contents'])
            cnt += 1
            if cnt > 20:
                break
        print('=' * 100)


def exact_content(article_content):
    ref2_re = re.compile(r'【 在 .+ 的大作中提到: 】\n(:.+\n)+((.*\n*)+$)')
    if "【 在 " in article_content:
        if not article_content.startswith(" 【 在 ") and not article_content.startswith("【 在 "):
            article_content = article_content[:article_content.find("【 在 ")]
        match = ref2_re.match(article_content)
        if match is not None:
            article_content = match.group(2)
    article_content = article_content.replace("\n\n", "\n")
    article_content = article_content.replace("<b>", "")
    article_content = article_content.replace("</b>", "")
    if article_content.endswith("\n"):
        article_content = article_content[:-1]
    return article_content


if __name__ == '__main__':
    search_demo()
