# -*- coding: utf-8 -*-
"""
全台商辦＆企業地圖 · 全國22縣市商業大樓與辦公室資料庫生成器
完整涵蓋全台22個縣市（北中南東離島無一遺漏）：
臺北、新北、基隆、桃園、新竹市、新竹縣、苗栗、臺中、彰化、南投、雲林、
嘉義市、嘉義縣、臺南、高雄、屏東、宜蘭、花蓮、臺東、澎湖、金門、連江(馬祖)。
排除沿街小吃、飲料店、美容美髮等零售。
鎖定：IT資訊軟體、金融保險、建築工程事務所、跨國貿易、專業諮詢會計法律、
以及四大高價值邊界金礦（商務中心、牙醫醫美診所、連鎖餐飲營運總部、海空運物流總部）。
"""

import json
import random
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

random.seed(42)

COUNTIES = {
    # --- 北部區域 ---
    "taipei": {
        "id": "taipei", "name": "臺北市", "icon": "🏛️", "region": "北部",
        "center": [25.0339, 121.5645], "zoom": 14,
        "districts": [
            {"id": "tp_xinyi", "name": "信義計畫區", "icon": "👑", "center": [25.0350, 121.5670], "zoom": 16},
            {"id": "tp_dunhua", "name": "敦南敦北金融特區", "icon": "🏦", "center": [25.0530, 121.5490], "zoom": 16},
            {"id": "tp_neihu", "name": "內湖科技商辦聚落", "icon": "💻", "center": [25.0780, 121.5740], "zoom": 15},
            {"id": "tp_nangang", "name": "南港軟體經貿特區", "icon": "🚀", "center": [25.0590, 121.6150], "zoom": 16},
            {"id": "tp_zhongshan", "name": "南京松江商貿特區", "icon": "💼", "center": [25.0515, 121.5330], "zoom": 16}
        ]
    },
    "new_taipei": {
        "id": "new_taipei", "name": "新北市", "icon": "🏙️", "region": "北部",
        "center": [25.0125, 121.4650], "zoom": 13,
        "districts": [
            {"id": "nt_banqiao", "name": "新板特區經貿核心", "icon": "🌟", "center": [25.0130, 121.4640], "zoom": 16},
            {"id": "nt_xinzhuang", "name": "新莊副都心CBD", "icon": "🏢", "center": [25.0580, 121.4500], "zoom": 16},
            {"id": "nt_zhonghe", "name": "中和遠東世紀園區", "icon": "🏭", "center": [24.9980, 121.4880], "zoom": 16},
            {"id": "nt_xindian", "name": "新店矽谷科技商辦", "icon": "💡", "center": [24.9850, 121.5380], "zoom": 16},
            {"id": "nt_xizhi", "name": "汐止經貿U-TOWN", "icon": "🚅", "center": [25.0600, 121.6500], "zoom": 16}
        ]
    },
    "keelung": {
        "id": "keelung", "name": "基隆市", "icon": "⚓", "region": "北部",
        "center": [25.1285, 121.7410], "zoom": 15,
        "districts": [
            {"id": "kl_port", "name": "基隆港務商貿特區", "icon": "🚢", "center": [25.1310, 121.7400], "zoom": 16},
            {"id": "kl_xinyi", "name": "義一路金融商圈", "icon": "🏦", "center": [25.1325, 121.7450], "zoom": 16}
        ]
    },
    "taoyuan": {
        "id": "taoyuan", "name": "桃園市", "icon": "✈️", "region": "北部",
        "center": [24.9936, 121.3010], "zoom": 13,
        "districts": [
            {"id": "ty_art", "name": "藝文/經國CBD", "icon": "👑", "center": [25.0165, 121.3005], "zoom": 16},
            {"id": "ty_station", "name": "桃園站前金融商圈", "icon": "🏦", "center": [24.9892, 121.3135], "zoom": 16},
            {"id": "ty_qingpu", "name": "青埔高鐵經貿特區", "icon": "🚅", "center": [25.0125, 121.2150], "zoom": 16},
            {"id": "ty_guishan", "name": "龜山長庚A8生醫商辦", "icon": "🩺", "center": [25.0595, 121.3685], "zoom": 16},
            {"id": "ty_luzhu", "name": "南崁航運物流CBD", "icon": "🚢", "center": [25.0450, 121.2940], "zoom": 16}
        ]
    },
    "hsinchu_city": {
        "id": "hsinchu_city", "name": "新竹市", "icon": "🔬", "region": "北部",
        "center": [24.8040, 120.9720], "zoom": 14,
        "districts": [
            {"id": "hcc_guangfu", "name": "光復科技金融特區", "icon": "💼", "center": [24.7960, 121.0010], "zoom": 16},
            {"id": "hcc_guanpu", "name": "關埔經貿核心", "icon": "🌟", "center": [24.7920, 121.0200], "zoom": 16},
            {"id": "hcc_station", "name": "東門站前金融商圈", "icon": "🏦", "center": [24.8020, 120.9710], "zoom": 16}
        ]
    },
    "hsinchu_county": {
        "id": "hsinchu_county", "name": "新竹縣", "icon": "💻", "region": "北部",
        "center": [24.8250, 121.0150], "zoom": 14,
        "districts": [
            {"id": "hc_zhubei", "name": "竹北高鐵經貿CBD", "icon": "🚅", "center": [24.8080, 121.0400], "zoom": 16},
            {"id": "hc_taiyuan", "name": "台元科技經貿商辦", "icon": "🏢", "center": [24.8410, 121.0100], "zoom": 16}
        ]
    },
    "yilan": {
        "id": "yilan", "name": "宜蘭縣", "icon": "🏞️", "region": "北部",
        "center": [24.7550, 121.7530], "zoom": 13,
        "districts": [
            {"id": "yl_city", "name": "宜蘭市文教金融商圈", "icon": "🏦", "center": [24.7570, 121.7530], "zoom": 16},
            {"id": "yl_luodong", "name": "羅東商業經貿中心", "icon": "💼", "center": [24.6780, 121.7700], "zoom": 16}
        ]
    },

    # --- 中部區域 ---
    "taichung": {
        "id": "taichung", "name": "臺中市", "icon": "🌇", "region": "中部",
        "center": [24.1620, 120.6450], "zoom": 13,
        "districts": [
            {"id": "tc_7qi", "name": "七期新市政CBD", "icon": "👑", "center": [24.1610, 120.6430], "zoom": 16},
            {"id": "tc_boulevard", "name": "台灣大道金融軸帶", "icon": "🏦", "center": [24.1550, 120.6620], "zoom": 16},
            {"id": "tc_chongde", "name": "文心崇德新商辦圈", "icon": "📈", "center": [24.1720, 120.6850], "zoom": 16}
        ]
    },
    "miaoli": {
        "id": "miaoli", "name": "苗栗縣", "icon": "⛰️", "region": "中部",
        "center": [24.5600, 120.8200], "zoom": 13,
        "districts": [
            {"id": "ml_zhunan", "name": "竹南頭份科技商貿區", "icon": "🔬", "center": [24.6900, 120.9000], "zoom": 16},
            {"id": "ml_city", "name": "苗栗市中正金融街", "icon": "🏦", "center": [24.5650, 120.8210], "zoom": 16}
        ]
    },
    "changhua": {
        "id": "changhua", "name": "彰化縣", "icon": "🌾", "region": "中部",
        "center": [24.0800, 120.5400], "zoom": 13,
        "districts": [
            {"id": "ch_city", "name": "彰化市中山金融商圈", "icon": "🏦", "center": [24.0810, 120.5420], "zoom": 16},
            {"id": "ch_yuanlin", "name": "員林商業經貿中心", "icon": "🌟", "center": [23.9600, 120.5730], "zoom": 16}
        ]
    },
    "nantou": {
        "id": "nantou", "name": "南投縣", "icon": "🌲", "region": "中部",
        "center": [23.9100, 120.6850], "zoom": 13,
        "districts": [
            {"id": "nt_city", "name": "南投市南崗商務特區", "icon": "🏢", "center": [23.9150, 120.6820], "zoom": 16},
            {"id": "nt_caotun", "name": "草屯經貿商業中心", "icon": "💼", "center": [23.9800, 120.6860], "zoom": 16}
        ]
    },
    "yunlin": {
        "id": "yunlin", "name": "雲林縣", "icon": "🌻", "region": "中部",
        "center": [23.7080, 120.5430], "zoom": 13,
        "districts": [
            {"id": "yl_douliu", "name": "斗六市民生金融商圈", "icon": "🏦", "center": [23.7120, 120.5440], "zoom": 16},
            {"id": "yl_huwei", "name": "虎尾高鐵科技特區", "icon": "🚅", "center": [23.7380, 120.4280], "zoom": 16}
        ]
    },

    # --- 南部區域 ---
    "kaohsiung": {
        "id": "kaohsiung", "name": "高雄市", "icon": "⚓", "region": "南部",
        "center": [22.6250, 120.3050], "zoom": 13,
        "districts": [
            {"id": "kh_bay", "name": "亞洲新灣區經貿特區", "icon": "🌊", "center": [22.6110, 120.3010], "zoom": 16},
            {"id": "kh_zhongzheng", "name": "中正金融金融廊帶", "icon": "🏦", "center": [22.6300, 120.3120], "zoom": 16},
            {"id": "kh_zuoying", "name": "左營高鐵博愛特區", "icon": "🚅", "center": [22.6850, 120.3070], "zoom": 16}
        ]
    },
    "tainan": {
        "id": "tainan", "name": "臺南市", "icon": "🏯", "region": "南部",
        "center": [22.9980, 120.2150], "zoom": 13,
        "districts": [
            {"id": "tn_west", "name": "中西區站前金融商圈", "icon": "🏦", "center": [22.9950, 120.2080], "zoom": 16},
            {"id": "tn_east", "name": "東區南紡商辦特區", "icon": "🌟", "center": [22.9900, 120.2320], "zoom": 16},
            {"id": "tn_yongkang", "name": "永康工業轉型商辦CBD", "icon": "🏢", "center": [23.0250, 120.2450], "zoom": 16}
        ]
    },
    "chiayi_city": {
        "id": "chiayi_city", "name": "嘉義市", "icon": "🌸", "region": "南部",
        "center": [23.4800, 120.4490], "zoom": 14,
        "districts": [
            {"id": "cy_chuiyang", "name": "垂楊金融商貿大道", "icon": "🏦", "center": [23.4750, 120.4450], "zoom": 16},
            {"id": "cy_station", "name": "中山站前商務核心", "icon": "💼", "center": [23.4800, 120.4430], "zoom": 16}
        ]
    },
    "chiayi_county": {
        "id": "chiayi_county", "name": "嘉義縣", "icon": "🌾", "region": "南部",
        "center": [23.4500, 120.3000], "zoom": 13,
        "districts": [
            {"id": "cyc_hsr", "name": "嘉義高鐵經貿特區", "icon": "🚅", "center": [23.4590, 120.3240], "zoom": 16},
            {"id": "cyc_minxiong", "name": "民雄工業科技商務區", "icon": "🏭", "center": [23.5350, 120.4350], "zoom": 16}
        ]
    },
    "pingtung": {
        "id": "pingtung", "name": "屏東縣", "icon": "🌴", "region": "南部",
        "center": [22.6700, 120.4900], "zoom": 13,
        "districts": [
            {"id": "pt_minsheng", "name": "屏東市民生金融商圈", "icon": "🏦", "center": [22.6720, 120.4920], "zoom": 16},
            {"id": "pt_ziyou", "name": "自由路經貿行政商圈", "icon": "💼", "center": [22.6780, 120.4850], "zoom": 16}
        ]
    },

    # --- 東部區域 ---
    "hualien": {
        "id": "hualien", "name": "花蓮縣", "icon": "🌊", "region": "東部",
        "center": [23.9800, 121.6050], "zoom": 13,
        "districts": [
            {"id": "hl_zhongshan", "name": "花蓮市中山金融特區", "icon": "🏦", "center": [23.9820, 121.6070], "zoom": 16},
            {"id": "hl_zhongzheng", "name": "中正路商業經貿核心", "icon": "💼", "center": [23.9780, 121.6040], "zoom": 16}
        ]
    },
    "taitung": {
        "id": "taitung", "name": "臺東縣", "icon": "☀️", "region": "東部",
        "center": [22.7580, 121.1450], "zoom": 13,
        "districts": [
            {"id": "tt_zhonghua", "name": "臺東市中華金融街", "icon": "🏦", "center": [22.7560, 121.1480], "zoom": 16},
            {"id": "tt_datong", "name": "大同商業商務中心", "icon": "💼", "center": [22.7540, 121.1520], "zoom": 16}
        ]
    },

    # --- 離島區域 ---
    "penghu": {
        "id": "penghu", "name": "澎湖縣", "icon": "🏝️", "region": "離島",
        "center": [23.5650, 119.5780], "zoom": 14,
        "districts": [
            {"id": "ph_magong", "name": "馬公港務金融特區", "icon": "🚢", "center": [23.5640, 119.5670], "zoom": 16}
        ]
    },
    "kinmen": {
        "id": "kinmen", "name": "金門縣", "icon": "🏰", "region": "離島",
        "center": [24.4350, 118.3200], "zoom": 13,
        "districts": [
            {"id": "km_jincheng", "name": "金城民生金融商業區", "icon": "🏦", "center": [24.4360, 118.3180], "zoom": 16},
            {"id": "km_jinhu", "name": "金湖免稅經貿特區", "icon": "🌟", "center": [24.4410, 118.3900], "zoom": 16}
        ]
    },
    "lienchiang": {
        "id": "lienchiang", "name": "連江縣", "icon": "🪨", "region": "離島",
        "center": [26.1550, 119.9500], "zoom": 14,
        "districts": [
            {"id": "lc_nangan", "name": "南竿介壽政經商務區", "icon": "🏢", "center": [26.1580, 119.9520], "zoom": 16}
        ]
    }
}

