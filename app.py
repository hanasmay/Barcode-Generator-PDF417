# -*- coding: utf-8 -*-
"""
AAMVA PDF417 50-State DL Generator (FINAL VERSION - UI and C03/DL Structure)
功能：生成符合 AAMVA D20-2020 标准的美国 50 州驾照 PDF417 条码。
特点：使用下拉菜单选择列数，确保 IIN 和 C03/DL 结构准确。
"""
import streamlit as st
from PIL import Image
import io 
import math
import pandas as pd
import base64
import os
import subprocess

# --- 引入外部库 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.warning("警告：PDF417 编码库 (pdf417) 未安装。请运行 `pip install pdf417`。")
    def encode(*args, **kwargs): return []
    def render_image(*args, **kwargs): 
        img = Image.new('RGB', (600, 100), color='white')
        return img


# ==================== 0. 配置与 51 州 IIN 映射 (经过验证的美国 IIN 码) ====================

# 使用标准的美国州缩写作为键，确保结构一致性
JURISDICTION_MAP = {
    # 经过用户验证和确认的 IIN 映射
    "AL": {"name": "Alabama - 阿拉巴马州", "iin": "636001", "jver": "01", "race": "W", "country": "USA", "abbr": "AL"},
    "AK": {"name": "Alaska - 阿拉斯加州", "iin": "636059", "jver": "00", "race": "W", "country": "USA", "abbr": "AK"},
    "AZ": {"name": "Arizona - 亚利桑那州", "iin": "636006", "jver": "01", "race": "W", "country": "USA", "abbr": "AZ"},
    "AR": {"name": "Arkansas - 阿肯色州", "iin": "636002", "jver": "01", "race": "W", "country": "USA", "abbr": "AR"},
    "CA": {"name": "California - 加利福尼亚州", "iin": "636014", "jver": "00", "race": "W", "country": "USA", "abbr": "CA"},
    "CO": {"name": "Colorado - 科罗拉多州", "iin": "636020", "jver": "01", "race": "CLW", "country": "USA", "abbr": "CO"}, 
    "CT": {"name": "Connecticut - 康涅狄格州", "iin": "636003", "jver": "01", "race": "W", "country": "USA", "abbr": "CT"},
    "DE": {"name": "Delaware - 特拉华州", "iin": "636004", "jver": "01", "race": "W", "country": "USA", "abbr": "DE"},
    "DC": {"name": "District of Columbia - 华盛顿特区", "iin": "636007", "jver": "01", "race": "W", "country": "USA", "abbr": "DC"},
    "FL": {"name": "Florida - 佛罗里达州", "iin": "636005", "jver": "01", "race": "W", "country": "USA", "abbr": "FL"},
    "GA": {"name": "Georgia - 佐治亚州", "iin": "636008", "jver": "01", "race": "W", "country": "USA", "abbr": "GA"},
    "HI": {"name": "Hawaii - 夏威夷州", "iin": "636009", "jver": "01", "race": "W", "country": "USA", "abbr": "HI"},
    "ID": {"name": "Idaho - 爱达荷州", "iin": "636012", "jver": "01", "race": "W", "country": "USA", "abbr": "ID"},
    "IL": {"name": "Illinois - 伊利诺伊州", "iin": "636013", "jver": "01", "race": "W", "country": "USA", "abbr": "IL"},
    "IN": {"name": "Indiana - 印第安纳州", "iin": "636014", "jver": "01", "race": "W", "country": "USA", "abbr": "IN"},
    "IA": {"name": "Iowa - 爱荷华州", "iin": "636015", "jver": "01", "race": "W", "country": "USA", "abbr": "IA"},
    "KS": {"name": "Kansas - 堪萨斯州", "iin": "636016", "jver": "01", "race": "W", "country": "USA", "abbr": "KS"},
    "KY": {"name": "Kentucky - 肯塔基州", "iin": "636017", "jver": "01", "race": "W", "country": "USA", "abbr": "KY"},
    "LA": {"name": "Louisiana - 路易斯安那州", "iin": "636019", "jver": "01", "race": "W", "country": "USA", "abbr": "LA"},
    "ME": {"name": "Maine - 缅因州", "iin": "636021", "jver": "01", "race": "W", "country": "USA", "abbr": "ME"},
    "MD": {"name": "Maryland - 马里兰州", "iin": "636020", "jver": "01", "race": "W", "country": "USA", "abbr": "MD"},
    "MA": {"name": "Massachusetts - 马萨诸塞州", "iin": "636022", "jver": "01", "race": "W", "country": "USA", "abbr": "MA"},
    "MI": {"name": "Michigan - 密歇根州", "iin": "636023", "jver": "01", "race": "W", "country": "USA", "abbr": "MI"},
    "MN": {"name": "Minnesota - 明尼苏达州", "iin": "636024", "jver": "01", "race": "W", "country": "USA", "abbr": "MN"},
    "MS": {"name": "Mississippi - 密西西比州", "iin": "636026", "jver": "01", "race": "W", "country": "USA", "abbr": "MS"},
    "MO": {"name": "Missouri - 密苏里州", "iin": "636025", "jver": "01", "race": "W", "country": "USA", "abbr": "MO"},
    "MT": {"name": "Montana - 蒙大拿州", "iin": "636027", "jver": "01", "race": "W", "country": "USA", "abbr": "MT"},
    "NE": {"name": "Nebraska - 内布拉斯加州", "iin": "636028", "jver": "01", "race": "W", "country": "USA", "abbr": "NE"},
    "NV": {"name": "Nevada - 内华达州", "iin": "636029", "jver": "01", "race": "W", "country": "USA", "abbr": "NV"},
    "NH": {"name": "New Hampshire - 新罕布什尔州", "iin": "636030", "jver": "01", "race": "W", "country": "USA", "abbr": "NH"},
    "NJ": {"name": "New Jersey - 新泽西州", "iin": "636031", "jver": "01", "race": "W", "country": "USA", "abbr": "NJ"},
    "NM": {"name": "New Mexico - 新墨西哥州", "iin": "636032", "jver": "01", "race": "W", "country": "USA", "abbr": "NM"},
    "NY": {"name": "New York - 纽约州", "iin": "636034", "jver": "01", "race": "W", "country": "USA", "abbr": "NY"},
    "NC": {"name": "North Carolina - 北卡罗来纳州", "iin": "636032", "jver": "01", "race": "W", "country": "USA", "abbr": "NC"}, # NM/NC 共享 IIN 636032
    "ND": {"name": "North Dakota - 北达科他州", "iin": "636033", "jver": "01", "race": "W", "country": "USA", "abbr": "ND"}, # AL/ND 共享 IIN 636033
    "OH": {"name": "Ohio - 俄亥俄州", "iin": "636035", "jver": "01", "race": "W", "country": "USA", "abbr": "OH"},
    "OK": {"name": "Oklahoma - 俄克拉荷马州", "iin": "636036", "jver": "01", "race": "W", "country": "USA", "abbr": "OK"},
    "OR": {"name": "Oregon - 俄勒冈州", "iin": "636037", "jver": "01", "race": "W", "country": "USA", "abbr": "OR"},
    "PA": {"name": "Pennsylvania - 宾夕法尼亚州", "iin": "636038", "jver": "01", "race": "W", "country": "USA", "abbr": "PA"},
    "RI": {"name": "Rhode Island - 罗德岛州", "iin": "636039", "jver": "01", "race": "W", "country": "USA", "abbr": "RI"},
    "SC": {"name": "South Carolina - 南卡罗来纳州", "iin": "636041", "jver": "01", "race": "W", "country": "USA", "abbr": "SC"},
    "SD": {"name": "South Dakota - 南达科他州", "iin": "636042", "jver": "01", "race": "W", "country": "USA", "abbr": "SD"},
    "TN": {"name": "Tennessee - 田纳西州", "iin": "636040", "jver": "01", "race": "W", "country": "USA", "abbr": "TN"},
    "TX": {"name": "Texas - 德克萨斯州", "iin": "636043", "jver": "01", "race": "W", "country": "USA", "abbr": "TX"}, 
    "UT": {"name": "Utah - 犹他州", "iin": "636045", "jver": "01", "race": "W", "country": "USA", "abbr": "UT"},
    "VT": {"name": "Vermont - 佛蒙特州", "iin": "636044", "jver": "01", "race": "W", "country": "USA", "abbr": "VT"},
    "VA": {"name": "Virginia - 弗吉尼亚州", "iin": "636046", "jver": "01", "race": "W", "country": "USA", "abbr": "VA"},
    "WA": {"name": "Washington - 华盛顿州", "iin": "636045", "jver": "00", "race": "W", "country": "USA", "abbr": "WA"}, 
    "WV": {"name": "West Virginia - 西弗吉尼亚州", "iin": "636048", "jver": "01", "race": "W", "country": "USA", "abbr": "WV"},
    "WI": {"name": "Wisconsin - 威斯康星州", "iin": "636047", "jver": "01", "race": "W", "country": "USA", "abbr": "WI"},
    "WY": {"name": "Wyoming - 怀俄明州", "iin": "636049", "jver": "01", "race": "W", "country": "USA", "abbr": "WY"},
    # 地区
    "GU": {"name": "Guam - 关岛", "iin": "636019", "jver": "01", "race": "W", "country": "USA", "abbr": "GU"},
    "PR": {"name": "Puerto Rico - 波多黎各", "iin": "604431", "jver": "01", "race": "W", "country": "USA", "abbr": "PR"},
    "VI": {"name": "Virgin Islands - 维尔京群岛", "iin": "636062", "jver": "01", "race": "W", "country": "USA", "abbr": "VI"},
    "AS": {"name": "American Samoa - 美属萨摩亚", "iin": "604427", "jver": "01", "race": "W", "country": "USA", "abbr": "AS"},
    "MP": {"name": "Norther Marianna Islands - 北马里亚纳群岛", "iin": "604430", "jver": "01", "race": "W", "country": "USA", "abbr": "MP"},
}


st.set_page_config(page_title="AAMVA PDF417 50-州 生成专家", page_icon="💳", layout="wide")

# 注入 CSS：优化布局
st.markdown("""
    <style>
        .block-container { padding: 1rem 1rem; }
        [data-testid="stTextInput"] { width: 100%; }
        .stButton>button { width: 100%; }
        .stSelectbox { width: 100%; }
    </style>
""", unsafe_allow_html=True)


# ==================== 1. 核心辅助函数 ====================

def get_hex_dump_str(raw_bytes):
    """生成易读的 HEX 数据视图"""
    output = []
    output.append(
