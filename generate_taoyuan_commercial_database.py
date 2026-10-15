# -*- coding: utf-8 -*-
"""
桃園市商辦大樓與核心企業資料庫生成器 (Commercial Office & Corporate Database)
專為「辦公室設備與弱電系統規劃廠商」量身打造
納入：
1. 核心商辦企業 (資訊科技、金融證券、專業事務所、設計工程、企管行銷、國貿代理、建設開發、製造業市區總部)
2. 第三組 4 大邊界高弱電客群：
   - A. 商務中心 / 共享辦公 (Co-working Space)
   - B. 牙醫醫美診所 / 專科體系 (Dental & Aesthetic Clinics)
   - C. 連鎖餐飲零售之「營運總部 / 辦公室」(Corporate HQs)
   - D. 物流倉儲·海空運承攬總部 (Logistics & Freight HQs)
排除：臨街小吃飲料店、美髮理容美甲、傳統雜貨零售、汽機車修護、自助洗衣、娃娃機娛樂等。
"""

import json
import random

# Fixed seed for deterministic realistic generation
random.seed(42)

DISTRICTS = {
    "taoyuan": {
        "id": "taoyuan",
        "name": "桃園區",
        "icon": "🏛️",
        "desc": "中正藝文特區頂級商辦群 · 經國水岸商務特區 · 站前金融大道",
        "center": [24.9985, 121.3060],
        "zoom": 15,
        "zones": ["藝文特區商辦", "經國特區商辦", "站前金融街", "大興西路商貿帶"],
        "buildings": [
            {"name": "中悅世界中心", "road": "同德五街", "address": "同德五街77號", "lat": 25.0162, "lng": 121.3015, "floors": 32, "count": 48},
            {"name": "中悅一品企業大樓", "road": "同德六街", "address": "同德六街89號", "lat": 25.0175, "lng": 121.3008, "floors": 28, "count": 36},
            {"name": "昭揚乾坤科技大樓", "road": "藝文一街", "address": "藝文一街86號", "lat": 25.0150, "lng": 121.3028, "floors": 20, "count": 32},
            {"name": "昭揚銳商務總部", "road": "同德五街", "address": "同德五街68號", "lat": 25.0158, "lng": 121.3020, "floors": 18, "count": 28},
            {"name": "富邦人壽桃園金融大樓", "road": "中正路", "address": "中正路1088號", "lat": 25.0135, "lng": 121.3045, "floors": 22, "count": 35},
            {"name": "經國雙星商務大樓", "road": "經國路", "address": "經國路433號", "lat": 25.0285, "lng": 121.3120, "floors": 16, "count": 26},
            {"name": "昭揚飛企業大樓", "road": "經國一路", "address": "經國一路18號", "lat": 25.0310, "lng": 121.3135, "floors": 15, "count": 24},
            {"name": "國泰人壽桃園大樓", "road": "復興路", "address": "復興路186號", "lat": 24.9912, "lng": 121.3140, "floors": 16, "count": 30},
            {"name": "遠東國際金融大樓", "road": "中華路", "address": "中華路10號", "lat": 24.9902, "lng": 121.3125, "floors": 14, "count": 25},
            {"name": "新光人壽桃園站前大樓", "road": "復興路", "address": "復興路99號", "lat": 24.9898, "lng": 121.3150, "floors": 15, "count": 26},
            {"name": "藝文金融天下大樓", "road": "大興西路二段", "address": "大興西路二段6號", "lat": 25.0105, "lng": 121.3012, "floors": 18, "count": 28},
            {"name": "中正商業大樓", "road": "中正路", "address": "中正路886號", "lat": 25.0080, "lng": 121.3070, "floors": 14, "count": 22}
        ]
    },
    "zhongli": {
        "id": "zhongli",
        "name": "中壢區",
        "icon": "🚄",
        "desc": "高鐵青埔特區科技總部 · 海華SOGO金融商圈 · 站前商貿核心",
        "center": [24.9830, 121.2180],
        "zoom": 15,
        "zones": ["青埔高鐵商辦", "海華金融特區", "中壢站前商圈", "環北科技大道"],
        "buildings": [
            {"name": "國泰置地廣場·青埔", "road": "高鐵北路一段", "address": "高鐵北路一段31號", "lat": 25.0130, "lng": 121.2155, "floors": 20, "count": 42},
            {"name": "青埔金融雙星大樓", "road": "領航南路三段", "address": "領航南路三段88號", "lat": 25.0090, "lng": 121.2130, "floors": 18, "count": 32},
            {"name": "置地國際商貿中心", "road": "青埔路二段", "address": "青埔路二段168號", "lat": 25.0145, "lng": 121.2175, "floors": 16, "count": 28},
            {"name": "海華國際星鑽金融大樓", "road": "環北路", "address": "環北路400號", "lat": 24.9665, "lng": 121.2225, "floors": 24, "count": 45},
            {"name": "海華世紀宮廷商務大樓", "road": "環北路", "address": "環北路398號", "lat": 24.9658, "lng": 121.2218, "floors": 21, "count": 36},
            {"name": "永豐銀行中壢商業大樓", "road": "延平路", "address": "延平路500號", "lat": 24.9575, "lng": 121.2248, "floors": 15, "count": 26},
            {"name": "元大證券中壢金融大樓", "road": "中山路", "address": "中山路118號", "lat": 24.9558, "lng": 121.2260, "floors": 14, "count": 24},
            {"name": "中壢第一商業大樓", "road": "中央東路", "address": "中央東路88號", "lat": 24.9565, "lng": 121.2285, "floors": 12, "count": 20},
            {"name": "領航亞太商務總部", "road": "高鐵南路二段", "address": "高鐵南路二段180號", "lat": 25.0055, "lng": 121.2110, "floors": 15, "count": 25}
        ]
    },
    "guishan": {
        "id": "guishan",
        "name": "龜山區",
        "icon": "🏥",
        "desc": "林口長庚A8商務圈 · 文化二路醫療生技與跨國科技總部",
        "center": [25.0610, 121.3650],
        "zoom": 15,
        "zones": ["長庚A8商務圈", "文化二路商貿帶", "復興一路商圈", "華亞科技園外商辦"],
        "buildings": [
            {"name": "華亞科技商務大樓", "road": "文化二路", "address": "文化二路188號", "lat": 25.0585, "lng": 121.3680, "floors": 18, "count": 34},
            {"name": "長庚國際醫療商務中心", "road": "復興一路", "address": "復興一路12號", "lat": 25.0618, "lng": 121.3662, "floors": 16, "count": 30},
            {"name": "文化科技雙星大樓", "road": "文化二路", "address": "文化二路88號", "lat": 25.0645, "lng": 121.3645, "floors": 15, "count": 26},
            {"name": "復興金融商辦大樓", "road": "復興一路", "address": "復興一路80號", "lat": 25.0602, "lng": 121.3685, "floors": 14, "count": 22},
            {"name": "長庚文化企業大樓", "road": "文化三路", "address": "文化三路36號", "lat": 25.0630, "lng": 121.3710, "floors": 12, "count": 20}
        ]
    },
    "luzhu": {
        "id": "luzhu",
        "name": "蘆竹區",
        "icon": "✈️",
        "desc": "南崁國際航運總部廊道 · 長榮企業大樓 · 新南路商務核心",
        "center": [25.0460, 121.2940],
        "zoom": 15,
        "zones": ["南崁新南路商辦", "長榮企業總部周邊", "中正路金融街", "台茂商務特區"],
        "buildings": [
            {"name": "長榮海運航空總部大樓", "road": "新南路一段", "address": "新南路一段163號", "lat": 25.0475, "lng": 121.2930, "floors": 24, "count": 46},
            {"name": "台茂南崁企業雙星", "road": "南崁路一段", "address": "南崁路一段112號", "lat": 25.0535, "lng": 121.2890, "floors": 16, "count": 28},
            {"name": "南崁金融天下大樓", "road": "中正路", "address": "中正路109號", "lat": 25.0435, "lng": 121.2965, "floors": 15, "count": 25},
            {"name": "新南航運商務大樓", "road": "新南路一段", "address": "新南路一段99號", "lat": 25.0450, "lng": 121.2945, "floors": 14, "count": 22},
            {"name": "南崁國際貿易大樓", "road": "南崁路一段", "address": "南崁路一段66號", "lat": 25.0510, "lng": 121.2915, "floors": 12, "count": 20}
        ]
    },
    "dayuan": {
        "id": "dayuan",
        "name": "大園區",
        "icon": "🌐",
        "desc": "航空城自貿港商貿特區 · 國際跨境物流承攬與空運報關企業總部",
        "center": [25.0680, 121.2450],
        "zoom": 14,
        "zones": ["航空自貿港區商辦", "大園國際商務特區", "航翔物流總部廊道"],
        "buildings": [
            {"name": "遠雄航空自由貿易港區商務大樓", "road": "航翔路", "address": "航翔路101號", "lat": 25.0740, "lng": 121.2480, "floors": 18, "count": 38},
            {"name": "航翔自貿科技商務中心", "road": "航翔路", "address": "航翔路88號", "lat": 25.0725, "lng": 121.2460, "floors": 15, "count": 28},
            {"name": "航空城國貿企業大樓", "road": "大成路", "address": "大成路一段50號", "lat": 25.0635, "lng": 121.2015, "floors": 12, "count": 22}
        ]
    }
}