# Premier Landmark Commercial Towers Across ALL 22 Counties
LANDMARK_BUILDINGS = [
    # --- 臺北市 (Taipei) ---
    {"id": "BLD_TP_101", "name": "台北101金融大樓", "county_id": "taipei", "district_id": "tp_xinyi", "address": "台北市信義區信義路五段7號", "lat": 25.0339, "lng": 121.5645, "floors": 101, "tier": "A+"},
    {"id": "BLD_TP_CATHAY", "name": "國泰置地廣場·信義", "county_id": "taipei", "district_id": "tp_xinyi", "address": "台北市信義區忠孝東路五段68號", "lat": 25.0410, "lng": 121.5670, "floors": 46, "tier": "A+"},
    {"id": "BLD_TP_NANSHAN", "name": "台北南山廣場", "county_id": "taipei", "district_id": "tp_xinyi", "address": "台北市信義區松智路17號", "lat": 25.0352, "lng": 121.5668, "floors": 48, "tier": "A+"},
    {"id": "BLD_TP_UNIPRES", "name": "統一國際大樓", "county_id": "taipei", "district_id": "tp_xinyi", "address": "台北市信義區松高路9號", "lat": 25.0395, "lng": 121.5658, "floors": 30, "tier": "A+"},
    {"id": "BLD_TP_HONGTAI", "name": "宏泰世界大樓", "county_id": "taipei", "district_id": "tp_dunhua", "address": "台北市松山區民生東路三段168號", "lat": 25.0578, "lng": 121.5475, "floors": 24, "tier": "A"},
    {"id": "BLD_TP_FED", "name": "遠企中心辦公大樓", "county_id": "taipei", "district_id": "tp_dunhua", "address": "台北市大安區敦化南路二段207號", "lat": 25.0272, "lng": 121.5488, "floors": 43, "tier": "A+"},
    {"id": "BLD_TP_METRO_NEIHU", "name": "大都會科技大樓", "county_id": "taipei", "district_id": "tp_neihu", "address": "台北市內湖區瑞光路513巷", "lat": 25.0795, "lng": 121.5682, "floors": 12, "tier": "A"},
    {"id": "BLD_TP_NK_SOFT", "name": "南港軟體園區世貿大樓", "county_id": "taipei", "district_id": "tp_nangang", "address": "台北市南港區園區街3號", "lat": 25.0595, "lng": 121.6148, "floors": 20, "tier": "A"},
    {"id": "BLD_TP_NANJING_FUBON", "name": "富邦南京商貿大樓", "county_id": "taipei", "district_id": "tp_zhongshan", "address": "台北市中山區南京東路三段136號", "lat": 25.0518, "lng": 121.5420, "floors": 18, "tier": "A"},

    # --- 新北市 (New Taipei) ---
    {"id": "BLD_NT_FED_NEW", "name": "遠東新世紀板橋總部大樓", "county_id": "new_taipei", "district_id": "nt_banqiao", "address": "新北市板橋區新站路16號", "lat": 25.0135, "lng": 121.4655, "floors": 50, "tier": "A+"},
    {"id": "BLD_NT_MANHATTAN", "name": "曼哈頓金融大樓", "county_id": "new_taipei", "district_id": "nt_banqiao", "address": "新北市板橋區文化路一段268號", "lat": 25.0190, "lng": 121.4650, "floors": 22, "tier": "A"},
    {"id": "BLD_NT_JOYCE_IFC", "name": "中悅IFC國際金融中心", "county_id": "new_taipei", "district_id": "nt_xinzhuang", "address": "新北市新莊區中港路與副都心大道口", "lat": 25.0590, "lng": 121.4510, "floors": 30, "tier": "A+"},
    {"id": "BLD_NT_FED_CENTURY", "name": "中和遠東世紀廣場 (A/B棟)", "county_id": "new_taipei", "district_id": "nt_zhonghe", "address": "新北市中和區連城路268號", "lat": 24.9985, "lng": 121.4885, "floors": 18, "tier": "A"},
    {"id": "BLD_NT_SILICON", "name": "新店台北矽谷園區大樓", "county_id": "new_taipei", "district_id": "nt_xindian", "address": "新北市新店區北新路三段205號", "lat": 24.9855, "lng": 121.5385, "floors": 16, "tier": "A"},
    {"id": "BLD_NT_UTOWN", "name": "汐止遠雄U-TOWN商辦特區", "county_id": "new_taipei", "district_id": "nt_xizhi", "address": "新北市汐止區新台五路一段99號", "lat": 25.0605, "lng": 121.6505, "floors": 37, "tier": "A+"},

    # --- 基隆市 (Keelung) ---
    {"id": "BLD_KL_CROWN", "name": "基隆皇冠商業摩天大樓", "county_id": "keelung", "district_id": "kl_port", "address": "基隆市中正區信一路177號", "lat": 25.1305, "lng": 121.7455, "floors": 33, "tier": "A"},
    {"id": "BLD_KL_PORT_HQ", "name": "基隆港務海運商務大樓", "county_id": "keelung", "district_id": "kl_port", "address": "基隆市仁愛區港西街6號", "lat": 25.1320, "lng": 121.7390, "floors": 16, "tier": "A"},
    {"id": "BLD_KL_YI1_FIN", "name": "義一路金融經貿大樓", "county_id": "keelung", "district_id": "kl_xinyi", "address": "基隆市中正區義一路88號", "lat": 25.1330, "lng": 121.7470, "floors": 15, "tier": "A"},

    # --- 桃園市 (Taoyuan) ---
    {"id": "BLD_TY_WORLD_CENTER", "name": "中悅世界中心", "county_id": "taoyuan", "district_id": "ty_art", "address": "桃園市桃園區中正路1071號", "lat": 25.0162, "lng": 121.3003, "floors": 32, "tier": "A+"},
    {"id": "BLD_TY_GLOBAL_HQ", "name": "中悅環球企業總部", "county_id": "taoyuan", "district_id": "ty_art", "address": "桃園市桃園區中正路1082號", "lat": 25.0175, "lng": 121.2995, "floors": 28, "tier": "A+"},
    {"id": "BLD_TY_JINGGUO", "name": "經國亞洲商貿大樓", "county_id": "taoyuan", "district_id": "ty_art", "address": "桃園市桃園區經國路888號", "lat": 25.0280, "lng": 121.3075, "floors": 20, "tier": "A"},
    {"id": "BLD_TY_STATION_FIN", "name": "新光三越金融經貿大樓", "county_id": "taoyuan", "district_id": "ty_station", "address": "桃園市桃園區中正路19號", "lat": 24.9895, "lng": 121.3130, "floors": 18, "tier": "A"},
    {"id": "BLD_TY_QINGPU_CATHAY", "name": "國泰置地廣場·青埔", "county_id": "taoyuan", "district_id": "ty_qingpu", "address": "桃園市中壢區高鐵北路一段58號", "lat": 25.0135, "lng": 121.2155, "floors": 20, "tier": "A+"},
    {"id": "BLD_TY_A8_MED", "name": "長庚國際生醫經貿大樓 (A8)", "county_id": "taoyuan", "district_id": "ty_guishan", "address": "桃園市龜山區復興一路8號", "lat": 25.0592, "lng": 121.3688, "floors": 18, "tier": "A"},
    {"id": "BLD_TY_EVA_AIR", "name": "長榮航空企業全球總部", "county_id": "taoyuan", "district_id": "ty_luzhu", "address": "桃園市蘆竹區新南路一段376號", "lat": 25.0455, "lng": 121.2945, "floors": 16, "tier": "A+"},

    # --- 新竹市 (Hsinchu City) ---
    {"id": "BLD_HCC_GUANGFU", "name": "光復科技商務中心", "county_id": "hsinchu_city", "district_id": "hcc_guangfu", "address": "新竹市東區光復路二段295號", "lat": 24.7960, "lng": 121.0010, "floors": 16, "tier": "A"},
    {"id": "BLD_HCC_GUANPU", "name": "關埔經貿金融大樓", "county_id": "hsinchu_city", "district_id": "hcc_guanpu", "address": "新竹市東區慈雲路118號", "lat": 24.7925, "lng": 121.0210, "floors": 18, "tier": "A"},
    {"id": "BLD_HCC_DONGMEN", "name": "東門站前金融大樓", "county_id": "hsinchu_city", "district_id": "hcc_station", "address": "新竹市東區中正路1號", "lat": 24.8025, "lng": 120.9715, "floors": 14, "tier": "A"},

    # --- 新竹縣 (Hsinchu County) ---
    {"id": "BLD_HC_WEISHUN", "name": "暐順經貿大樓 6+Plaza", "county_id": "hsinchu_county", "district_id": "hc_zhubei", "address": "新竹縣竹北市復興三路二段168號", "lat": 24.8085, "lng": 121.0405, "floors": 20, "tier": "A+"},
    {"id": "BLD_HC_CATHAY_ZB", "name": "國泰置地廣場·竹北", "county_id": "hsinchu_county", "district_id": "hc_zhubei", "address": "新竹縣竹北市自強南路8號", "lat": 24.8140, "lng": 121.0280, "floors": 24, "tier": "A+"},
    {"id": "BLD_HC_TAIYUAN_HQ", "name": "台元科技園區商務總部", "county_id": "hsinchu_county", "district_id": "hc_taiyuan", "address": "新竹縣竹北市台元一街1號", "lat": 24.8415, "lng": 121.0105, "floors": 16, "tier": "A"},

    # --- 宜蘭縣 (Yilan) ---
    {"id": "BLD_YL_CATHAY", "name": "宜蘭國泰金融經貿大樓", "county_id": "yilan", "district_id": "yl_city", "address": "宜蘭市中山路二段420號", "lat": 24.7565, "lng": 121.7525, "floors": 14, "tier": "A"},
    {"id": "BLD_YL_LUODONG_FUBON", "name": "羅東富邦商業經貿大樓", "county_id": "yilan", "district_id": "yl_luodong", "address": "宜蘭縣羅東鎮公正路155號", "lat": 24.6785, "lng": 121.7710, "floors": 12, "tier": "A"},

    # --- 臺中市 (Taichung) ---
    {"id": "BLD_TC_LIANJU_ZHONGYONG", "name": "聯聚中雍大廈", "county_id": "taichung", "district_id": "tc_7qi", "address": "台中市西屯區市政北七路99號", "lat": 24.1645, "lng": 120.6405, "floors": 39, "tier": "A+"},
    {"id": "BLD_TC_DINGSHENG_BHW", "name": "鼎盛BHW台灣財經中心", "county_id": "taichung", "district_id": "tc_7qi", "address": "台中市西屯區市政北二路236號", "lat": 24.1615, "lng": 120.6385, "floors": 36, "tier": "A+"},
    {"id": "BLD_TC_FENGYI_SHIZHENG", "name": "豐邑市政核心大樓", "county_id": "taichung", "district_id": "tc_7qi", "address": "台中市西屯區市政路386號", "lat": 24.1575, "lng": 120.6415, "floors": 38, "tier": "A+"},
    {"id": "BLD_TC_NTC", "name": "NTC國家商貿中心", "county_id": "taichung", "district_id": "tc_7qi", "address": "台中市西屯區市政北二路282號", "lat": 24.1605, "lng": 120.6360, "floors": 35, "tier": "A+"},
    {"id": "BLD_TC_CTBC", "name": "中信金控台中旗艦金融大樓", "county_id": "taichung", "district_id": "tc_7qi", "address": "台中市西屯區惠中路一段88號", "lat": 24.1610, "lng": 120.6440, "floors": 28, "tier": "A+"},
    {"id": "BLD_TC_TAIWAN_BLVD", "name": "順天經貿廣場", "county_id": "taichung", "district_id": "tc_boulevard", "address": "台中市西屯區文心路二段201號", "lat": 24.1565, "lng": 120.6495, "floors": 23, "tier": "A"},

    # --- 苗栗縣 (Miaoli) ---
    {"id": "BLD_ML_ZHUNAN_TECH", "name": "竹南群聯科技經貿大樓", "county_id": "miaoli", "district_id": "ml_zhunan", "address": "苗栗縣竹南鎮科專九路1號", "lat": 24.6920, "lng": 120.9020, "floors": 15, "tier": "A"},
    {"id": "BLD_ML_CITY_FIN", "name": "苗栗世華金融商業大樓", "county_id": "miaoli", "district_id": "ml_city", "address": "苗栗市中正路560號", "lat": 24.5660, "lng": 120.8215, "floors": 12, "tier": "A"},

    # --- 彰化縣 (Changhua) ---
    {"id": "BLD_CH_BANK_HQ", "name": "彰化銀行歷史金融經貿大樓", "county_id": "changhua", "district_id": "ch_city", "address": "彰化市光復路88號", "lat": 24.0820, "lng": 120.5430, "floors": 16, "tier": "A"},
    {"id": "BLD_CH_YUANLIN_FIN", "name": "員林世華商業經貿中心", "county_id": "changhua", "district_id": "ch_yuanlin", "address": "彰化縣員林市中正路420號", "lat": 23.9610, "lng": 120.5740, "floors": 14, "tier": "A"},

    # --- 南投縣 (Nantou) ---
    {"id": "BLD_NT_NANGANG", "name": "南投農會商業金融大樓", "county_id": "nantou", "district_id": "nt_city", "address": "南投市南崗二路1號", "lat": 23.9160, "lng": 120.6830, "floors": 12, "tier": "A"},
    {"id": "BLD_NT_CAOTUN", "name": "草屯商業金融商務中心", "county_id": "nantou", "district_id": "nt_caotun", "address": "南投縣草屯鎮中正路600號", "lat": 23.9810, "lng": 120.6870, "floors": 11, "tier": "A"},

    # --- 雲林縣 (Yunlin) ---
    {"id": "BLD_YL_DOULIU_CATHAY", "name": "斗六國泰金融商業大樓", "county_id": "yunlin", "district_id": "yl_douliu", "address": "雲林縣斗六市民生路200號", "lat": 23.7125, "lng": 120.5445, "floors": 14, "tier": "A"},
    {"id": "BLD_YL_HUWEI_HSR", "name": "虎尾高鐵科技經貿大樓", "county_id": "yunlin", "district_id": "yl_huwei", "address": "雲林縣虎尾鎮站前東路168號", "lat": 23.7385, "lng": 120.4290, "floors": 12, "tier": "A"},

    # --- 嘉義市 (Chiayi City) ---
    {"id": "BLD_CY_CHUIYANG_CATHAY", "name": "嘉義國泰垂楊金融大樓", "county_id": "chiayi_city", "district_id": "cy_chuiyang", "address": "嘉義市西區垂楊路726號", "lat": 23.4755, "lng": 120.4455, "floors": 18, "tier": "A"},
    {"id": "BLD_CY_SK_TOWER", "name": "新光人壽嘉義經貿大樓", "county_id": "chiayi_city", "district_id": "cy_station", "address": "嘉義市東區中山路188號", "lat": 23.4805, "lng": 120.4440, "floors": 15, "tier": "A"},

    # --- 嘉義縣 (Chiayi County) ---
    {"id": "BLD_CYC_HSR_TOWER", "name": "嘉義高鐵經貿商業大樓", "county_id": "chiayi_county", "district_id": "cyc_hsr", "address": "嘉義縣太保市保鐵五路88號", "lat": 23.4595, "lng": 120.3245, "floors": 12, "tier": "A"},
    {"id": "BLD_CYC_MINXIONG", "name": "民雄工業科技商務總部", "county_id": "chiayi_county", "district_id": "cyc_minxiong", "address": "嘉義縣民雄鄉建國路二段", "lat": 23.5360, "lng": 120.4360, "floors": 11, "tier": "A"},

    # --- 臺南市 (Tainan) ---
    {"id": "BLD_TN_CATHAY_ZD", "name": "國泰置地廣場·台南", "county_id": "tainan", "district_id": "tn_west", "address": "台南市中西區西門路一段658號", "lat": 22.9875, "lng": 120.1985, "floors": 22, "tier": "A+"},
    {"id": "BLD_TN_SK_TOWER", "name": "新光三越商辦大樓", "county_id": "tainan", "district_id": "tn_west", "address": "台南市中西區中山路162號", "lat": 22.9960, "lng": 120.2105, "floors": 18, "tier": "A"},
    {"id": "BLD_TN_TS_HQ", "name": "南紡企業全球營運總部", "county_id": "tainan", "district_id": "tn_east", "address": "台南市東區中華東路一段366號", "lat": 22.9910, "lng": 120.2330, "floors": 20, "tier": "A+"},
    {"id": "BLD_TN_YONGKANG_FIN", "name": "永康世華商業金融大樓", "county_id": "tainan", "district_id": "tn_yongkang", "address": "台南市永康區中華路425號", "lat": 23.0255, "lng": 120.2455, "floors": 16, "tier": "A"},

    # --- 高雄市 (Kaohsiung) ---
    {"id": "BLD_KH_85", "name": "高雄85大樓經貿金融中心", "county_id": "kaohsiung", "district_id": "kh_bay", "address": "高雄市苓雅區自強三路5號", "lat": 22.6115, "lng": 120.3005, "floors": 85, "tier": "A+"},
    {"id": "BLD_KH_THE_ONE", "name": "遠雄THE ONE商辦特區", "county_id": "kaohsiung", "district_id": "kh_bay", "address": "高雄市前鎮區中華五路", "lat": 22.6080, "lng": 120.3030, "floors": 68, "tier": "A+"},
    {"id": "BLD_KH_GC_BAY", "name": "國城亞灣經貿創新大樓", "county_id": "kaohsiung", "district_id": "kh_bay", "address": "高雄市前鎮區復興四路12號", "lat": 22.6030, "lng": 120.3015, "floors": 24, "tier": "A+"},
    {"id": "BLD_KH_ZZ_FIN", "name": "中正金融中心大樓", "county_id": "kaohsiung", "district_id": "kh_zhongzheng", "address": "高雄市新興區中正三路55號", "lat": 22.6310, "lng": 120.3115, "floors": 22, "tier": "A"},
    {"id": "BLD_KH_POUCHEN", "name": "寶成雙子星企業大樓", "county_id": "kaohsiung", "district_id": "kh_bay", "address": "高雄市前鎮區中山二路2號", "lat": 22.6050, "lng": 120.3070, "floors": 26, "tier": "A"},

    # --- 屏東縣 (Pingtung) ---
    {"id": "BLD_PT_CATHAY", "name": "屏東國泰金融商業大樓", "county_id": "pingtung", "district_id": "pt_minsheng", "address": "屏東市民生路250號", "lat": 22.6725, "lng": 120.4925, "floors": 14, "tier": "A"},
    {"id": "BLD_PT_ZIYOU_FUBON", "name": "屏東富邦經貿商業中心", "county_id": "pingtung", "district_id": "pt_ziyou", "address": "屏東市自由路560號", "lat": 22.6785, "lng": 120.4855, "floors": 12, "tier": "A"},

    # --- 花蓮縣 (Hualien) ---
    {"id": "BLD_HL_CATHAY", "name": "花蓮國泰金融商貿大樓", "county_id": "hualien", "district_id": "hl_zhongshan", "address": "花蓮市中山路450號", "lat": 23.9825, "lng": 121.6075, "floors": 14, "tier": "A"},
    {"id": "BLD_HL_SK_TOWER", "name": "新光人壽花蓮經貿大樓", "county_id": "hualien", "district_id": "hl_zhongzheng", "address": "花蓮市中正路500號", "lat": 23.9785, "lng": 121.6045, "floors": 12, "tier": "A"},

    # --- 臺東縣 (Taitung) ---
    {"id": "BLD_TT_CATHAY", "name": "臺東國泰世華金融大樓", "county_id": "taitung", "district_id": "tt_zhonghua", "address": "臺東市中華路一段580號", "lat": 22.7565, "lng": 121.1485, "floors": 12, "tier": "A"},
    {"id": "BLD_TT_DATONG_FIN", "name": "臺東大同商業經貿中心", "county_id": "taitung", "district_id": "tt_datong", "address": "臺東市大同路120號", "lat": 22.7545, "lng": 121.1525, "floors": 10, "tier": "A"},

    # --- 離島區域 ---
    # 澎湖縣 (Penghu)
    {"id": "BLD_PH_PORT", "name": "馬公港務國際經貿大樓", "county_id": "penghu", "district_id": "ph_magong", "address": "澎湖縣馬公市臨海路36號", "lat": 23.5645, "lng": 119.5675, "floors": 10, "tier": "A"},
    # 金門縣 (Kinmen)
    {"id": "BLD_KM_MINSHENG", "name": "金門信用合作社商務大樓", "county_id": "kinmen", "district_id": "km_jincheng", "address": "金門縣金城鎮民生路25號", "lat": 24.4365, "lng": 118.3185, "floors": 10, "tier": "A"},
    {"id": "BLD_KM_EVERRICH", "name": "昇恆昌金湖國際商務中心", "county_id": "kinmen", "district_id": "km_jinhu", "address": "金門縣金湖鎮太湖路二段218號", "lat": 24.4415, "lng": 118.3905, "floors": 12, "tier": "A"},
    # 連江縣 (Matsu)
    {"id": "BLD_LC_NANGAN", "name": "馬祖綜合經貿金融大樓", "county_id": "lienchiang", "district_id": "lc_nangan", "address": "連江縣南竿鄉介壽村256號", "lat": 26.1585, "lng": 119.9525, "floors": 8, "tier": "A"}
]

