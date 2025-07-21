# -*- coding: utf-8 -*-
import requests
import json
import time
import re
import pymysql
from transformers import AutoTokenizer, AutoModelForSequenceClassification


def _parse_newcoder_page(data, skip_words, start_date):
    assert data['success'] == True
    pattern = re.compile("|".join(skip_words))
    res = []
    for x in data['data']['records']:
        x = x['data']
        dic = {"user": x['userBrief']['nickname']}

        x = x['contentData'] if 'contentData' in x else x['momentData']
        dic['title'] = x['title']
        dic['content'] = x['content']
        dic['id'] = int(x['id'])
        dic['url'] = 'https://www.nowcoder.com/discuss/' + str(x['id'])
        text = str(x['title']) if x['title'] else "" + str(x['content']) if x['content'] else ""
        if len(skip_words) > 0 and pattern.search(text) != None:  # 关键词正则过滤
            continue

        createdTime = x['createdAt'] if 'createdAt' in x else x['createTime']
        dic['createTime'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(createdTime // 1000))
        dic['editTime'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(x['editTime'] // 1000))

        if dic['editTime'] < start_date:  # 根据时间过滤
            continue
        res.append(dic)

    return res


def get_newcoder_page(page=1, keyword="校招", skip_words=[], start_date='2023'):
    header = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
        "content-type": "application/json"
    }
    data = {
        "type": "all",
        "query": keyword,
        "page": page,
        "tag": [],
        "order": "create"
    }
    x = requests.post('https://gw-c.nowcoder.com/api/sparta/pc/search', data=json.dumps(data), headers=header, )
    data = _parse_newcoder_page(x.json(), skip_words, start_date)
    return data


def upsert_to_db(data, host, user, passwd, database, charset, port):
    db = pymysql.connect(
        host=host,
        user=user,
        passwd=passwd,
        database=database,
        charset=charset,
        port=port
    )
    try:
        cursor = db.cursor()
        sql = "select id, edited_time from newcoder_search where id in ({})".format(
            ",".join([str(x['id']) for x in data]))
        cursor.execute(sql)
        exists = cursor.fetchall()
        dic = {x[0]: x[1].strftime("%Y-%m-%d %H:%M:%S") for x in exists}

        insert_data = [[x[k] for k in x] for x in data if x['id'] not in dic]
        update_data = [(x['editTime'], x['id']) for x in data if x['id'] in dic and dic[x['id']] != x['editTime']]
        sql = "INSERT INTO newcoder_search (user, title, content, id, url, created_time, edited_time) VALUES(%s, %s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, insert_data)
        sql = "update newcoder_search set edited_time = %s where id = %s"
        cursor.executemany(sql, update_data)
        db.commit()
    except Exception as e:
        print("db error: ", e)
    db.close()
    return [x for x in data if x['id'] not in dic], [x for x in data if
                                                     x['id'] in dic and dic[x['id']] != x['editTime']]


def _batch_generate(texts, model, tokenizer, id2label={0: '招聘信息', 1: '经验贴', 2: '求助贴'}, max_length=128):
    inputs = tokenizer(texts, return_tensors="pt", max_length=128, padding=True, truncation=True)
    outputs = model(**inputs).logits.argmax(-1).tolist()
    return [id2label[x] for x in outputs]


def model_predict(text_list, model=None, tokenizer=None, model_name="roberta4h512", batch_size=4):
    if not text_list: return []
    if not model:
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
    if not tokenizer:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
    model.eval()
    result, start = [], 0
    while (start < len(text_list)):
        result.extend(_batch_generate(text_list[start: start + batch_size], model, tokenizer))
        start += batch_size
    return result


def filter(data, unique_content, model=None, tokenizer=None):
    # 模型过滤，根据页面内容去重
    labels = model_predict([(str(x['title']) if x['title'] else "") + "\t" +
                            (str(x['content']) if x['content'] else "") for x in data], model, tokenizer)
    result = []
    for i, x in enumerate(data):
        if x['content'] in unique_content or labels[i] != "招聘信息":
            continue
        unique_content.add(x['content'])
        result.append(x)
    return result


def run(keywords, skip_words, db_config):
    res = []
    for key in keywords:
        print(key, time.strftime("%Y-%m-%d %H:%M:%S"))
        for i in range(1, 21):
            print(i)
            page = get_newcoder_page(i, key, skip_words,
                                     start_date=time.strftime("%Y-%m-%d",
                                                              time.localtime(time.time() - 15 * 24 * 60 * 60)))
            if not page:
                break
            res.extend(page)
            time.sleep(1)

    res.sort(key=lambda x: len(x['content']))
    result, ids = [], set()  # 根据id去重
    for x in res:
        if x['id'] in ids:
            continue
        ids.add(x['id'])
        result.append(x)

    print("total num: ", len(result))
    # print(result)
    insert_data, update_data = upsert_to_db(result, **db_config)  # insert_data, update_data

    # 使用模型过滤数据
    unique_content, shared_model, shared_tokenizer = set(), None, None
    insert_data = filter(insert_data, unique_content, shared_model, shared_tokenizer)
    update_data = filter(update_data, unique_content, shared_model, shared_tokenizer)
    return insert_data, update_data


def main():
    # 指定要过滤的词
    skip_words = ['求捞', '泡池子', '池子了', '池子中', 'offer对比', '总结一下', '给个建议', '开奖群', '没消息', '有消息', '拉垮', '求一个', '求助', '池子的',
                  '决赛圈', 'offer比较', '求捞', '补录面经', '捞捞', '收了我吧', 'offer选择', '有offer了', '想问一下', 'kpi吗', 'kpi面吗', 'kpi面吧']

    # 指定搜索的关键词
    keywords = ['实习', '招聘'， "面经"]

    # 配置数据库信息
    db_config = {
        "host": "localhost",
        "user": "root",
        "passwd": "Cptbtptp1+",
        "database": 'test',
        "charset": 'utf8mb4',
        "port": 3306
    }

    run(keywords, skip_words, db_config)


if __name__ == "__main__":
    main()
    print("end")