# 產業分類配置（專門針對弱電/辦公室設備）
CATEGORIES = [
    {
        "id": "IT_SOFTWARE",
        "name": "資訊科技 / 軟體雲端",
        "icon": "💻",
        "badge_color": "#2563EB",
        "tags": ["系統整合", "雲端SaaS", "AI大數據", "資安監控", "網通設備"],
        "weak_points": [
            "需全新建置 Cat6A 機房網路線與伺服器機櫃",
            "會議室需 75 吋智慧觸控大屏與視訊連線系統",
            "機密研發辦公室需臉部識別自動門禁與考勤連動",
            "全辦公室高密度 WiFi 6 AP 覆蓋與防火牆升級"
        ]
    },
    {
        "id": "FINANCE",
        "name": "金融金控 / 證券投顧",
        "icon": "💰",
        "badge_color": "#059669",
        "tags": ["銀行分行", "證券投顧", "資產管理", "產壽險部"],
        "weak_points": [
            "營業大廳需 4K 監控系統與法規要求 180 天錄影儲存",
            "理財顧問電話需全面更換 IP-PBX 數位錄音電話總機",
            "金庫與重要檔案庫房三道式生物辨識門禁",
            "不斷電系統 (UPS) 與不斷訊網路備援工程"
        ]
    },
    {
        "id": "COWORKING",
        "name": "商務中心 / 共享辦公 ⭐",
        "icon": "🏢",
        "is_border_group": True,
        "badge_color": "#D97706",
        "tags": ["共享空間", "新創基地", "商務中心", "會議租賃"],
        "weak_points": [
            "全區 40 間獨立辦公室獨立電子鎖門禁系統",
            "公共會議室智慧預約電子紙顯示屏與視訊設備",
            "全場高速獨立 VLAN 切網，防範租戶相互干擾",
            "出入口人臉測溫考勤、訪客 QR Code 門禁"
        ]
    },
    {
        "id": "CLINIC",
        "name": "牙醫醫美診所 / 專科體系 ⭐",
        "icon": "🏥",
        "is_border_group": True,
        "badge_color": "#DC2626",
        "tags": ["植牙中心", "醫美旗艦", "眼科專科", "健檢中心"],
        "weak_points": [
            "診間與手術室隱私隔離門禁與對講系統",
            "高畫質診療櫃台叫號分機與智慧排隊大屏",
            "高解析度監控攝影機防止醫療爭議死角",
            "電子病歷專用高速內網與資料加密儲存伺服器"
        ]
    },
    {
        "id": "FNB_HQ",
        "name": "連鎖餐飲零售·營運總部 ⭐",
        "icon": "🍔",
        "is_border_group": True,
        "badge_color": "#EA580C",
        "tags": ["企業控股", "餐飲總部", "連鎖管理", "採購中心"],
        "weak_points": [
            "全台 80 家分店中央視訊會議與即時監控聯網",
            "總部辦公室電話分機總機與客服錄音系統",
            "展示廚房及會議中心投影音響廣播工程",
            "資訊中心伺服器機房弱電工程建置"
        ]
    },
    {
        "id": "LOGISTICS_HQ",
        "name": "物流倉儲·海空運承攬總部 ⭐",
        "icon": "📦",
        "is_border_group": True,
        "badge_color": "#0891B2",
        "tags": ["航空貨運", "報關承攬", "跨境電商", "海運承攬"],
        "weak_points": [
            "24 小時出勤指紋/刷卡考勤機與外勤差勤系統",
            "物流總部大螢幕即時貨況戰情電視牆",
            "進出口單據高印量彩色影印機 OA 租賃",
            "多方通話總機交換機與大量客服電話分機"
        ]
    },
    {
        "id": "LAW_ACCOUNTING",
        "name": "專業事務所 (會計/律師/專利)",
        "icon": "⚖️",
        "badge_color": "#4F46E5",
        "tags": ["聯合會計師", "律師事務所", "專利商標", "代書地政士"],
        "weak_points": [
            "合夥人辦公室專用門禁鎖與機密卷宗庫防盜監控",
            "長約高階彩色複合機租賃 (低單張列印成本方案)",
            "保密電話通話錄音與分機總機升級",
            "內部加密 NAS 儲存與異地備份網路架設"
        ]
    },
    {
        "id": "DESIGN_ENG",
        "name": "建築室內設計 / 工程技師",
        "icon": "🎨",
        "badge_color": "#7C3AED",
        "tags": ["室內裝修", "建築師事務所", "結構技師", "景觀設計"],
        "weak_points": [
            "大圖出圖機與工程圖高速彩色掃描設備",
            "繪圖工作站 10Gbps 高速內部區域網路",
            "業主提案大型 4K 觸控簡報螢幕與視訊鏡頭",
            "樣品展示間感應門禁與柔光監視器"
        ]
    },
    {
        "id": "CONSULTING",
        "name": "企管人資 / 廣告行銷傳播",
        "icon": "📈",
        "badge_color": "#9333EA",
        "tags": ["管理顧問", "獵頭人資", "數位傳播", "公關行銷"],
        "weak_points": [
            "開放式辦公空間全區無死角高速 WiFi 6",
            "視訊會議多方收音麥克風與追蹤鏡頭",
            "雲端差勤打卡系統與多功能事務機",
            "新辦公室搬遷網路佈線與理線工程"
        ]
    },
    {
        "id": "TRADING",
        "name": "國際貿易 / 跨國代理進出口",
        "icon": "🚢",
        "badge_color": "#0D9488",
        "tags": ["進出口貿易", "原廠代理", "外銷總部", "經銷商總部"],
        "weak_points": [
            "跨國視訊專線機房與防火牆設定",
            "展示間音響設備、投影機與環境控制",
            "各部門分機對外國際電話費節費系統 (VoIP)",
            "出入口高階防偽刷卡門禁"
        ]
    },
    {
        "id": "CONSTRUCTION",
        "name": "建設開發 / 不動產代銷總部",
        "icon": "🏗️",
        "badge_color": "#B45309",
        "tags": ["知名建商", "代銷集團", "土地開發", "資產管理"],
        "weak_points": [
            "企業總部接待大廳豪華迎賓大屏與環繞音響",
            "高階主管樓層指靜脈/臉部辨識最高安全門禁",
            "案場工務遠端即時監控中心與網路連線",
            "全棟智慧辦公室自動化控制系統"
        ]
    },
    {
        "id": "CORP_HQ",
        "name": "製造業·市區營運業務總部",
        "icon": "🏭",
        "badge_color": "#334155",
        "tags": ["上市櫃科技", "業務總部", "採購中心", "財務總處"],
        "weak_points": [
            "市區總部與中南部廠區內部專線網路串接 (SD-WAN)",
            "大型跨廠區視訊會議室智慧整合環控",
            "企業總部伺服器機房冷卻與電力監控系統",
            "總機自動語音應答與客服分機調度"
        ]
    }
]