# Business Categories & Border Groups
CORE_CATEGORIES = [
    {"name": "IT資訊與軟體研發", "icon": "💻", "color": "#0284C7", "border": "NONE"},
    {"name": "金融保險與資產管理", "icon": "🏦", "color": "#059669", "border": "NONE"},
    {"name": "建築工程與室內設計", "icon": "📐", "color": "#D97706", "border": "NONE"},
    {"name": "專業會計與法律智財", "icon": "⚖️", "color": "#7C3AED", "border": "NONE"},
    {"name": "跨國貿易與進出口商", "icon": "🌐", "color": "#2563EB", "border": "NONE"},
    {"name": "企管顧問與人資獵頭", "icon": "💼", "color": "#475569", "border": "NONE"},
    # Four High-Value Border Groups
    {"name": "商務中心/共享辦公", "icon": "🏢", "color": "#DC2626", "border": "COWORKING"},
    {"name": "牙醫醫美/專科體系", "icon": "🩺", "color": "#0D9488", "border": "CLINIC"},
    {"name": "企業營運總部(餐飲/零售)", "icon": "🍔", "color": "#EA580C", "border": "CORP_HQ"},
    {"name": "物流倉儲·海空運總部", "icon": "🚢", "color": "#0284C7", "border": "LOGISTICS"}
]

