import datetime

from elasticsearch import Elasticsearch

from querysearch import search_by_keyword

es = Elasticsearch(hosts="http://localhost:9200")


def get_demo():
    dsl = {
        "query": {

            "bool": {
                "filter": [
                    {"wildcard": {"url": '*IWhisper*'}},
                    {
                        "range": {
                            'reply_time': {
                                'gte': (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
                            }
                        }
                    }
                ]
            }
        },
        "sort": {
            "articles.voteup_count": {
                "mode": "sum",
                "order": "desc",
            },
            "reply_count": {
                "order": "desc",
            },

        },

        "from": 0, "size": 100,

    }

    result = es.search(index='byr_articles', body=dsl)
    search_by_keyword.print_content(result)


if __name__ == '__main__':
    get_demo()
