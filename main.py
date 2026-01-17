import os

import load2es
import merge

if not os.path.exists("byr_data.json"):
    with open("byr_data.json", "a+") as _:
        pass

if not os.path.exists("byr_data_merge.json"):
    with open("byr_data_merge.json", "a+") as _:
        pass

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from byr_bbs.spiders.board_spider import BoardSpiderSpider

process = CrawlerProcess(get_project_settings())
process.crawl(BoardSpiderSpider)
process.start()
process.join()
if True:
    load2es.doLoadEs()
if True:
    # exit(0)
    merge.doMerge()
    os.remove("byr_data.json")