COMPANY_PREFIXES = {
    "IT資訊與軟體研發": ["智拓資訊", "聯雲數位", "凌威軟體", "鈦準科技", "數創整合", "芯曜系統", "宏曜科技", "極智雲端", "創匯資訊", "艾斯威科技"],
    "金融保險與資產管理": ["國泰金控營運", "富邦人壽展業", "新光金融管理", "元大證券投資", "台新資產信託", "永豐租賃顧問", "兆豐財富管理"],
    "建築工程與室內設計": ["九典聯合建築師", "原相工程顧問", "十方空間設計", "大矩聯合事務所", "太極營造工程", "築拓機電設計"],
    "專業會計與法律智財": ["勤業眾信聯合", "安侯建業聯合", "致遠法律專利", "立揚智財專利", "宏景會計師", "誠揚企管法務"],
    "跨國貿易與進出口商": ["日商三菱物產", "德商博世貿易", "美商邁高國際", "瑞昇進出口", "東洋精密貿易", "華貿跨國實業"],
    "企管顧問與人資獵頭": ["藝思人才顧問", "英傑企管顧問", "萬寶華人資諮詢", "優勢管理顧問", "聯曜人力資源", "博思策略諮詢"],
    "商務中心/共享辦公": ["JustCo 捷思商務中心", "Spaces 共享辦公室", "德事商務中心 (TEC)", "大瀚環球商務中心", "雷格斯 Regus 商務特區", "微客空間商務中心"],
    "牙醫醫美/專科體系": ["品漾數位美學牙醫", "愛爾麗醫美旗艦", "君綺醫學美容中心", "博康聯合專科診所", "雅丰美膚醫學", "極緻植牙數位中心"],
    "企業營運總部(餐飲/零售)": ["王品集團後勤營運中心", "瓦城泰統數位總部", "乾杯集團營運管理處", "三商餐飲資訊中心", "路易莎咖啡行政總部", "藏壽司台灣運籌中心"],
    "物流倉儲·海空運總部": ["長榮物流總部", "陽明海運承攬處", "萬海國際航運", "中菲行國際物流", "沛榮國際海運", "台驊國際控股"]
}

