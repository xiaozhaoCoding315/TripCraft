"""
TripCraft RAG Seed Data Service

Pre-populates Qdrant with travel notes and attraction data for popular destinations.
This ensures the RAG system provides useful recommendations even without manual data ingestion.
"""

import json
import logging
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.models.travel import RagDocument

logger = logging.getLogger(__name__)

# Seed data for popular Chinese destinations
DESTINATION_SEED_DATA: dict[str, dict[str, Any]] = {
    "杭州": {
        "attractions": [
            {
                "name": "西湖",
                "type": "自然风光",
                "description": "世界文化遗产，杭州的标志性景点。建议游览时间2-3小时，可乘船游湖或环湖步行。",
                "tips": "春季赏花、秋季观月最佳。避开周末和节假日以减少拥挤。",
            },
            {
                "name": "灵隐寺",
                "type": "历史文化",
                "description": "江南著名古刹，始建于东晋。飞来峰石刻造像是珍贵文物。",
                "tips": "需要购买飞来峰门票后才能进入。建议早上前往，人少清净。",
            },
            {
                "name": "雷峰塔",
                "type": "历史文化",
                "description": "因白蛇传而闻名，登塔可俯瞰西湖全景。",
                "tips": "傍晚时分登塔观赏日落最佳。",
            },
            {
                "name": "西溪湿地",
                "type": "自然风光",
                "description": "城市湿地公园，电影《非诚勿扰》取景地。",
                "tips": "适合慢游，建议预留半天时间。可乘船游览。",
            },
            {
                "name": "宋城",
                "type": "主题乐园",
                "description": "大型主题公园，有《宋城千古情》演出。",
                "tips": "演出需单独购票，建议提前预订。",
            },
        ],
        "travel_notes": [
            {
                "title": "杭州3日游经典路线",
                "content": "杭州3日游建议：Day1 西湖游船+雷峰塔+河坊街；Day2 灵隐寺+龙井村+南宋御街；Day3 西溪湿地或宋城。住宿选在西湖附近或地铁沿线。",
            },
            {
                "title": "杭州美食推荐",
                "content": "必吃：西湖醋鱼、东坡肉、龙井虾仁、叫化童鸡。推荐餐厅：楼外楼（西湖醋鱼）、知味观（小吃）。河坊街适合逛吃但价格偏贵。",
            },
            {
                "title": "杭州交通提示",
                "content": "杭州地铁覆盖主要景区。西湖周边建议步行或骑行，避免打车拥堵。高铁到杭州东站，地铁1号线直达西湖。",
            },
        ],
    },
    "北京": {
        "attractions": [
            {
                "name": "故宫博物院",
                "type": "历史文化",
                "description": "明清两代皇家宫殿，世界文化遗产。",
                "tips": "必须提前网上预约，周一闭馆。建议预留4-6小时游览。",
            },
            {
                "name": "长城（八达岭）",
                "type": "历史文化",
                "description": "世界七大奇迹之一，距市区约70公里。",
                "tips": "建议早出发避开人流。体力不好可选择缆车。",
            },
            {
                "name": "天坛",
                "type": "历史文化",
                "description": "明清皇帝祭天的场所，建筑精美。",
                "tips": "建议游览2小时，可观看晨练的老人。",
            },
            {
                "name": "颐和园",
                "type": "皇家园林",
                "description": "中国现存最大的皇家园林，世界文化遗产。",
                "tips": "面积很大，建议预留半天。春季赏花、秋季观红叶。",
            },
            {
                "name": "南锣鼓巷",
                "type": "休闲",
                "description": "老北京胡同，有很多特色小店和美食。",
                "tips": "适合傍晚逛，但人很多。",
            },
        ],
        "travel_notes": [
            {
                "title": "北京5日游攻略",
                "content": "经典路线：Day1 天安门+故宫+景山；Day2 八达岭长城；Day3 颐和园+圆明园；Day4 天坛+南锣鼓巷；Day5 798艺术区或购物。",
            },
            {
                "title": "北京美食指南",
                "content": "必吃：北京烤鸭（全聚德/便宜坊）、炸酱面、豆汁焦圈、铜锅涮肉。推荐：护国寺小吃、簋街夜市。",
            },
            {
                "title": "北京交通建议",
                "content": "地铁最方便，覆盖所有主要景点。去长城可坐S2线火车或877路公交。避开早晚高峰打车。",
            },
        ],
    },
    "上海": {
        "attractions": [
            {
                "name": "外滩",
                "type": "城市地标",
                "description": "万国建筑博览群，夜景尤为壮观。",
                "tips": "建议傍晚前往，可同时欣赏日落和夜景。",
            },
            {
                "name": "豫园",
                "type": "历史文化",
                "description": "明代私家园林，江南古典园林代表。",
                "tips": "周边城隍庙商圈有很多小吃。",
            },
            {
                "name": "东方明珠",
                "type": "城市地标",
                "description": "上海标志性建筑，可登塔俯瞰城市。",
                "tips": "建议购买观光层门票，透明玻璃栈道很刺激。",
            },
            {
                "name": "田子坊",
                "type": "艺术休闲",
                "description": "创意园区，有很多艺术工作室和小店。",
                "tips": "适合拍照，但价格偏贵。",
            },
            {
                "name": "迪士尼乐园",
                "type": "主题乐园",
                "description": "中国大陆首座迪士尼主题乐园。",
                "tips": "建议工作日前往，周末人很多。提前下载APP查看排队时间。",
            },
        ],
        "travel_notes": [
            {
                "title": "上海3日游推荐",
                "content": "Day1 外滩+南京路+豫园；Day2 迪士尼全天；Day3 田子坊+新天地+陆家嘴。住宿选在地铁沿线。",
            },
            {
                "title": "上海美食攻略",
                "content": "必吃：小笼包、生煎、蟹壳黄、本帮菜。推荐：南翔小笼、绿波廊、老正兴。",
            },
            {
                "title": "上海交通提示",
                "content": "地铁网络发达，推荐购买交通卡。外滩到陆家嘴可坐轮渡（更有体验感）。",
            },
        ],
    },
    "成都": {
        "attractions": [
            {
                "name": "大熊猫基地",
                "type": "动物园",
                "description": "世界著名大熊猫迁地保护基地。",
                "tips": "建议早上前往，熊猫更活跃。提前网上购票。",
            },
            {
                "name": "宽窄巷子",
                "type": "历史文化",
                "description": "清朝古街道，成都慢生活体验地。",
                "tips": "适合喝茶、看川剧变脸。",
            },
            {
                "name": "锦里",
                "type": "历史文化",
                "description": "武侯祠旁的仿古商业街。",
                "tips": "夜景很美，有很多小吃。",
            },
            {
                "name": "青城山",
                "type": "自然风光",
                "description": "道教发源地之一，山清水秀。",
                "tips": "建议预留一天时间，可当天往返。",
            },
            {
                "name": "都江堰",
                "type": "历史文化",
                "description": "古代水利工程，世界文化遗产。",
                "tips": "可与青城山安排在同一天游览。",
            },
        ],
        "travel_notes": [
            {
                "title": "成都3日游攻略",
                "content": "Day1 宽窄巷子+锦里+武侯祠；Day2 大熊猫基地+春熙路；Day3 青城山或都江堰。",
            },
            {
                "title": "成都美食地图",
                "content": "必吃：火锅、串串、担担面、龙抄手。推荐：小龙坎火锅、马路边边串串。",
            },
            {
                "title": "成都旅游贴士",
                "content": "成都生活节奏慢，适合休闲游。大熊猫基地一定要早上去，否则熊猫都在睡觉。",
            },
        ],
    },
    "西安": {
        "attractions": [
            {
                "name": "兵马俑",
                "type": "历史文化",
                "description": "世界第八大奇迹，秦始皇陵兵马俑坑。",
                "tips": "建议请讲解员或租语音导览。预留3-4小时。",
            },
            {
                "name": "大雁塔",
                "type": "历史文化",
                "description": "唐代佛教塔，玄奘译经之地。",
                "tips": "可登塔俯瞰，周边有大唐不夜城。",
            },
            {
                "name": "钟楼",
                "type": "历史文化",
                "description": "西安地标建筑，位于市中心。",
                "tips": "夜景很美，可购买钟楼鼓楼联票。",
            },
            {
                "name": "回民街",
                "type": "美食街",
                "description": "西安著名美食街，有很多清真小吃。",
                "tips": "晚上更热闹，但人很多。",
            },
            {
                "name": "华清宫",
                "type": "历史文化",
                "description": "唐代皇家温泉行宫，杨贵妃沐浴之地。",
                "tips": "可与兵马俑安排在同一天。",
            },
        ],
        "travel_notes": [
            {
                "title": "西安3日游推荐",
                "content": "Day1 兵马俑+华清宫；Day2 市区城墙+钟楼+回民街；Day3 大雁塔+陕西历史博物馆。",
            },
            {
                "title": "西安美食攻略",
                "content": "必吃：肉夹馍、羊肉泡馍、凉皮、biangbiang面。推荐：回民街、永兴坊。",
            },
            {
                "title": "西安旅游建议",
                "content": "景点较分散，建议提前规划路线。兵马俑一定要请讲解，否则看不懂。",
            },
        ],
    },
    "南京": {
        "attractions": [
            {
                "name": "中山陵",
                "type": "历史文化",
                "description": "孙中山先生陵寝，位于紫金山南麓。建筑宏伟，象征三民主义。",
                "tips": "周一闭馆。免费但需提前预约，建议早上去避开人流。",
            },
            {
                "name": "夫子庙",
                "type": "历史文化",
                "description": "中国四大文庙之一，秦淮河畔的标志性建筑群。",
                "tips": "夜景比白天更有韵味，秦淮河夜游体验佳。商业化较重但小吃丰富。",
            },
            {
                "name": "明孝陵",
                "type": "世界文化遗产",
                "description": "明太祖朱元璋陵寝，神道石像生是南京标志性景观。",
                "tips": "石像路秋天极美。神道全程步行约30分钟，建议与中山陵安排同一天。",
            },
            {
                "name": "总统府",
                "type": "近代史",
                "description": "中国近代史遗址博物馆，见证太平天国、民国政府等历史。",
                "tips": "建议请讲解或租语音导览。预留2-3小时游览。",
            },
            {
                "name": "玄武湖",
                "type": "自然风光",
                "description": "中国最大的皇家园林湖泊，免费开放的城市公园。",
                "tips": "适合傍晚散步。可远眺紫金山和明城墙。环湖骑行约1小时。",
            },
        ],
        "travel_notes": [
            {
                "title": "南京3日游攻略",
                "content": "Day1 中山陵+明孝陵+美龄宫；Day2 总统府+南京博物院+1912街区；Day3 夫子庙+秦淮河夜游+老门东。住宿选在新街口或夫子庙附近。",
            },
            {
                "title": "南京美食指南",
                "content": "必吃：鸭血粉丝汤、盐水鸭、牛肉锅贴、小笼包。推荐：回味鸭血粉丝、韩复兴盐水鸭、蒋有记锅贴。夫子庙小吃多但偏贵，老门东更地道。",
            },
            {
                "title": "南京历史贴士",
                "content": "南京博物院免费但需提前3天预约，周一闭馆。明孝陵神道和中山陵步行相连，建议安排半天。城墙骑行从中华门段最美。",
            },
        ],
    },
    "重庆": {
        "attractions": [
            {
                "name": "洪崖洞",
                "type": "城市地标",
                "description": "依山而建的吊脚楼群，被誉为现实版《千与千寻》。11层立体建筑。",
                "tips": "晚上亮灯后（约19:00-23:00）最壮观。从1楼到11楼都是平地出入，立体魔幻。",
            },
            {
                "name": "长江索道",
                "type": "交通体验",
                "description": "横跨长江的空中客运索道，被誉为“万里长江第一条空中走廊”。",
                "tips": "避开早晚高峰。建议傍晚乘坐，可看日落和夜景。单程约4分钟。",
            },
            {
                "name": "磁器口古镇",
                "type": "历史文化",
                "description": "千年古镇，保存完好的明清建筑群，重庆的“小重庆”。",
                "tips": "商业化较重，建议去后街小巷寻找本地特色。陈麻花必尝。可安排2-3小时。",
            },
            {
                "name": "武隆天坑",
                "type": "自然风光",
                "description": "世界自然遗产，《变形金刚4》《满城尽带黄金甲》取景地。",
                "tips": "距市区约3小时车程，建议预留一天。必须跟团或包车前往。",
            },
            {
                "name": "白公馆",
                "type": "红色文化",
                "description": "原四川军阀白驹的香山别墅，后为国民党特务机关监狱，关押过小萝卜头等革命烈士。",
                "tips": "与渣滓洞相距不远，建议一起参观。免费参观，周一闭馆。",
            },
        ],
        "travel_notes": [
            {
                "title": "重庆3日游攻略",
                "content": "Day1 解放碑+洪崖洞+长江索道；Day2 磁器口古镇+白公馆+渣滓洞；Day3 武隆天坑仙女山一日游。住宿选在解放碑或观音桥商圈。",
            },
            {
                "title": "重庆火锅地图",
                "content": "必吃火锅，重庆火锅以牛油锅底为主，九宫格是特色。推荐：珮姐老火锅、周师兄大刀腰片、楠火锅。微辣对外地人已足够辣，建议鸳鸯锅。",
            },
            {
                "title": "重庆交通建议",
                "content": "重庆是山城，导航距离和实际步行距离差异大。轻轨是最佳出行方式，2号线和3号线可观江景。打车容易迷路，建议选轻轨+步行。",
            },
        ],
    },
    "苏州": {
        "attractions": [
            {
                "name": "拙政园",
                "type": "世界文化遗产",
                "description": "中国四大名园之一，苏州园林的代表作。以水为中心，山水萦绕。",
                "tips": "建议游览2小时。旺季（4-5月、9-10月）人多。可租讲解了解造园美学。",
            },
            {
                "name": "虎丘",
                "type": "历史文化",
                "description": "吴中第一名胜，苏东坡云'到苏州不游虎丘，乃憾事也'。虎丘塔是中国第一斜塔。",
                "tips": "建议游览1.5小时。春季虎丘花会值得一看。云岩寺塔不可登塔。",
            },
            {
                "name": "平江路",
                "type": "历史街区",
                "description": "苏州保存最完整的古街区，河街相邻、水陆并行。",
                "tips": "早上人少，适合拍照。沿河茶馆可品茶听评弹。商业化程度适中。",
            },
            {
                "name": "周庄古镇",
                "type": "水乡古镇",
                "description": "中国第一水乡，双桥、沈厅、张厅是标志性景点。",
                "tips": "距苏州市区约1小时车程。建议傍晚去，游客少且夜景美。万三蹄是特色美食。",
            },
            {
                "name": "苏州博物馆",
                "type": "文化场馆",
                "description": "贝聿铭晚期代表作，现代建筑与苏州园林美学的完美结合。",
                "tips": "免费但需提前预约，周一闭馆。建筑本身比展品更值得看。紧邻拙政园可一起游览。",
            },
        ],
        "travel_notes": [
            {
                "title": "苏州3日游攻略",
                "content": "Day1 拙政园+苏州博物馆+平江路；Day2 虎丘+寒山寺+山塘街；Day3 周庄古镇或同里古镇一日游。住宿选在观前街或平江路附近。",
            },
            {
                "title": "苏州美食推荐",
                "content": "必吃：苏式汤面、松鼠桂鱼、蟹粉小笼、阳澄湖大闸蟹（秋季）。推荐：同得兴精品面馆、松鹤楼。偏甜口味，不甜不正宗。",
            },
            {
                "title": "苏州园林游览建议",
                "content": "苏州园林各有特色：拙政园宏大、留园精致、狮子林假山群、沧野趣。建议选1-2个精听讲解，比走马观花效果好得多。坐船游古城河是独特体验。",
            },
        ],
    },
}


