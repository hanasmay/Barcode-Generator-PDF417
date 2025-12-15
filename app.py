# -*- coding: utf-8 -*-
import streamlit as st
from PIL import Image
import io 
import math
import pandas as pd
import base64

# --- 引入外部库 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.warning("警告：PDF417 编码库 (pdf417) 未安装。条码图像功能将使用占位符。请运行 `pip install pdf417`。")
    def encode(*args, **kwargs): return []
    def render_image(*args, **kwargs): return Image.new('RGB', (400, 100), color='white')


# ==================== 0. 配置与 51 州 IIN 映射 (保持不变) ====================

JURISDICTION_MAP = {
    # ... (保持您的 JURISDICTION_MAP 不变) ...
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

st.set_page_config(page_title="AAMVA PDF417 生成专家", page_icon="💳", layout="wide")

# 注入 CSS：优化布局
st.markdown("""
    <style>
        .block-container { padding: 1rem 1rem; }
        [data-testid="stTextInput"] { width: 100%; }
        .stButton>button { width: 100%; }
        .stSelectbox { width: 100%; }
    </style>
""", unsafe_allow_html=True)


# ==================== 1. 核心辅助函数 (保持不变) ====================

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


# ==================== 2. AAMVA 生成核心逻辑 (单文件修正) ====================

def generate_aamva_data_core(inputs):
    """根据 Streamlit 输入字典，生成 AAMVA PDF417 原始数据流 (修正为单子文件 DL)"""
    
    # 1. 获取州配置
    jurisdiction_code = inputs['jurisdiction_code']
    config = JURISDICTION_MAP.get(jurisdiction_code)
    
    iin = config['iin']
    jurisdiction_version = config['jver']
    
    # 2. 清洗输入数据 (保持不变)
    first_name = inputs['first_name'].strip().upper()
    middle_name = inputs['middle_name'].strip().upper() if inputs['middle_name'] else "NONE"
    last_name = inputs['last_name'].strip().upper()
    address = inputs['address'].strip().upper()
    city = inputs['city'].strip().upper()
    zip_code = inputs['zip_input'].replace("-", "").strip().upper()
    if len(zip_code) == 5: zip_code += "0000"
    
    dob = clean_date_input(inputs['dob'])
    exp_date = clean_date_input(inputs['exp_date'])
    iss_date = clean_date_input(inputs['iss_date'])
    rev_date = clean_date_input(inputs['rev_date'])

    dl_number = inputs['dl_number'].strip().upper()
    class_code = inputs['class_code'].strip().upper()
    rest_code = inputs['rest_code'].strip().upper() if inputs['rest_code'] else "NONE"
    end_code = inputs['end_code'].strip().upper() if inputs['end_code'] else "NONE"
    dd_code = inputs['dd_code'].strip().upper()
    audit_code = inputs['audit_code'].strip().upper()
    dda_code = inputs['dda_code'].strip().upper()
    
    sex = inputs['sex'].strip()
    height = convert_height_to_inches_ui(inputs['height_input'])
    weight = inputs['weight'].strip().upper()
    eyes = inputs['eyes'].strip().upper()
    hair = inputs['hair'].strip().upper()
    race = inputs['race'].strip().upper() if inputs['race'] else config['race']
    
    # --- 3. 构造子文件 DL (AAMVA V09 核心结构) ---
    aamva_version = "09"
    
    # **核心修改 1: 子文件数量改为 1**
    num_entries = "01" 
    
    # 构造 DL 子文件内容（使用 \x0a (LF) 作为字段分隔符）
    dl_content_body = (
        f"DL"                                    
        f"DAQ{dl_number}\x0a"                      
        f"DCS{last_name}\x0a"                      
        f"DDEN{first_name}\x0a"                    
        f"DAC{middle_name}\x0a"                    
        f"DDFN\x0a"                                
        f"DAD\x0a"                                 
        f"DDGN\x0a"                                
        f"DCA{class_code}\x0a"                     
        f"DCB{rest_code}\x0a"                      
        f"DCD{end_code}\x0a"                       
        f"DBD{iss_date}\x0a"                       
        f"DBB{dob}\x0a"
        f"DBA{exp_date}\x0a"
        f"DBC{sex}\x0a"
        f"DAU{height} IN\x0a"                      
        f"DAY{eyes}\x0a"                           
        f"DAG{address}\x0a"                     
        f"DAI{city}\x0a"                           
        f"DAJ{jurisdiction_code}\x0a"              
        f"DAK{zip_code}\x0a"                       
        f"DCF{dd_code}\x0a"                         
        f"DCGUSA\x0a"                              
        f"DDA{dda_code}\x0a"
        f"DDB{rev_date}\x0a"                       
        f"DAZ{hair}\x0a"                           
        f"DCJ{audit_code}\x0a"                     
        f"DCL{race}\x0a"                           
        f"DAW{weight}"                             
    )
    
    # 清理空字段，并最终拼接 DL 子文件。用 \x0d (CR) 结束 DL 文件
    subfile_dl_final = dl_content_body.replace("NONE\x0a", "\x0a").replace("  ", " ").replace("\x0a\x0a", "\x0a") + "\x0d"

    # **核心修改 2: 移除 ZC 子文件**
    # subfile_zc_final = f"ZC{f'ZCAC'}\x0d" 

    # --- 4. 动态计算头部和偏移量 (关键修正) ---
    
    # DL 文件的实际长度
    len_dl = len(subfile_dl_final.encode('latin-1'))
    
    # Header Control Field (C03XXXXXX) 的固定长度
    control_field_len = 9 
    
    # AAMVA Header (固定长度)
    aamva_header_prefix = f"@\x0a\x1e\x0dANSI {iin}{aamva_version}{jurisdiction_version}{num_entries}"
    aamva_header_len = 21 
    
    # **核心修改 3: Designator 长度改为 1 个 (10 字节)**
    designator_len = 1 * 10 
    
    # Total File Length (C03XX)
    # 总长度 = Header Prefix (21) + Control Field (9) + Designator (10) + DL Content 
    total_data_len = aamva_header_len + control_field_len + designator_len + len_dl
    
    # Offset of DL file: DL 文件在 Designator 之后开始
    offset_dl_val = aamva_header_len + control_field_len + designator_len 
    
    # --- 5. 构造最终 Designator 和 Header ---
    
    # 构造 Control Field (C03XXXXXX)
    control_field = f"C03{total_data_len:05d}{int(num_entries):02d}" 
    
    # 构造 Designator (类型 + 偏移量 + 长度)
    des_dl = f"DL{offset_dl_val:04d}{len_dl:04d}"
    
    # 最终拼接: Header Prefix + Control Field + Designator (仅 DL) + Subfile (仅 DL)
    return aamva_header_prefix + control_field + des_dl + subfile_dl_final


# ==================== 3. Streamlit 生成界面 UI (保持不变) ====================

def pdf417_generator_ui():
    st.title("💳 AAMVA PDF417 数据生成专家")
    st.caption("基于 AAMVA D20-2020 标准，修正为**单子文件 DL (Num Entries = 01)** 模式。")

    # --- 状态选择 ---
    jurisdictions = {v['name']: k for k, v in JURISDICTION_MAP.items()}
    sorted_names = sorted(jurisdictions.keys())
    
    default_state_name = JURISDICTION_MAP["CO"]['name'] # 默认科罗拉多州
    selected_name = st.selectbox("选择目标州/管辖区 (Jurisdiction)", 
                                 options=sorted_names,
                                 index=sorted_names.index(default_state_name))
    jurisdiction_code = jurisdictions[selected_name]
    
    st.info(f"选中的 IIN: **{JURISDICTION_MAP[jurisdiction_code]['iin']}** | 州代码: **{jurisdiction_code}** | 子文件数: **01**")

    # --- 默认数据 (保持不变) ---
    default_data = {
        'first_name': 'LACEY', 'middle_name': 'LYNN', 'last_name': 'GOODING',
        'address': '8444 KALAMATH ST', 'city': 'FEDERAL HEIGHTS', 'zip_input': '80260',
        'dob': '09/23/1990', 'exp_date': '09/23/2026', 'iss_date': '04/20/2021', 'rev_date': '10302015',
        'dl_number': '171625540', 'class_code': 'R', 'rest_code': 'C', 'end_code': 'NONE',
        'dd_code': '6358522', 'audit_code': 'CDOR_DL_0_042121_06913', 'dda_code': 'F',
        'sex': '2', 'height_input': '069', 'weight': '140', 'eyes': 'BLU', 'hair': 'BRO', 'race': 'CLW'
    }
    
    if JURISDICTION_MAP[jurisdiction_code].get('race'):
        default_data['race'] = JURISDICTION_MAP[jurisdiction_code]['race']

    # --- 1. 身份信息 ---
    st.subheader("👤 身份与姓名")
    col1, col2, col3 = st.columns(3)
    inputs = {}
    inputs['last_name'] = col1.text_input("姓氏 (DCS)", default_data['last_name'])
    inputs['first_name'] = col2.text_input("名 (DDEN)", default_data['first_name'])
    inputs['middle_name'] = col3.text_input("中间名 (DAC)", default_data['middle_name'])
    
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
    
    inputs['audit_code'] = st.text_input("审计信息/机构代码 (DCJ)", default_data['audit_code'])
    inputs['jurisdiction_code'] = jurisdiction_code 

    # --- 3. 日期信息 ---
    st.subheader("📅 日期 (MMDDYYYY)")
    col1, col2, col3, col4 = st.columns(4)
    inputs['dob'] = col1.text_input("出生日期 (DBB)", default_data['dob'], help="MMDDYYYY 格式")
    inputs['iss_date'] = col2.text_input("签发日期 (DBD)", default_data['iss_date'])
    inputs['exp_date'] = col3.text_input("过期日期 (DBA)", default_data['exp_date'])
    inputs['rev_date'] = col4.text_input("版面发行日期 (DDB)", default_data['rev_date'])
    
    # --- 4. 地址信息 ---
    st.subheader("🏠 地址信息")
    col1, col2 = st.columns([3, 1])
    inputs['address'] = col1.text_input("街道地址 (DAG)", default_data['address'])
    inputs['city'] = col2.text_input("城市 (DAI)", default_data['city'])
    
    col1, col2, col3 = st.columns([1, 1, 2])
    col1.text(f"州/省 (DAJ): {jurisdiction_code}") 
    col2.text(f"国家 (DCG): USA") 
    inputs['zip_input'] = col3.text_input("邮编 (DAK)", default_data['zip_input'], help="输入 5 位数字，将自动补全为 9 位。")
    
    # --- 5. 物理特征 ---
    st.subheader("🏋️ 物理特征")
    col1, col2, col3, col4, col5 = st.columns(5)
    inputs['sex'] = col1.selectbox("性别 (DBC)", options=['1', '2', '9'], index=['1', '2', '9'].index(default_data['sex']))
    inputs['height_input'] = col2.text_input("身高 (DAU)", default_data['height_input'], help="总英寸 (如 069) 或 feet/inches (如 509)。")
    inputs['weight'] = col3.text_input("体重 (DAW)", default_data['weight'], help="磅 (LB)")
    inputs['eyes'] = col4.text_input("眼睛颜色 (DAY)", default_data['eyes'])
    inputs['hair'] = col5.text_input("头发颜色 (DAZ)", default_data['hair'])
    inputs['race'] = st.text_input("民族/其他分类 (DCL)", default_data['race'], help=f"例如 {default_data['race']}")

    st.markdown("---")
    
    # --- 6. 生成按钮 ---
    if st.button("🚀 生成 PDF417 条码", type="primary"):
        if not all([inputs['dl_number'], inputs['last_name'], inputs['dob']]):
            st.error("请输入驾照号码、姓氏和出生日期 (DOB)。")
            return

        with st.spinner("正在生成 AAMVA 数据并编码..."):
            try:
                aamva_data = generate_aamva_data_core(inputs)
                
                aamva_bytes = aamva_data.encode('latin-1')
                codes = encode(aamva_bytes, columns=13, security_level=5)
                
                image = render_image(codes, scale=4, ratio=3, padding=10) 
                
                buf = io.BytesIO()
                image.save(buf, format="PNG")
                png_image_bytes = buf.getvalue()
                
                actual_len = len(aamva_bytes)
                st.success(f"✅ 条码数据生成成功！总字节长度：{actual_len} bytes")

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