LOW_VOLTAGE_NEEDS_BY_CAT = {
    "IT資訊與軟體研發": "需求：Cat6A高頻網路佈線、10G核心交換器、雙冗餘UPS機房、人臉辨識門禁、視訊會議大螢幕",
    "金融保險與資產管理": "需求：金融高規NDAA監控、金庫/機密檔案門禁、全天候數位錄影備份、IP-PBX總機系統、高階多功能OA彩色影印機",
    "建築工程與室內設計": "需求：A0高速大圖工程繪圖機、NAS大型圖檔儲存陣列、全彩OA租賃合約、繪圖工作站專用網路",
    "專業會計與法律智財": "需求：每分鐘65張以上極速雙面影印機、保密碎紙與浮水印列印、指紋感應門禁、靜音會議室視訊系統",
    "跨國貿易與進出口商": "需求：跨時區Teams/Zoom國際視訊系統、多線國際電話交換機(SIP Trunk)、雲端PBX、高速彩色掃描歸檔",
    "企管顧問與人資獵頭": "需求：高密度多功能面談室預約系統、分機錄音合約備份、門禁打卡考勤連動ERP、訪客登記管理平板",
    "商務中心/共享辦公": "需求：⭐ 高客單價！多組獨立VLAN網路切割、20組以上獨立密碼刷卡門禁、每間獨立分機總機、公共OA事務機刷卡計費",
    "牙醫醫美/專科體系": "需求：⭐ 高預算！診間隱私防護全彩監控、手術室雙備援門禁、電子病歷PACS伺服器機房、全區智慧迎賓廣播",
    "企業營運總部(餐飲/零售)": "需求：⭐ 全台分店中央監控機房、高畫質視訊戰情室、企業級總機PBX系統、月印量5萬張以上OA影印設備",
    "物流倉儲·海空運總部": "需求：⭐ 長距離光纖佈線、海關保稅區監控攝影機、車牌辨識道閘系統、工業級機房冷通道散熱"
}

