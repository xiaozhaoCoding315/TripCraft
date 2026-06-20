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
        """Seed all destination data"""
        total_attractions = 0
        total_notes = 0

        for destination, data in DESTINATION_SEED_DATA.items():
            # Seed attractions
            for attraction in data.get("attractions", []):
                try:
                    doc = {
                        "text": f"{attraction['name']} - {attraction['type']}\n{attraction['description']}\n\n贴士：{attraction['tips']}",
                        "destination": destination,
                        "type": "attraction",
                        "name": attraction["name"],
                    }
                    rag.qdrant.upsert(
                        collection_name="travel_notes",
                        points=[{
                            "id": hash(f"{destination}_{attraction['name']}"),
                            "vector": rag.embedder.embed_query(doc["text"]),
                            "payload": doc,
                        }],
                    )
                    total_attractions += 1
                except Exception as exc:
                    logger.debug(f"Failed to seed attraction {attraction['name']}: {exc}")

            # Seed travel notes
            for note in data.get("travel_notes", []):
                try:
                    doc = {
                        "text": f"{note['title']}\n\n{note['content']}",
                        "destination": destination,
                        "type": "travel_note",
                        "title": note["title"],
                    }
                    rag.qdrant.upsert(
                        collection_name="travel_notes",
                        points=[{
                            "id": hash(f"{destination}_{note['title']}"),
                            "vector": rag.embedder.embed_query(doc["text"]),
                            "payload": doc,
                        }],
                    )
                    total_notes += 1
                except Exception as exc:
                    logger.debug(f"Failed to seed note {note['title']}: {exc}")

        logger.info(f"Seeded {total_attractions} attractions and {total_notes} travel notes")


async def seed_rag_data(settings: Settings) -> None:
    """Convenience function to seed RAG data"""
    service = SeedDataService(settings)
    await service.seed_if_empty()
