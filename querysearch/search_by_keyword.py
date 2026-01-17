import json
import re

from elasticsearch import Elasticsearch

# 初始化 ES 客户端
es = Elasticsearch(hosts="http://localhost:9200")


def search_demo():
    words = [""]

    dsl = {
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "should": [
                            # 这里的内容会在下方循环中动态添加
                        ],
                        "filter": [
                            {
                                "range": {
                                    'reply_time': {
                                        # 'gte': '2025-01-01',
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1  # 至少匹配一个条件
                    }
                },
                "functions": [
                    {
                        # 算分逻辑1：点赞数加权
                        "script_score": {
                            "script": {
                                # log10(2 + sum) 平滑处理，避免0赞报错，同时防止超高赞彻底掩盖文本相关性
                                "source": "Math.log10(2 + doc['articles.voteup_count'].sum())",
                                "lang": "painless"
                            },
                        },
                        "weight": 2.0  # 提高点赞的权重
                    },
                    {
                        # 算分逻辑2：回复数加权
                        "field_value_factor": {
                            "field": "reply_count",
                            "modifier": "log1p",  # log(1+v)，平滑处理
                            "factor": 1.2
                        },
                        "weight": 1.0
                    },
                ],
                "score_mode": "sum",  # functions 内部：点赞分 + 回复分
                "boost_mode": "multiply",  # 最终得分：文本相关性分 * (热度分)
                "max_boost": 10  # 允许热度最大放大 10 倍
            },

        },
        # 【优化】移除 sort 字段，直接使用 function_score 计算出的 _score 倒序排列
        # 这样既能保证搜出的内容是相关的，又能让高赞的排在前面
        "sort": [
            {"_score": {"order": "desc"}}
        ],
        "_source": ["title", "url", "reply_time", "articles", "reply_count", "voteup_count"],  # 仅返回需要字段
        "from": 0,
        "size": 40,
    }

    # 动态构建查询文本条件
    condition = dsl["query"]["function_score"]["query"]["bool"]["should"]

    for word in words:
        # 1. 标题匹配（权重最高）
        condition.append({
            "match": {
                "title": {
                    "query": word,
                    "boost": 10
                }
            }
        })
        # 2. 标题短语匹配（包含且顺序接近，权重极高）
        condition.append({
            "match_phrase": {
                "title": {
                    "query": word,
                    "boost": 20,
                    "slop": 2  # 允许中间隔几个词
                }
            }
        })
        # 3. 内容匹配
        condition.append({
            "match": {
                "articles.article_contents": {
                    "query": word,
                    "boost": 5
                }
            }
        })
        # 4. 内容短语匹配
        condition.append({
            "match_phrase": {
                "articles.article_contents": {
                    "query": word,
                    "boost": 10
                }
            }
        })
        # 【优化】移除了 wildcard 查询 (*word*)。
        # wildcard 性能极差且容易导致内存溢出。
        # 应该依赖 IK 分词器或 Ngram 分词器来解决部分匹配问题。

    # 是否解释查询计划（调试用）
    explain = False
    if explain:
        dsl["explain"] = True
        dsl["size"] = 2

    # 执行搜索
    try:
        result = es.search(index='byr_articles', body=dsl)
        if explain:
            print(json.dumps(result.body, ensure_ascii=False))

        print_content(result)
    except Exception as e:
        print(f"查询出错: {e}")


def print_content(result):
    print(f"搜索到 {result['hits']['total']['value']} 条结果，前 {len(result['hits']['hits'])} 条如下：")
    print("-" * 50)

    for item in result["hits"]["hits"]:
        source = item["_source"]
        # 安全获取字段，防止字段缺失报错
        title = source.get("title", "无标题")
        url = source.get("url", "")
        reply_time = source.get("reply_time", "")

        print(f"标题: {title}")
        print(f"链接: {url}")
        print(f"时间: {reply_time}")

        # 对帖子内的回复按点赞数进行Python层面的排序
        articles = source.get('articles', [])
        if articles:
            # key 函数优化：处理可能存在的 None 或非数字类型
            key = lambda x: int(x.get('voteup_count', 0) or 0)
            articles.sort(key=key, reverse=True)

            cnt = 0
            for article in articles:
                vote_count = int(article.get('voteup_count', 0) or 0)

                # 只显示有点赞的评论，或者前几条
                if vote_count == 0 and cnt > 0:
                    break

                content = exact_content(article.get('article_contents', ''))

                # 【修正】str(vote_count) 避免 int 和 str 拼接报错
                prefix = f"[{str(vote_count)}赞] "
                # prefix+=str(article['id'])

                if "\n" in content:
                    formatted_content = "\n    ".join(content.split("\n"))
                    print(prefix + "\n    " + formatted_content)
                else:
                    print(prefix + content)

                cnt += 1
                if cnt > 20:  # 限制每个帖子只显示前 5 条高赞回复，避免刷屏
                    break
        print('\n' + "=" * 50 + '\n')


def exact_content(article_content):
    if not article_content:
        return ""

    # 处理 "【 在 ... 的大作中提到: 】" 这种引用格式
    ref2_re = re.compile(r'【 在 .+ 的大作中提到: 】\n(:.+\n)+((.*\n*)+$)')

    if "【 在 " in article_content:
        # 尝试去除引用头部
        if not article_content.strip().startswith("【 在 "):
            # 如果引用不在开头，截取到引用之前
            idx = article_content.find("【 在 ")
            if idx > 0:
                article_content = article_content[:idx]

        # 尝试提取引用后的正文
        match = ref2_re.match(article_content)
        if match is not None:
            try:
                article_content = match.group(2)
            except IndexError:
                pass

    # 清洗 HTML 标签和多余换行
    article_content = article_content.replace("\n\n", "\n")
    article_content = article_content.replace("<b>", "").replace("</b>", "")

    return article_content.strip()


if __name__ == '__main__':
    search_demo()