# 企業名稱辭庫
PREFIXES = [
    "台灣", "亞太", "國際", "全球", "宏", "達", "華", "富", "新", "聯", "國", "鼎", "信", "盛",
    "創", "智", "科", "誠", "通", "順", "興", "裕", "豐", "展", "瑞", "捷", "博", "邁", "冠", "晉"
]
CORE_NAMES = [
    "智能", "數位", "雲端", "資訊", "光電", "生醫", "創新", "通訊", "能源", "精密",
    "資產", "投顧", "聯合", "工程", "實業", "國際", "航運", "物流", "生技", "建築",
    "行銷", "國際貿易", "置業", "企業管理", "科技", "精密機械", "數位行銷", "系統科技"
]
SUFFIXES = ["股份有限公司", "有限公司", "集團總部", "台灣分公司", "企業有限公司"]

CONTACT_SURNAMES = ["陳", "林", "黃", "張", "李", "王", "吳", "劉", "蔡", "楊", "許", "鄭", "謝", "郭", "洪"]
CONTACT_TITLES = ["總務經理", "行政主任", "IT資訊長", "採購副理", "專案經理", "管理部主管", "副總經理", "執行秘書"]

CAPITAL_TIERS = [
    {"tier": "TIER_100M", "label": "👑 1億以上", "min": 100000000, "max": 800000000, "prob": 0.22},
    {"tier": "TIER_30M", "label": "💎 3,000萬~1億", "min": 30000000, "max": 99000000, "prob": 0.35},
    {"tier": "TIER_5M", "label": "🏢 500萬~3,000萬", "min": 5000000, "max": 29000000, "prob": 0.33},
    {"tier": "TIER_UNDER_5M", "label": "🌱 500萬以下", "min": 1000000, "max": 4900000, "prob": 0.10}
]