class SeedDataService:
    """Service to populate RAG with seed data for popular destinations"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._seeded = False

    async def seed_if_empty(self) -> None:
        """Seed data if Qdrant collections are empty"""
        if self._seeded:
            return

        try:
            from app.services.rag import TravelRagService

            rag = TravelRagService(self.settings)

            # Check if data exists by trying to scroll
            try:
                from qdrant_client import QdrantClient
                client = QdrantClient(url=self.settings.qdrant_url, api_key=self.settings.qdrant_api_key)
                result = client.scroll(
                    collection_name="travel_notes",
                    limit=1,
                    with_payload=False,
                    with_vectors=False
                )
                if result[0]:  # Has points
                    logger.info("RAG already contains data, skipping seed")
                    self._seeded = True
                    client.close()
                    return
                client.close()
            except Exception:
                pass  # Collection might not exist yet

            await self._seed_data(rag)
            self._seeded = True

        except Exception as exc:
            logger.warning(f"Failed to seed RAG data: {exc}")

    async def _seed_data(self, rag: Any) -> None:
        """Seed all destination data — 修复：使用标准 ingest API（双写 dense+sparse）。

        旧代码直接调用 rag.qdrant.upsert / rag.embedder.embed_query，但这些属性在
        TravelRagService 上不存在（qdrant 是私有 client，embed 是实例方法非 embedder）。
        现改为通过 ingest_notes / ingest_attractions 标准接口导入，自动走预处理管线
        （Markdown 清洗 + 分块 + 实体抽取）和双索引同步写入。
        """
        total_attractions = 0
        total_notes = 0

        for destination, data in DESTINATION_SEED_DATA.items():
            # Seed attractions: 聚合为一个文档批量导入
            attraction_docs: list[RagDocument] = []
            for attraction in data.get("attractions", []):
                text = (
                    f"《{attraction['name']}》是{destination}的{attraction['type']}类景点。"
                    f"{attraction['description']}\n\n"
                    f"游玩贴士：{attraction['tips']}\n\n"
                    f"建议游玩时长：2-3小时。门票信息请关注官方公告。"
                )
                attraction_docs.append(RagDocument(
                    id=f"seed_attraction_{destination}_{attraction['name']}",
                    title=attraction["name"],
                    text=text,
                    city=destination,
                    source="seed_data",
                    tags=["attraction", attraction["type"], destination],
                ))

            if attraction_docs:
                try:
                    # 每个景点单独导入（保持 doc_key 独立）
                    for doc in attraction_docs:
                        resp = await rag.ingest_attractions(destination, [doc])
                        if resp.inserted > 0:
                            total_attractions += 1
                except Exception as exc:
                    logger.warning(f"Failed to seed attractions for {destination}: {exc}")

            # Seed travel notes: 聚合导入
            note_docs: list[RagDocument] = []
            for note in data.get("travel_notes", []):
                note_docs.append(RagDocument(
                    id=f"seed_note_{destination}_{note['title']}",
                    title=note["title"],
                    text=f"{note['title']}\n\n{note['content']}",
                    city=destination,
                    source="seed_data",
                    tags=["travel_note", destination],
                ))

            if note_docs:
                try:
                    for doc in note_docs:
                        resp = await rag.ingest_notes(destination, [doc])
                        if resp.inserted > 0:
                            total_notes += 1
                except Exception as exc:
                    logger.warning(f"Failed to seed notes for {destination}: {exc}")

        logger.info(f"Seeded {total_attractions} attractions and {total_notes} travel notes (dual-write to Qdrant + rag_chunks)")


async def seed_rag_data(settings: Settings) -> None:
    """Convenience function to seed RAG data"""
    service = SeedDataService(settings)
    await service.seed_if_empty()