STATUS_POOL = ["尚未拜訪", "尚未拜訪", "尚未拜訪", "洽談中", "已拜訪"]

def generate_database():
    companies = []
    company_id_counter = 1000

    for bld in LANDMARK_BUILDINGS:
        total_floors = max(2, min(bld["floors"], 35))
        # Larger buildings have more tenants
        company_count = random.randint(14, 28)
        floor_pool = [random.randint(2, total_floors) for _ in range(company_count)]
        chosen_floors = sorted(floor_pool, reverse=True)

        for fl in chosen_floors:
            company_id_counter += 1
            dice = random.random()
            if dice < 0.15:
                cat_info = next(c for c in CORE_CATEGORIES if c["border"] == "COWORKING")
            elif dice < 0.28:
                cat_info = next(c for c in CORE_CATEGORIES if c["border"] == "CLINIC")
            elif dice < 0.40:
                cat_info = next(c for c in CORE_CATEGORIES if c["border"] == "CORP_HQ")
            elif dice < 0.52:
                cat_info = next(c for c in CORE_CATEGORIES if c["border"] == "LOGISTICS")
            else:
                cat_info = random.choice([c for c in CORE_CATEGORIES if c["border"] == "NONE"])

            cat_name = cat_info["name"]
            prefix = random.choice(COMPANY_PREFIXES[cat_name])
            suffix = random.choice(["股份有限公司", "有限公司", "台灣分公司", "辦事處", "企業社"])
            comp_name = f"{prefix}{suffix}"

            cap_rand = random.random()
            if cap_rand < 0.25:
                capital_str = f"{random.randint(10, 60) * 1000}萬"
                capital_tier = "TIER_100M"
            elif cap_rand < 0.55:
                capital_str = f"{random.randint(30, 99) * 100}萬"
                capital_tier = "TIER_30M"
            elif cap_rand < 0.85:
                capital_str = f"{random.randint(5, 29) * 100}萬"
                capital_tier = "TIER_5M"
            else:
                capital_str = f"{random.randint(50, 490)}萬"
                capital_tier = "TIER_UNDER_5M"

            is_listed = (capital_tier == "TIER_100M" and random.random() < 0.45)
            tax_id = str(random.randint(10000000, 99999999))
            rep_names = ["林俊銘", "陳威廷", "黃柏宇", "李雅婷", "張文德", "王致遠", "劉建宏", "蔡孟蓉", "吳冠廷", "鄭宇翔"]
            rep_name = random.choice(rep_names)
            phone = f"0{random.randint(2, 8)}-{random.randint(200, 899)}{random.randint(1000, 9999)}"

            floor_str = f"{fl}F"
            if random.random() < 0.35:
                floor_str += f"-{random.choice(['A', 'B', 'C', '1室', '2室', '3室'])}"

            jitter_lat = bld["lat"] + random.uniform(-0.00015, 0.00015)
            jitter_lng = bld["lng"] + random.uniform(-0.00015, 0.00015)

            comp_obj = {
                "id": f"C_{company_id_counter}",
                "name": comp_name,
                "county_id": bld["county_id"],
                "district_id": bld["district_id"],
                "building_id": bld["id"],
                "building_name": bld["name"],
                "floor": floor_str,
                "floor_num": fl,
                "address": f"{bld['address']} {floor_str}",
                "lat": round(jitter_lat, 6),
                "lng": round(jitter_lng, 6),
                "category": cat_name,
                "cat_icon": cat_info["icon"],
                "cat_color": cat_info["color"],
                "border_group": cat_info["border"],
                "capital_str": capital_str,
                "capital_tier": capital_tier,
                "is_listed": is_listed,
                "tax_id": tax_id,
                "rep_name": rep_name,
                "phone": phone,
                "status": random.choice(STATUS_POOL),
                "low_voltage_needs": LOW_VOLTAGE_NEEDS_BY_CAT[cat_name]
            }
            companies.append(comp_obj)

    for b in LANDMARK_BUILDINGS:
        b["company_count"] = len([c for c in companies if c["building_id"] == b["id"]])

    bundle = {
        "counties": COUNTIES,
        "buildings": LANDMARK_BUILDINGS,
        "companies": companies,
        "categories": CORE_CATEGORIES,
        "meta": {
            "title": "全台商辦＆企業地圖",
            "version": "2.1.0",
            "total_counties": len(COUNTIES),
            "total_companies": len(companies),
            "total_buildings": len(LANDMARK_BUILDINGS),
            "target_industry": "辦公室設備（OA影印機）與弱電系統工程規劃"
        }
    }

    output_file = 'commercial_database_taiwan.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    print(f"[OK] 全台商辦資料庫生成成功！總計 {len(companies):,} 家公司、{len(LANDMARK_BUILDINGS)} 棟指標大樓、完整涵蓋 {len(COUNTIES)} 個縣市！")
    return bundle

if __name__ == '__main__':
    generate_database()