STATUS_CHOICES = ["尚未拜訪", "尚未拜訪", "尚未拜訪", "洽談中", "已拜訪"]

def generate_taoyuan_data():
    all_companies = []
    building_summary = []
    
    comp_id_seq = 10001
    
    for dist_id, dist_info in DISTRICTS.items():
        for b_idx, b in enumerate(dist_info["buildings"]):
            building_companies = []
            building_id = f"bld_{dist_id}_{b_idx+1}"
            
            # Floor assignment for companies in this building
            floors_count = b["floors"]
            assigned_count = b["count"]
            
            for c_idx in range(assigned_count):
                comp_id_seq += 1
                
                # Category selection
                cat = random.choice(CATEGORIES)
                
                # Capital Tier selection
                r_val = random.random()
                cum = 0
                chosen_tier_cfg = CAPITAL_TIERS[1]
                for tc in CAPITAL_TIERS:
                    cum += tc["prob"]
                    if r_val <= cum:
                        chosen_tier_cfg = tc
                        break
                
                capital_num = random.randint(chosen_tier_cfg["min"] // 1000000, chosen_tier_cfg["max"] // 1000000) * 1000000
                if capital_num >= 100000000:
                    capital_str = f"NT$ {capital_num // 100000000}億{(capital_num % 100000000)//10000000}千萬" if (capital_num % 100000000) else f"NT$ {capital_num // 100000000}億元"
                else:
                    capital_str = f"NT$ {capital_num // 10000}萬元"
                
                # Floor assignment
                fl_num = (c_idx % (floors_count - 1)) + 2  # 2F to top floor
                room_suffix = f"-{random.randint(1, 4)}" if random.random() > 0.5 else ""
                floor_str = f"{fl_num}F{room_suffix}"
                
                # Company Name Generation
                p1 = random.choice(PREFIXES)
                p2 = random.choice(PREFIXES)
                c_core = random.choice(CORE_NAMES)
                suf = random.choice(SUFFIXES)
                
                # Specialized name if border group
                if cat["id"] == "COWORKING":
                    name = f"{random.choice(['大瀚', '雷格斯', '寰宇', '悅思', '頂好', '極客', '創客'])}{b['name'].replace('大樓', '')}商務中心"
                elif cat["id"] == "CLINIC":
                    name = f"{random.choice(['君綺', '雅丰', '新光', '維格', '米蘭', '安美', '耀美', '品適'])}{random.choice(['美學牙醫旗艦中心', '醫美聯合專科', '國際精準醫療診所', '微創專科診所'])}"
                elif cat["id"] == "FNB_HQ":
                    name = f"{random.choice(['饗賓', '王品', '瓦城', '乾杯', '鼎王', '豆府', '三商', '路易莎'])}{random.choice(['餐飲實業總部', '企業控股股份有限公司', '國際餐飲事業管理處'])}"
                elif cat["id"] == "LOGISTICS_HQ":
                    name = f"{random.choice(['長榮', '萬海', '陽明', '中菲行', '台驊', '順豐', '日通', '建榮'])}{random.choice(['海空運承攬總部', '國際物流供應鏈總處', '通運報關事業部'])}"
                else:
                    name = f"{p1}{p2}{c_core}{suf}"
                
                # Slight lat/lng jitter so markers don't overlap 100% on high zoom, but still stay around building
                lat_jitter = (random.random() - 0.5) * 0.0003
                lng_jitter = (random.random() - 0.5) * 0.0003
                
                # Contact info
                contact = f"{random.choice(CONTACT_SURNAMES)}{random.choice(CONTACT_TITLES)}"
                phone_tail = f"{random.randint(100, 999)} 分機 {random.randint(101, 899)}"
                phone = f"03-{random.randint(311, 399)}-{phone_tail}"
                
                # Listed status
                is_listed = "是" if (chosen_tier_cfg["tier"] == "TIER_100M and random.random() < 0.65") or (chosen_tier_cfg["tier"] == "TIER_30M" and random.random() < 0.25) else "否"
                
                # Status & Logs
                status = random.choice(STATUS_CHOICES)
                notes = random.choice(cat["weak_points"])
                
                logs = []
                if status == "已拜訪":
                    logs.append({
                        "id": f"log_{comp_id_seq}_1",
                        "date": "2026-10-12 14:30",
                        "contact": contact,
                        "outcome": "已提報價單 · 議價審核",
                        "summary": f"初訪洽談順利。{notes}。預計本月底召開總務與IT主管採購會議。",
                        "next_action": "下週二提供 Cat6A 與門禁考勤整合系統詳細報價單"
                    })
                elif status == "洽談中":
                    logs.append({
                        "id": f"log_{comp_id_seq}_1",
                        "date": "2026-10-14 10:15",
                        "contact": contact,
                        "outcome": "樣品測試中 · 送件評估",
                        "summary": "客戶對視訊大屏與人臉辨識門禁機非常感興趣，已送測試機借測兩週。",
                        "next_action": "10/24 到現場回收測試機並討論簽約細節"
                    })
                
                comp_data = {
                    "id": comp_id_seq,
                    "district_id": dist_id,
                    "district_name": dist_info["name"],
                    "building_id": building_id,
                    "building_name": b["name"],
                    "floor": floor_str,
                    "floor_num": fl_num,
                    "name": name,
                    "road": b["road"],
                    "address": f"桃園市{dist_info['name']}{b['address']} {floor_str}",
                    "lat": round(b["lat"] + lat_jitter, 6),
                    "lng": round(b["lng"] + lng_jitter, 6),
                    "bld_lat": b["lat"],
                    "bld_lng": b["lng"],
                    "category_id": cat["id"],
                    "category_name": cat["name"],
                    "category_icon": cat["icon"],
                    "category_color": cat["badge_color"],
                    "is_border_group": cat.get("is_border_group", False),
                    "capital": capital_num,
                    "capital_str": capital_str,
                    "capital_tier": chosen_tier_cfg["tier"],
                    "capital_tier_label": chosen_tier_cfg["label"],
                    "is_listed": is_listed,
                    "status": status,
                    "contact": contact,
                    "phone": phone,
                    "notes": notes,
                    "visit_logs": logs
                }
                
                building_companies.append(comp_data)
                all_companies.append(comp_data)
            
            # Sort building companies by floor descending (top floor first, just like real building directory)
            building_companies.sort(key=lambda x: x["floor_num"], reverse=True)
            
            building_summary.append({
                "building_id": building_id,
                "district_id": dist_id,
                "name": b["name"],
                "road": b["road"],
                "address": f"桃園市{dist_info['name']}{b['address']}",
                "lat": b["lat"],
                "lng": b["lng"],
                "floors": b["floors"],
                "company_count": len(building_companies),
                "companies": [c["id"] for c in building_companies]
            })

    # Root payload
    database_payload = {
        "metadata": {
            "title": "全國商辦與企業地圖 · 桃園旗艦示範區",
            "version": "v1.0",
            "focus": "辦公室設備與弱電系統規劃 (門禁考勤 / 監視網路 / 機房PBX / 視訊會議 / OA)",
            "total_companies": len(all_companies),
            "total_buildings": len(building_summary),
            "districts_count": len(DISTRICTS)
        },
        "districts": DISTRICTS,
        "categories": CATEGORIES,
        "capital_tiers": CAPITAL_TIERS,
        "buildings": building_summary,
        "companies": all_companies
    }
    
    with open("commercial_database_taoyuan.json", "w", encoding="utf-8") as f:
        json.dump(database_payload, f, ensure_ascii=False, indent=2)
        
    print(f"[OK] 成功生成 commercial_database_taoyuan.json！")
    print(f"     收錄商辦企業：{len(all_companies):,} 家")
    print(f"     指標商辦大樓：{len(building_summary):,} 棟")
    print(f"     涵蓋精華行政區：{len(DISTRICTS)} 區")

if __name__ == "__main__":
    generate_taoyuan_data()
