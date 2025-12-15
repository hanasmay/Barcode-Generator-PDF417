# -*- coding: utf-8 -*-
"""
AAMVA PDF417 50-State DL Generator (FINAL VERSION WITH PRECISE HIDING AND DEFAULTS)
功能：生成符合 AAMVA D20-2020 标准的美国 50 州驾照 PDF417 条码。
特点：修正了 1 字节长度错误，并默认隐藏 DCL 字段。
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


# ==================== 0. 配置与 51 州 IIN 映射 ====================

JURISDICTION_MAP = {
    "ME": {"name": "Maine - 缅因州", "iin": "636021", "jver": "01", "race": "W"},
    "VT": {"name": "Vermont - 佛蒙特州", "iin": "636044", "jver": "01", "race": "W"},
    "NH": {"name": "New Hampshire - 新罕布什尔州", "iin": "636029", "jver": "01", "race": "W"},
    "MA": {"name": "Massachusetts - 马萨诸塞州", "iin": "636022", "jver": "01", "race": "W"},
    "RI": {"name": "Rhode Island - 罗德岛州", "iin": "636039", "jver": "01", "race": "W"},
    "CT": {"name": "Connecticut - 康涅狄格州", "iin": "636003", "jver": "01", "race": "W"},
    "NY": {"name": "New York - 纽约州", "iin": "636034", "jver": "01", "race": "W"},
    "NJ": {"name": "New Jersey - 新泽西州", "iin": "636030", "jver": "01", "race": "W"},
    "PA": {"name": "Pennsylvania - 宾夕法尼亚州", "iin": "636038", "jver": "01", "race": "W"},
    "OH": {"name": "Ohio - 俄亥俄州", "iin": "636035", "jver": "01", "race": "W"},
    "IN": {"name": "Indiana - 印第安纳州", "iin": "636014", "jver": "01", "race": "W"},
    "IL": {"name": "Illinois - 伊利诺伊州", "iin": "636013", "jver": "01", "race": "W"},
    "MI": {"name": "Michigan - 密歇根州", "iin": "636023", "jver": "01", "race": "W"},
    "WI": {"name": "Wisconsin - 威斯康星州", "iin": "636047", "jver": "01", "race": "W"},
    "MN": {"name": "Minnesota - 明尼苏达州", "iin": "636024", "jver": "01", "race": "W"},
    "IA": {"name": "Iowa - 爱荷华州", "iin": "636015", "jver": "01", "race": "W"},
    "MO": {"name": "Missouri - 密苏里州", "iin": "636025", "jver": "01", "race": "W"},
    "ND": {"name": "North Dakota - 北达科他州", "iin": "636033", "jver": "01", "race": "W"},
    "SD": {"name": "South Dakota - 南达科他州", "iin": "636042", "jver": "01", "race": "W"},
    "NE": {"name": "Nebraska - 内布拉斯加州", "iin": "636028", "jver": "01", "race": "W"},
    "KS": {"name": "Kansas - 堪萨斯州", "iin": "636016", "jver": "01", "race": "W"},
    "DE": {"name": "Delaware - 特拉华州", "iin": "636004", "jver": "01", "race": "W"},
    "MD": {"name": "Maryland - 马里兰州", "iin": "636020", "jver": "01", "race": "W"},
    "VA": {"name": "Virginia - 弗吉尼亚州", "iin": "636046", "jver": "01", "race": "W"},
    "WV": {"name": "West Virginia - 西弗吉尼亚州", "iin": "636048", "jver": "01", "race": "W"},
    "NC": {"name": "North Carolina - 北卡罗来纳州", "iin": "636032", "jver": "01", "race": "W"},
    "SC": {"name": "South Carolina - 南卡罗来纳州", "iin": "636041", "jver": "01", "race": "W"},
    "GA": {"name": "Georgia - 佐治亚州", "iin": "636008", "jver": "01", "race": "W"},
    "FL": {"name": "Florida - 佛罗里达州", "iin": "636005", "jver": "01", "race": "W"},
    "KY": {"name": "Kentucky - 肯塔基州", "iin": "636017", "jver": "01", "race": "W"},
    "TN": {"name": "Tennessee - 田纳西州", "iin": "636040", "jver": "01", "race": "W"},
    "AL": {"name": "Alabama - 阿拉巴马州", "iin": "636001", "jver": "01", "race": "W"},
    "MS": {"name": "Mississippi - 密西西比州", "iin": "636026", "jver": "01", "race": "W"},
    "AR": {"name": "Arkansas - 阿肯色州", "iin": "636002", "jver": "01", "race": "W"},
    "LA": {"name": "Louisiana - 路易斯安那州", "iin": "636019", "jver": "01", "race": "W"},
    "OK": {"name": "Oklahoma - 俄克拉荷马州", "iin": "636036", "jver": "01", "race": "W"},
    "TX": {"name": "Texas - 德克萨斯州", "iin": "636043", "jver": "01", "race": "W"},
    "MT": {"name": "Montana - 蒙大拿州", "iin": "636027", "jver": "01", "race": "W"},
    "ID": {"name": "Idaho - 爱达荷州", "iin": "636012", "jver": "01", "race": "W"},
    "WY": {"name": "Wyoming - 怀俄明州", "iin": "636049", "jver": "01", "race": "W"},
    "CO": {"name": "Colorado - 科罗拉多州", "iin": "636020", "jver": "01", "race": "CLW"}, 
    "UT": {"name": "Utah - 犹他州", "iin": "636045", "jver": "01", "race": "W"},
    "AZ": {"name": "Arizona - 亚利桑那州", "iin": "636006", "jver": "01", "race": "W"},
    "NM": {"name": "New Mexico - 新墨西哥州", "iin": "636031", "jver": "01", "race": "W"},
    "AK": {"name": "Alaska - 阿拉斯加州", "iin": "636000", "jver": "00", "race": "W"},
    "WA": {"name": "Washington - 华盛顿州", "iin": "636045", "jver": "00", "race": "W"},
    "OR": {"name": "Oregon - 俄勒冈州", "iin": "636037", "jver": "01", "race": "W"},
    "CA": {"name": "California - 加利福尼亚州", "iin": "636000", "jver": "00", "race": "W"},
    "NV": {"name": "Nevada - 内华达州", "iin": "636032", "jver": "01", "race": "W"},
    "HI": {"name": "Hawaii - 夏威夷州", "iin": "636009", "jver": "01", "race": "W"},
    "DC": {"name": "District of Columbia - 华盛顿特区", "iin": "636007", "jver": "01", "race": "W"},
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
    output.append(f"📦 数据长度: {len(raw_bytes)} 字节")
    output.append("-" * 50)
    
    if isinstance(raw_bytes, str):
        raw_bytes = raw_bytes.encode('latin-1', errors='ignore')

    hex_str = raw_bytes.hex().upper()

    for i in range(0, len(hex_str), 32):
        chunk = hex_str[i:i+32]
        ascii_chunk = ""
        for j in range(0, len(chunk), 2):
            try:
                byte_val = int(chunk[j:j+2], 16)
                ascii_chunk += chr(byte_val) if 32 <= byte_val <= 126 else "."
            except ValueError:
                ascii_chunk += "?" 
        output.append(f"{chunk.ljust(32)} | {ascii_chunk}")
    return "\n".join(output)

def clean_date_input(date_str):
    """清理日期输入，移除分隔符"""
    return date_str.replace("/", "").replace("-", "").strip().upper()

def convert_height_to_inches_ui(height_str):
    """将身高 (如 510) 转换为 AAMVA 要求的 3 位总英寸 (如 070)"""
    height_str = height_str.strip()
    if not height_str or not height_str.isdigit(): return "000"
    
    if len(height_str) < 3: 
        total_inches = int(height_str)
    else:
        try:
            inches_part = int(height_str[-2:])
            feet_part = int(height_str[:-2])
            total_inches = (feet_part * 12) + inches_part
        except ValueError:
             return f"{int(height_str):03d}"
             
    return f"{total_inches:03d}"


# ==================== 2. AAMVA 生成核心逻辑 (强制单文件模式) ====================

def generate_aamva_data_core(inputs):
    """根据 Streamlit 输入字典，生成 AAMVA PDF417 原始数据流 (强制单文件模式)"""
    
    # 1. 获取州配置
    jurisdiction_code = inputs['jurisdiction_code']
    config = JURISDICTION_MAP.get(jurisdiction_code)
    
    # 动态版本控制
    iin = config['iin']
    jurisdiction_version = config['jver']
    aamva_version = "09" # 通用版本
    
    # **核心结构：强制使用 01 个子文件**
    num_entries = "01" 
    
    # 2. 清洗输入数据 - 基础字段
    last_name = inputs['last_name'].strip().upper()
    first_name = inputs['first_name'].strip().upper()

    dob = clean_date_input(inputs['dob'])
    exp_date = clean_date_input(inputs['exp_date'])
    iss_date = clean_date_input(inputs['iss_date'])
    rev_date = clean_date_input(inputs['rev_date'])
    dl_number = inputs['dl_number'].strip().upper()
    class_code = inputs['class_code'].strip().upper()
    rest_code = inputs['rest_code'].strip().upper() if inputs['rest_code'] else "NONE"
    end_code = inputs['end_code'].strip().upper() if inputs['end_code'] else "NONE"
    dd_code = inputs['dd_code'].strip().upper()
    dda_code = inputs['dda_code'].strip().upper()
    sex = inputs['sex'].strip()
    
    # --- 3. 清洗输入数据 - 动态隐藏字段 ---
    
    # 中间名 (DAC) - 始终可见，若为空则设为 NONE
    middle_name = inputs['middle_name'].strip().upper() if inputs['middle_name'].strip() else "NONE"
    dac_field = f"DAC{middle_name}\x0a"
    
    # 地址 (DAH) - 仅公寓号可隐藏
    apartment_num = inputs['apartment_num'].strip().upper() if inputs['apartment_num'].strip() else "NONE"
    dah_field = f"DAH{apartment_num}\x0a" if not st.session_state.get('hide_apartment_num', False) else ""
    
    # 身体特征 (DAU, DAY, DAZ, DCL, DAW) - 各自独立隐藏
    
    # DAU (身高)
    height_input = inputs['height_input']
    height = convert_height_to_inches_ui(height_input)
    height = height if not st.session_state.get('hide_height', False) else ""
    dau_field = f"DAU{height} IN\x0a" if height else ""
    
    # DAY (眼睛)
    eyes = inputs['eyes'].strip().upper() if not st.session_state.get('hide_eyes', False) else ""
    day_field = f"DAY{eyes}\x0a" if eyes else ""
    
    # DAZ (头发)
    hair = inputs['hair'].strip().upper() if not st.session_state.get('hide_hair', False) else ""
    daz_field = f"DAZ{hair}\x0a" if hair else ""
    
    # DCL (民族/分类)
    race_default = inputs['race'].strip().upper() if inputs['race'].strip() else config['race']
    race = race_default if not st.session_state.get('hide_race', False) else ""
    dcl_field = f"DCL{race}\x0a" if race else ""
    
    # DAW (体重)
    weight = inputs['weight'].strip().upper() if not st.session_state.get('hide_weight', False) else ""
    daw_field = f"DAW{weight}\x0a" if weight else "" # 暂以 \x0a 结尾

    # 审计码 (DCJ) - 独立隐藏
    audit_code = inputs['audit_code'].strip().upper() if inputs['audit_code'].strip() else "NONE"
    dcj_field_with_sep = f"DCJ{audit_code}\x0a" if not st.session_state.get('hide_audit_code', False) else ""

    # 4. 地址固定字段 (DAG, DAI, DAJ, DAK) - 始终包含
    address = inputs['address'].strip().upper()
    city = inputs['city'].strip().upper()
    zip_input = inputs['zip_input'].replace("-", "").strip().upper()
    zip_code = zip_input
    if len(zip_code) == 5: zip_code += "0000"
    
    # 5. 构造 DL 子文件 (使用元组拼接)
    
    dl_content_tuple = (
        f"DL",
        f"DAQ{dl_number}\x0a",
        f"DCS{last_name}\x0a",
        f"DDEN{first_name}\x0a",
        dac_field,                          
        f"DDFN\x0a",
        f"DAD\x0a",
        f"DDGN\x0a",
        f"DCA{class_code}\x0a",
        f"DCB{rest_code}\x0a",
        f"DCD{end_code}\x0a",
        f"DBD{iss_date}\x0a",
        f"DBB{dob}\x0a",
        f"DBA{exp_date}\x0a",
        f"DBC{sex}\x0a",
        
        # 身体特征
        dau_field,
        day_field,

        # 地址块
        f"DAG{address}\x0a",
        dah_field, # 动态 DAH
        f"DAI{city}\x0a",
        f"DAJ{jurisdiction_code}\x0a",
        f"DAK{zip_code}\x0a",
        
        # 证件/固定字段
        f"DCF{dd_code}\x0a",
        f"DCGUSA\x0a",
        f"DDA{dda_code}\x0a",
        f"DDB{rev_date}\x0a",
        
        # 结尾可选字段 (DCJ, DAZ, DCL, DAW)
        dcj_field_with_sep,
        daz_field,
        dcl_field,
        daw_field,
    )
    
    all_fields_list = [f for f in dl_content_tuple if f]
    
    # 6. 最终清理: 确保最后一个字段不以 \x0a 结尾
    if all_fields_list and all_fields_list[-1].endswith('\x0a'):
        all_fields_list[-1] = all_fields_list[-1].rstrip('\x0a')

    dl_content_body = "".join(all_fields_list)

    # 7. 清理 NONE 字段并添加子文件结束符 \x0d
    subfile_dl_final = dl_content_body.replace("NONE\x0a", "\x0a") + "\x0d"
    
    # --- 8. 动态计算头部和 Control Field ---
    
    # **核心修正 1：精确计算 Control Field 中的 len_dl**
    len_dl = len(subfile_dl_final.encode('latin-1'))
    
    control_field_len = 9
    aamva_header_prefix = f"@\x0a\x1e\x0dANSI {iin}{aamva_version}{jurisdiction_version}{num_entries}"
    header_prefix_len = 21 
    designator_len = 1 * 10 
    
    # **核心修正 2：确保总长度与 len_dl 相加**
    total_data_len = header_prefix_len + control_field_len + designator_len + len_dl
    
    control_field = f"C03{total_data_len:05d}{int(num_entries):02d}" 
    offset_dl_val = header_prefix_len + control_field_len + designator_len 
    des_dl = f"DL{offset_dl_val:04d}{len_dl:04d}"

    full_data = aamva_header_prefix + control_field + des_dl + subfile_dl_final
    
    return full_data


# ==================== 3. Streamlit 生成界面 UI ====================

def pdf417_generator_ui():
    st.title("💳 AAMVA PDF417 50-州 生成专家")
    st.caption("基于 AAMVA D20-2020 标准，**强制使用单文件 (Num Entries = 01)** 模式。")

    # --- 状态选择 ---
    jurisdictions = {v['name']: k for k, v in JURISDICTION_MAP.items()}
    sorted_names = sorted(jurisdictions.keys())
    
    default_state_name = JURISDICTION_MAP["TX"]['name']
    selected_name = st.selectbox("选择目标州/管辖区 (Jurisdiction)", 
                                 options=sorted_names,
                                 index=sorted_names.index(default_state_name))
    jurisdiction_code = jurisdictions[selected_name]
    
    st.info(f"选中的 IIN: **{JURISDICTION_MAP[jurisdiction_code]['iin']}** | 州代码: **{jurisdiction_code}** | 子文件数: **01 (强制)**")

    # --- 默认数据 ---
    default_data = {
        'first_name': 'LACEY', 'middle_name': 'LYNN', 'last_name': 'GOODING',
        'address': '8444 KALAMATH ST', 'apartment_num': 'APT B', 'city': 'FEDERAL HEIGHTS', 'zip_input': '80260',
        'dob': '09/23/1990', 'exp_date': '09/23/2026', 'iss_date': '04/20/2021', 'rev_date': '10302015',
        'dl_number': '171625540', 'class_code': 'C', 'rest_code': 'NONE', 'end_code': 'NONE',
        'dd_code': '6358522', 'audit_code': 'CDOR_DL_0_042121_06913', 'dda_code': 'F',
        'sex': '2', 'height_input': '069', 'weight': '140', 'eyes': 'BLU', 'hair': 'BRO', 'race': 'W'
    }
    if JURISDICTION_MAP[jurisdiction_code].get('race'):
        default_data['race'] = JURISDICTION_MAP[jurisdiction_code]['race']

    # ========================================================
    # 动态参数控制区 (新功能)
    # ========================================================
    
    st.subheader("⚙️ 动态参数设置")
    
    # DAH 和 DCJ 默认隐藏
    col_hide_1, col_hide_2 = st.columns(2)
    col_hide_1.checkbox("隐藏公寓号/附加地址 (DAH)", key='hide_apartment_num', value=True, help="**默认隐藏。** 移除 DAH 字段。")
    col_hide_2.checkbox("隐藏审计信息/机构代码 (DCJ)", key='hide_audit_code', value=True, help="**默认隐藏。** 移除 DCJ 字段。")
    
    # 身体特征独立控制 (DCL 默认隐藏)
    st.markdown("---")
    st.subheader("🏋️ 身体特征动态隐藏")
    col_phy_1, col_phy_2, col_phy_3, col_phy_4, col_phy_5 = st.columns(5)
    col_phy_1.checkbox("隐藏身高 (DAU)", key='hide_height', value=False)
    col_phy_2.checkbox("隐藏体重 (DAW)", key='hide_weight', value=False)
    col_phy_3.checkbox("隐藏眼睛 (DAY)", key='hide_eyes', value=False)
    col_phy_4.checkbox("隐藏头发 (DAZ)", key='hide_hair', value=False)
    col_phy_5.checkbox("隐藏民族/分类 (DCL)", key='hide_race', value=True, help="**默认隐藏。** 移除 DCL 字段。") 
    st.markdown("---")
    
    
    # --- 1. 身份信息 ---
    st.subheader("👤 身份与姓名")
    col1, col2, col3 = st.columns(3)
    inputs = {}
    inputs['last_name'] = col1.text_input("姓氏 (DCS)", default_data['last_name'])
    inputs['first_name'] = col2.text_input("名 (DDEN)", default_data['first_name'])
    # DAC: 始终可见
    inputs['middle_name'] = col3.text_input("中间名 (DAC)", default_data['middle_name'], help="此字段始终包含。如留空，数据中将使用 'NONE'。")
    
    # --- 2. 证件信息 ---
    st.subheader("💳 证件信息")
    col1, col2, col3 = st.columns(3)
    inputs['dl_number'] = col1.text_input("驾照号码 (DAQ)", default_data['dl_number'])
    inputs['class_code'] = col2.text_input("类型 (DCA)", default_data['class_code'])
    inputs['dda_code'] = col3.selectbox("REAL ID (DDA)", options=['F', 'N'], index=['F', 'N'].index(default_data['dda_code']), help="F=Real ID, N=Federal Limits Apply")
    
    col1, col2, col3 = st.columns(3)
    inputs['rest_code'] = col1.text_input("限制 (DCB)", default_data['rest_code'])
    inputs['end_code'] = col2.text_input("背书 (DCD)", default_data['end_code'])
    inputs['dd_code'] = col3.text_input("鉴别码 (DCF)", default_data['dd_code'])
    
    # DCJ 审计码输入依赖于勾选框状态
    if not st.session_state.get('hide_audit_code', False):
        inputs['audit_code'] = st.text_input("审计信息/机构代码 (DCJ)", default_data['audit_code'])
    else:
        inputs['audit_code'] = ""
        st.markdown("**审计信息/机构代码 (DCJ)**: *已隐藏/移除*")
        

    inputs['jurisdiction_code'] = jurisdiction_code # 传递动态州码

    # --- 3. 日期信息 ---
    st.subheader("📅 日期 (MMDDYYYY)")
    col1, col2, col3, col4 = st.columns(4)
    inputs['dob'] = col1.text_input("出生日期 (DBB)", default_data['dob'], help="MMDDYYYY 格式")
    inputs['iss_date'] = col2.text_input("签发日期 (DBD)", default_data['iss_date'])
    inputs['exp_date'] = col3.text_input("过期日期 (DBA)", default_data['exp_date'])
    inputs['rev_date'] = col4.text_input("版面发行日期 (DDB)", default_data['rev_date'])
    
    # --- 4. 地址信息 ---
    st.subheader("🏠 地址信息")
    
    # 街道、城市固定可见
    col1, col2, col_apt = st.columns([3, 1, 1])
    inputs['address'] = col1.text_input("街道地址 (DAG)", default_data['address'])
    inputs['city'] = col2.text_input("城市 (DAI)", default_data['city'])
    
    # DAH (公寓号) 独立控制
    if not st.session_state.get('hide_apartment_num', False):
        inputs['apartment_num'] = col_apt.text_input("公寓号/附加地址 (DAH)", default_data['apartment_num'], help="如留空，数据中将使用 'NONE'。")
    else:
        inputs['apartment_num'] = ""
        col_apt.markdown("**公寓号 (DAH)**: *已隐藏/移除*")

    # 州/国家/邮编固定可见
    col1, col2, col3 = st.columns([1, 1, 2])
    col1.text(f"州/省 (DAJ): {jurisdiction_code}") 
    col2.text(f"国家 (DCG): USA") 
    inputs['zip_input'] = col3.text_input("邮编 (DAK)", default_data['zip_input'], help="输入 5 位数字，将自动补全为 9 位。")
        
    # --- 5. 物理特征 ---
    st.subheader("🏋️ 物理特征")
    
    col_sex, col_h, col_w, col_e, col_hair = st.columns(5)
    inputs['sex'] = col_sex.selectbox("性别 (DBC)", options=['1', '2', '9'], index=['1', '2', '9'].index(default_data['sex']))
    
    # DAU (身高)
    if not st.session_state.get('hide_height', False):
        inputs['height_input'] = col_h.text_input("身高 (DAU)", default_data['height_input'], help="总英寸 (如 069) 或 feet/inches (如 509)。")
    else:
        inputs['height_input'] = ""
        col_h.markdown("**身高 (DAU)**: *已隐藏/移除*")

    # DAW (体重)
    if not st.session_state.get('hide_weight', False):
        inputs['weight'] = col_w.text_input("体重 (DAW)", default_data['weight'], help="磅 (LB)")
    else:
        inputs['weight'] = ""
        col_w.markdown("**体重 (DAW)**: *已隐藏/移除*")

    # DAY (眼睛)
    if not st.session_state.get('hide_eyes', False):
        inputs['eyes'] = col_e.text_input("眼睛颜色 (DAY)", default_data['eyes'])
    else:
        inputs['eyes'] = ""
        col_e.markdown("**眼睛 (DAY)**: *已隐藏/移除*")

    # DAZ (头发)
    if not st.session_state.get('hide_hair', False):
        inputs['hair'] = col_hair.text_input("头发颜色 (DAZ)", default_data['hair'])
    else:
        inputs['hair'] = ""
        col_hair.markdown("**头发 (DAZ)**: *已隐藏/移除*")
        
    # DCL (民族/分类)
    if not st.session_state.get('hide_race', False):
        inputs['race'] = st.text_input("民族/其他分类 (DCL)", default_data['race'], help=f"例如 {default_data['race']}")
    else:
        inputs['race'] = ""
        st.markdown("**民族/分类 (DCL)**: *已隐藏/移除*")

    st.markdown("---")
    
    # --- 6. 生成按钮 ---
    if st.button("🚀 生成 PDF417 条码", type="primary"):
        if not all([inputs['dl_number'], inputs['last_name'], inputs['dob']]):
            st.error("请输入驾照号码、姓氏和出生日期 (DOB)。")
            return

        with st.spinner("正在生成 AAMVA 数据并编码..."):
            try:
                # 核心数据生成
                aamva_data = generate_aamva_data_core(inputs)
                
                # 编码 PDF417 (使用 latin-1 编码)
                aamva_bytes = aamva_data.encode('latin-1')
                codes = encode(aamva_bytes, columns=13, security_level=5)
                # 渲染图片
                image = render_image(codes, scale=4, ratio=3, padding=10) 
                
                # 将 PIL 图像转换为字节流
                buf = io.BytesIO()
                image.save(buf, format="PNG")
                png_image_bytes = buf.getvalue()
                
                actual_len = len(aamva_bytes)
                
                # 警告检查: 检查头部声明长度是否与实际长度匹配
                c03_start_index = aamva_data.find("C03")
                
                if c03_start_index != -1:
                    header_claimed_len_str = aamva_data[c03_start_index + 3 : c03_start_index + 8] 
                    
                    try:
                        header_claimed_len = int(header_claimed_len_str)
                        if header_claimed_len != actual_len:
                            st.error(f"⚠️ **结构警告:** 头部声明长度 ({header_claimed_len} bytes) 与实际长度 ({actual_len} bytes) 不匹配。")
                        else:
                            st.success(f"✅ 条码数据生成成功！总字节长度：{actual_len} bytes")
                            
                    except ValueError:
                        st.error(f"⚠️ **结构错误:** 无法解析 Control Field 的长度部分 ('{header_claimed_len_str}')。")
                        
                else:
                    st.error("⚠️ **结构错误:** 未能在数据流中找到 Control Field (C03) 标识符。")


                # --- 结果展示 ---
                col_img, col_download = st.columns([1, 1])

                with col_img:
                    st.image(png_image_bytes, caption="PDF417 条码图像", use_column_width=True)
                
                with col_download:
                    st.download_button(
                        label="💾 下载原始 AAMVA 数据 (.txt)",
                        data=aamva_bytes,
                        file_name=f"{jurisdiction_code}_DL_RAW.txt",
                        mime="text/plain"
                    )
                    st.download_button(
                        label="🖼️ 下载条码图片 (.png)",
                        data=png_image_bytes, 
                        file_name=f"{jurisdiction_code}_PDF417.png",
                        mime="image/png"
                    )

                st.markdown("---")
                st.subheader("底层 AAMVA 数据流 (HEX/ASCII)")
                st.code(get_hex_dump_str(aamva_bytes), language='text')

            except Exception as e:
                st.error(f"生成失败：请检查输入格式是否正确。错误详情：{e}")


# ==================== 4. 网页主程序区 ====================

if __name__ == "__main__":
    pdf417_generator_ui()
