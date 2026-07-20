"""
TripCraft RAG 黄金评测数据集

50 条测试查询，覆盖 8 城，3 种类型（精确匹配/语义模糊/否定查询），
3 种难度（easy/medium/hard）。每条查询包含：
- city: 目标城市
- query: 查询文本
- type: exact / semantic / negative
- difficulty: easy / medium / hard
- relevant_docs: 期望命中的 doc_key 列表（基于 seed_data 的 ID 命名规则）
- expected_answer: 期望的生成答案要点（用于 RAGAS 评测）
- notes: 标注说明
"""

from __future__ import annotations

from typing import Any

# 查询类型常量
EXACT = "exact"           # 精确匹配：查询词直接出现在源文档
SEMANTIC = "semantic"     # 语义模糊：查询是改写/意图表达
NEGATIVE = "negative"     # 否定查询：无相关文档


def _doc_key(city: str, category: str, name_or_title: str) -> str:
    """生成与 seed_data.py 一致的 doc_key 前缀。

    category: 'attraction' | 'note'
    """
    if category == "attraction":
        return f"seed_attraction_{city}_{name_or_title}"
    return f"seed_note_{city}_{name_or_title}"


GOLDEN_QUERIES: list[dict[str, Any]] = [
    # ====================================================================
    # 杭州 (7 条: 3 exact + 3 semantic + 1 negative)
    # ====================================================================
    {
        "id": "hz_01",
        "city": "杭州",
        "query": "西湖醋鱼",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("杭州", "note", "杭州美食推荐")],
        "expected_answer": "西湖醋鱼是杭州传统名菜",
    },
    {
        "id": "hz_02",
        "city": "杭州",
        "query": "灵隐寺门票",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("杭州", "attraction", "灵隐寺")],
        "expected_answer": "灵隐寺需要购买飞来峰门票后才能进入",
    },
    {
        "id": "hz_03",
        "city": "杭州",
        "query": "西溪湿地游船",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("杭州", "attraction", "西溪湿地")],
        "expected_answer": "西溪湿地可乘船游览，适合慢游",
    },
    {
        "id": "hz_04",
        "city": "杭州",
        "query": "杭州有什么必吃的特色菜",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("杭州", "note", "杭州美食推荐")],
        "expected_answer": "西湖醋鱼、东坡肉、龙井虾仁、叫化童鸡",
    },
    {
        "id": "hz_05",
        "city": "杭州",
        "query": "带老人杭州2天轻松游怎么安排",
        "type": SEMANTIC,
        "difficulty": "hard",
        "relevant_docs": [
            _doc_key("杭州", "note", "杭州3日游经典路线"),
            _doc_key("杭州", "attraction", "西湖"),
            _doc_key("杭州", "attraction", "灵隐寺"),
        ],
        "expected_answer": "老人游杭州应安排西湖、灵隐寺等经典景点，节奏放慢，避免爬山",
    },
    {
        "id": "hz_06",
        "city": "杭州",
        "query": "杭州龙井茶体验",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("杭州", "note", "杭州3日游经典路线")],
        "expected_answer": "龙井村可体验采茶是杭州特色体验",
    },
    {
        "id": "hz_07",
        "city": "杭州",
        "query": "杭州滑雪场推荐",
        "type": NEGATIVE,
        "difficulty": "medium",
        "relevant_docs": [],
        "expected_answer": "杭州没有滑雪场",
    },

    # ====================================================================
    # 北京 (6 条: 2 exact + 3 semantic + 1 negative)
    # ====================================================================
    {
        "id": "bj_01",
        "city": "北京",
        "query": "八达岭长城缆车",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("北京", "attraction", "长城（八达岭）")],
        "expected_answer": "长城建议去慕田峪段，人少景美，体力不好可选择缆车",
    },
    {
        "id": "bj_02",
        "city": "北京",
        "query": "北京烤鸭推荐",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("北京", "note", "北京美食指南")],
        "expected_answer": "烤鸭推荐便宜坊或四季民福",
    },
    {
        "id": "bj_03",
        "city": "北京",
        "query": "北京三日游经典路线",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("北京", "note", "北京5日游攻略")],
        "expected_answer": "故宫、长城、颐和园、天坛是必去景点",
    },
    {
        "id": "bj_04",
        "city": "北京",
        "query": "北京带老人游哪些景点合适",
        "type": SEMANTIC,
        "difficulty": "hard",
        "relevant_docs": [
            _doc_key("北京", "attraction", "故宫"),
            _doc_key("北京", "attraction", "颐和园"),
        ],
        "expected_answer": "故宫适合老人慢游，颐和园可乘船，长城对老人有挑战",
    },
    {
        "id": "bj_05",
        "city": "北京",
        "query": "北京胡同文化体验",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [
            _doc_key("北京", "attraction", "南锣鼓巷"),
            _doc_key("北京", "note", "北京5日游攻略"),
        ],
        "expected_answer": "五道营胡同比南锣鼓巷更地道",
    },
    {
        "id": "bj_06",
        "city": "北京",
        "query": "北京看海去哪里",
        "type": NEGATIVE,
        "difficulty": "medium",
        "relevant_docs": [],
        "expected_answer": "北京不靠海，无海滩景点",
    },

    # ====================================================================
    # 上海 (6 条: 2 exact + 3 semantic + 1 negative)
    # ====================================================================
    {
        "id": "sh_01",
        "city": "上海",
        "query": "外滩夜景",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("上海", "attraction", "外滩")],
        "expected_answer": "外滩夜景比白天更美，万国建筑博览群",
    },
    {
        "id": "sh_02",
        "city": "上海",
        "query": "上海迪士尼攻略",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("上海", "attraction", "迪士尼乐园")],
        "expected_answer": "迪士尼建议工作日前往，周末人很多",
    },
    {
        "id": "sh_03",
        "city": "上海",
        "query": "上海坐船看黄浦江两岸",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("上海", "note", "上海交通提示")],
        "expected_answer": "外滩到陆家嘴可坐轮渡",
    },
    {
        "id": "sh_04",
        "city": "上海",
        "query": "上海本帮菜推荐",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("上海", "note", "上海美食攻略")],
        "expected_answer": "小笼包、生煎、蟹壳黄、本帮菜",
    },
    {
        "id": "sh_05",
        "city": "上海",
        "query": "上海亲子游好去处",
        "type": SEMANTIC,
        "difficulty": "hard",
        "relevant_docs": [
            _doc_key("上海", "attraction", "迪士尼乐园"),
            _doc_key("上海", "attraction", "东方明珠"),
        ],
        "expected_answer": "迪士尼乐园和田子坊适合亲子游",
    },
    {
        "id": "sh_06",
        "city": "上海",
        "query": "上海爬山去哪里",
        "type": NEGATIVE,
        "difficulty": "easy",
        "relevant_docs": [],
        "expected_answer": "上海无山可爬",
    },

    # ====================================================================
    # 成都 (6 条: 2 exact + 3 semantic + 1 negative)
    # ====================================================================
    {
        "id": "cd_01",
        "city": "成都",
        "query": "大熊猫基地几点去合适",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("成都", "attraction", "大熊猫基地")],
        "expected_answer": "大熊猫基地建议早上8点前到，熊猫更活跃",
    },
    {
        "id": "cd_02",
        "city": "成都",
        "query": "成都火锅推荐",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("成都", "note", "成都美食地图")],
        "expected_answer": "火锅推荐社区小店，串串推荐马路边边",
    },
    {
        "id": "cd_03",
        "city": "成都",
        "query": "成都周边一日游",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [
            _doc_key("成都", "attraction", "青城山"),
            _doc_key("成都", "attraction", "都江堰"),
        ],
        "expected_answer": "都江堰+青城山可安排一日游",
    },
    {
        "id": "cd_04",
        "city": "成都",
        "query": "成都慢生活体验在哪里",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [
            _doc_key("成都", "attraction", "宽窄巷子"),
            _doc_key("成都", "note", "成都旅游贴士"),
        ],
        "expected_answer": "人民公园比宽窄巷子更地道，体验慢生活",
    },
    {
        "id": "cd_05",
        "city": "成都",
        "query": "成都看川剧变脸去哪里",
        "type": SEMANTIC,
        "difficulty": "hard",
        "relevant_docs": [_doc_key("成都", "attraction", "宽窄巷子")],
        "expected_answer": "宽窄巷子可以看川剧变脸",
    },
    {
        "id": "cd_06",
        "city": "成都",
        "query": "成都看海",
        "type": NEGATIVE,
        "difficulty": "easy",
        "relevant_docs": [],
        "expected_answer": "成都不靠海，无海可看",
    },

    # ====================================================================
    # 西安 (6 条: 2 exact + 3 semantic + 1 negative)
    # ====================================================================
    {
        "id": "xa_01",
        "city": "西安",
        "query": "兵马俑请讲解",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("西安", "attraction", "兵马俑")],
        "expected_answer": "兵马俑建议请讲解员或租语音导览，否则体验打折扣",
    },
    {
        "id": "xa_02",
        "city": "西安",
        "query": "西安回民街美食",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("西安", "attraction", "回民街")],
        "expected_answer": "回民街有很多清真小吃，但人多价高，周边小巷更实惠",
    },
    {
        "id": "xa_03",
        "city": "西安",
        "query": "西安城墙骑行最佳时间",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("西安", "note", "西安美食攻略")],
        "expected_answer": "城墙骑行建议傍晚，不晒且景色好",
    },
    {
        "id": "xa_04",
        "city": "西安",
        "query": "西安带老人怎么玩轻松",
        "type": SEMANTIC,
        "difficulty": "hard",
        "relevant_docs": [
            _doc_key("西安", "attraction", "兵马俑"),
            _doc_key("西安", "attraction", "大雁塔"),
        ],
        "expected_answer": "兵马俑请讲解，大雁塔可登塔俯瞰，城墙骑行适合体力好的游客",
    },
    {
        "id": "xa_05",
        "city": "西安",
        "query": "陕西历史博物馆预约",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("西安", "note", "西安美食攻略")],
        "expected_answer": "陕西历史博物馆需提前3天预约",
    },
    {
        "id": "xa_06",
        "city": "西安",
        "query": "西安滑雪",
        "type": NEGATIVE,
        "difficulty": "easy",
        "relevant_docs": [],
        "expected_answer": "西安市区无滑雪场",
    },

    # ====================================================================
    # 南京 (6 条: 2 exact + 3 semantic + 1 negative)
    # ====================================================================
    {
        "id": "nj_01",
        "city": "南京",
        "query": "南京盐水鸭推荐",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("南京", "note", "南京美食指南")],
        "expected_answer": "韩复兴盐水鸭是南京特色",
    },
    {
        "id": "nj_02",
        "city": "南京",
        "query": "中山陵周一闭馆",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("南京", "attraction", "中山陵")],
        "expected_answer": "中山陵周一闭馆，需提前预约",
    },
    {
        "id": "nj_03",
        "city": "南京",
        "query": "南京历史一日游怎么安排",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [
            _doc_key("南京", "attraction", "中山陵"),
            _doc_key("南京", "attraction", "明孝陵"),
            _doc_key("南京", "attraction", "总统府"),
        ],
        "expected_answer": "中山陵+明孝陵+总统府是南京历史一日游经典路线",
    },
    {
        "id": "nj_04",
        "city": "南京",
        "query": "南京秦淮河夜游",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("南京", "attraction", "夫子庙")],
        "expected_answer": "夫子庙夜景比白天更有韵味，秦淮河夜游体验佳",
    },
    {
        "id": "nj_05",
        "city": "南京",
        "query": "南京博物院参观攻略",
        "type": SEMANTIC,
        "difficulty": "hard",
        "relevant_docs": [_doc_key("南京", "note", "南京历史贴士")],
        "expected_answer": "南京博物院免费但需提前3天预约，周一闭馆",
    },
    {
        "id": "nj_06",
        "city": "南京",
        "query": "南京看海",
        "type": NEGATIVE,
        "difficulty": "easy",
        "relevant_docs": [],
        "expected_answer": "南京不靠海",
    },

    # ====================================================================
    # 重庆 (6 条: 2 exact + 3 semantic + 1 negative)
    # ====================================================================
    {
        "id": "cq_01",
        "city": "重庆",
        "query": "洪崖洞几点亮灯",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("重庆", "attraction", "洪崖洞")],
        "expected_answer": "洪崖洞晚上亮灯后约19:00-23:00最壮观",
    },
    {
        "id": "cq_02",
        "city": "重庆",
        "query": "重庆火锅微辣够了",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("重庆", "note", "重庆火锅地图")],
        "expected_answer": "重庆火锅微辣对外地人已足够辣，建议鸳鸯锅",
    },
    {
        "id": "cq_03",
        "city": "重庆",
        "query": "重庆坐索道看江景",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("重庆", "attraction", "长江索道")],
        "expected_answer": "长江索道傍晚乘坐可看日落和夜景",
    },
    {
        "id": "cq_04",
        "city": "重庆",
        "query": "重庆一天打卡路线",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [
            _doc_key("重庆", "attraction", "洪崖洞"),
            _doc_key("重庆", "attraction", "长江索道"),
            _doc_key("重庆", "attraction", "磁器口古镇"),
        ],
        "expected_answer": "解放碑+洪崖洞+长江索道是经典一日路线，磁器口需半天",
    },
    {
        "id": "cq_05",
        "city": "重庆",
        "query": "重庆武隆怎么去",
        "type": SEMANTIC,
        "difficulty": "hard",
        "relevant_docs": [_doc_key("重庆", "attraction", "武隆天坑")],
        "expected_answer": "武隆距市区约3小时车程，建议跟团或包车前往",
    },
    {
        "id": "cq_06",
        "city": "重庆",
        "query": "重庆看海",
        "type": NEGATIVE,
        "difficulty": "easy",
        "relevant_docs": [],
        "expected_answer": "重庆不靠海",
    },

    # ====================================================================
    # 苏州 (7 条: 3 exact + 3 semantic + 1 negative) — 补齐到 50 条
    # ====================================================================
    {
        "id": "sz_01",
        "city": "苏州",
        "query": "拙政园游览时长",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("苏州", "attraction", "拙政园")],
        "expected_answer": "拙政园建议游览2小时",
    },
    {
        "id": "sz_02",
        "city": "苏州",
        "query": "苏州松鼠桂鱼",
        "type": EXACT,
        "difficulty": "easy",
        "relevant_docs": [_doc_key("苏州", "note", "苏州美食推荐")],
        "expected_answer": "松鼠桂鱼是苏州特色菜，偏甜口味",
    },
    {
        "id": "sz_03",
        "city": "苏州",
        "query": "虎丘塔为什么是斜的",
        "type": EXACT,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("苏州", "attraction", "虎丘")],
        "expected_answer": "虎丘塔是中国第一斜塔，苏东坡说'到苏州不游虎丘乃憾事也'",
    },
    {
        "id": "sz_04",
        "city": "苏州",
        "query": "苏州坐船游古城河",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("苏州", "note", "苏州园林游览建议")],
        "expected_answer": "坐船游古城河是苏州独特体验",
    },
    {
        "id": "sz_05",
        "city": "苏州",
        "query": "苏州一天游园林怎么选",
        "type": SEMANTIC,
        "difficulty": "hard",
        "relevant_docs": [
            _doc_key("苏州", "attraction", "拙政园"),
            _doc_key("苏州", "note", "苏州园林游览建议"),
        ],
        "expected_answer": "选1-2个精听讲解，拙政园+留园或狮子林，比走马观花效果好",
    },
    {
        "id": "sz_06",
        "city": "苏州",
        "query": "苏州周庄一日游",
        "type": SEMANTIC,
        "difficulty": "medium",
        "relevant_docs": [_doc_key("苏州", "attraction", "周庄古镇")],
        "expected_answer": "周庄距市区约1小时车程，建议傍晚去游客少且夜景美",
    },
    {
        "id": "sz_07",
        "city": "苏州",
        "query": "苏州爬山去哪里",
        "type": NEGATIVE,
        "difficulty": "easy",
        "relevant_docs": [],
        "expected_answer": "苏州无山可爬",
    },
]


def get_all_queries() -> list[dict[str, Any]]:
    """返回全部 50 条黄金查询"""
    return GOLDEN_QUERIES


def get_queries_by_type(q_type: str) -> list[dict[str, Any]]:
    """按类型筛选查询"""
    return [q for q in GOLDEN_QUERIES if q["type"] == q_type]


def get_queries_by_city(city: str) -> list[dict[str, Any]]:
    """按城市筛选查询"""
    return [q for q in GOLDEN_QUERIES if q["city"] == city]


def get_queries_by_difficulty(difficulty: str) -> list[dict[str, Any]]:
    """按难度筛选查询"""
    return [q for q in GOLDEN_QUERIES if q["difficulty"] == difficulty]


def dataset_stats() -> dict[str, Any]:
    """返回数据集统计信息"""
    cities = set(q["city"] for q in GOLDEN_QUERIES)
    types = {t: len(get_queries_by_type(t)) for t in [EXACT, SEMANTIC, NEGATIVE]}
    difficulties = {d: len(get_queries_by_difficulty(d)) for d in ["easy", "medium", "hard"]}
    return {
        "total": len(GOLDEN_QUERIES),
        "cities": sorted(cities),
        "by_type": types,
        "by_difficulty": difficulties,
    }
