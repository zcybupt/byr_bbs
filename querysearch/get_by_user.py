from elasticsearch import Elasticsearch

import search_by_keyword

es = Elasticsearch(hosts="http://localhost:9200")


def get_demo():
    author = ""

    dsl = {
        "query": {

            "bool": {
                "filter": [
                    {"term": {"articles.id": author}},
                ]
            }
        },
        "sort": {
            # "articles.voteup_count": {
            #     "order": "desc",
            # },
            "articles.time": {
                "order": "desc",
            },
        },

        "from": 0, "size": 200,

    }

    result = es.search(index='byr_articles', body=dsl)
    for item in result["hits"]["hits"]:
        text = ''
        for article in item['_source']['articles']:
            if article['id'] == author:
                article['article_contents'] = search_by_keyword.exact_content(article['article_contents'])
                text = text + "\n" + article['time'] + " " + article['article_contents']
        print(item["_source"]["title"], item["_source"]["url"])
        print(text)
        print('=' * 20)


get_demo()
