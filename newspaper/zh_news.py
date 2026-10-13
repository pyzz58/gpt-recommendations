"""Native Chinese article routing; preserve publisher text and attribution.
This layer does NOT infer unverified prices, nor translate Chinese into fake
English quotations. English source editions remain bilingual as before.
"""
import re
def is_chinese(article):
    return article.get("language") == "zh" or bool(re.search(r"[\u4e00-\u9fff]",article.get("title",""))) and len(re.findall(r"[\u4e00-\u9fff]",article.get("title",""))) >= 4

def chinese_sections(article):
    s=(article.get("title","")+" "+article.get("summary",""))
    result=set()
    if re.search(r"美股|华尔街|纳斯达克|标普|道琼斯|美联储|美国国债|美国股市|纽约股市|特斯拉财报|苹果财报",s): result.add("美股与美国金融市场")
    if re.search(r"国际|外交|战争|峰会|停火|联合国|军事|选举|全球|冲突",s): result.add("国际政治与全球事件")
    if re.search(r"人工智能|大模型|算力|数据中心|AI|机器人",s,re.I): result.add("AI与数字产业")
    if re.search(r"科研|芯片|半导体|航空航天|能源|核聚变|量子|材料|卫星",s): result.add("科技、能源与前沿科学")
    if re.search(r"融资|创业|企业|公司|上市|并购|产业|供应链|商业|营收|利润|经济",s): result.add("创业、商业与企业竞争")
    if re.search(r"临床|医学|医疗|健康|药物|疫苗|公共卫生|医院",s): result.add("医疗、生命科学与公共健康")
    if re.search(r"政策|政府|国务院|外交|军事|央行|选举|全国人大|政治",s): result.add("国际政治与全球事件")
    return result

def chinese_importance(article):
    s=article.get("title","")+" "+article.get("summary","")
    structural=bool(re.search(r"国务院|财政部|证监会|中央银行|人民银行|美联储|SEC|监管|政策|批准|经济数据|贸易|关税",s,re.I))
    systemic=bool(re.search(r"全国|全球|国际|美国|中国|市场|产业|国家",s))
    has_change=bool(re.search(r"发布|出台|批准|决定|实施|增长|下降|突破|收购|监管|上调|下调",s))
    return (30 if systemic else 10,25 if structural else 12,20 if structural else 10,15 if has_change else 5)
