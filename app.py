# -*- coding: utf-8 -*-
import streamlit as st
import io
import re
from PIL import Image

# --- 依赖库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请确保在 requirements.txt 中包含了 pdf417 和 Pillow")

# ==================== 1. AAMVA 50 州 IIN 数据库 ====================
JURISDICTION_MAP = {
    "AL": "636033", "AK": "636059", "AZ": "636026", "AR": "636021", "CA": "636014",
    "CO": "636020", "CT": "636006", "DE": "636011", "DC": "636043", "FL": "636010",
    "GA": "636055", "HI": "636047", "ID": "636050", "IL": "636035", "IN": "636037",
    "IA": "636018", "KS": "636022", "KY": "636046", "LA": "636007", "ME": "636041",
    "MD": "636003", "MA": "636002", "MI": "636032", "MN": "636038", "MS": "636051",
    "MO": "636030", "MT": "636008", "NE": "636054", "NV": "636049", "NH": "636039",
    "NJ": "636036", "NM": "636009", "NY": "636001", "NC": "636004", "ND": "636034",
    "OH": "636023", "OK": "636058", "OR": "636029", "PA": "636025", "RI": "636052",
    "SC": "636005", "SD": "636042", "TN": "636053", "TX": "636015", "UT": "636040",
    "VT": "636024", "VA": "636000", "WA": "636045", "WV": "636061", "WI": "636031", "WY": "636060"
}

# ==================== 2. 辅助工具函数 ====================

def clean_date(date_str):
    """移除日期中的斜杠或横杠，仅保留数字"""
    return re.sub(r'[^0-9]', '', date_str)

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    aamva_ver, jur_ver, num_entries = "09", "00", "01"

    # 构建主体数据体
    body = [
        f"DAQ{inputs['dl_number'].upper()}\x0a",
        f"DCS{inputs['last_name'].upper()}\x0a",
        f"DDEN{inputs['first_name'].upper()}\x0a",
        f"DAC{inputs['middle_name'].upper()}\x0a",
        f"DDFN\x0aDAD\x0aDDGN\x0a",
        f"DCA{inputs['class'].upper()}\x0a",
        f"DBD{clean_date(inputs['iss_date'])}\x0a",
        f"DBB{clean_date(inputs['dob'])}\x0a",
        f"DBA{clean_date(inputs['exp_date'])}\x0a",
        f"DBC{inputs['sex']}\x0a"
    ]
    
    # 动态字段控制
    if not options['hide_height']: 
        body.append(f"DAU{inputs['height']} in\x0a")
    if not options['hide_weight']:
        body.append(f"DAW{inputs['weight']}\x0a")
    if not options['hide_eyes']:
        body.append(f"DAY{inputs['eyes'].upper()}\x0a")
    if not options['hide_hair']:
        body.append(f"DAZ{inputs['hair'].upper()}\x0a")
    
    body.append(f"DAG{inputs['address'].upper()}\x0a")
    body.append(f"DAI{inputs['city'].upper()}\x0a")
    body.append(f"DAJ{inputs['state']}\x0a")
    
    zip_val = clean_date(inputs['zip'])
    if len(zip_val) == 5: zip_val += "0000"
    body.append(f"DAK{zip_val}  \x0a")
    
    body.append(f"DCF{inputs['dd_code'].upper()}\x0a")
    body.append(f"DCGUSA\x0aDDAF\x0a")
    body.append(f"DDB{clean_date(inputs['rev_date'])}\x0a")
    body.append(f"DDD1\x0a")
    
    # REAL ID 标志
    body.append(f"DDA{'F' if inputs['is_real_id'] else 'N'}\x0a")
    
    if not options['hide_audit']: 
        body.append(f"DCJ{inputs['audit'].upper()}\x0a")
        
    body.append(f"DCU")

    subfile_str = "DL" + "".join(body) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    len_dl = len(subfile_bytes)

    header_prefix = f"@\x0a\x1e\x0dANSI {iin}{aamva_ver}{jur_ver}{num_entries}"
    designator = f"DL0032{len_dl:04d}"
    
    return header_prefix.encode('latin-1') + designator.encode('latin-1') + b"\x0d" + subfile_bytes

# ==================== 3. Streamlit UI 界面 ====================

def main():
    st.set_page_config(page_title="AAMVA 终极生成器", layout="wide")
    st.title("💳 AAMVA PDF417 50-州 终极生成器")
    st.caption("版本：2025.12 | 自动大写 | 自动清理日期 | 动态字段控制")

    with st.sidebar:
        st.subheader("⚙️ 侧边栏控制")
        target_state = st.selectbox("选择州", list(JURISDICTION_MAP.keys()), index=47)
        
        st.markdown("---")
        st.subheader("🙈 字段隐藏开关")
        hide_h = st.checkbox("隐藏身高 (DAU)", False)
        hide_w = st.checkbox("隐藏体重 (DAW)", False)
        hide_e = st.checkbox("隐藏眼色 (DAY)", False)
        hide_hair = st.checkbox("隐藏发色 (DAZ)", False)
        hide_a = st.checkbox("隐藏审计码 (DCJ)", True)
        
        options = {
            'hide_height': hide_h, 'hide_weight': hide_w, 
            'hide_eyes': hide_e, 'hide_hair': hide_hair, 'hide_audit': hide_a
        }
        
        st.markdown("---")
        col_count = st.slider("条码列数", 9, 20, 13)

    # 第一行：身份与日期
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👤 身份信息")
        ln = st.text_input("姓 (Last Name)", "SOLOMON").upper()
        fn = st.text_input("名 (First Name)", "DANIEL").upper()
        mn = st.text_input("中间名", "NONE").upper()
        dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B").upper()
        real_id = st.toggle("符合 REAL ID 标准 (DDA)", value=True)

    with c2:
        st.subheader("📅 关键日期 (支持斜杠格式)")
        dob = st.text_input("生日 (MMDDYYYY)", "08/08/1998")
        iss = st.text_input("签发日", "06/06/2024")
        exp = st.text_input("过期日", "08/08/2030")
        rev = st.text_input("版面发行日期", "11/12/2019")
        sex = st.selectbox("性别", ["1", "2"], format_func=lambda x: "男 (1)" if x=="1" else "女 (2)")

    # 第二行：地址与物理特征
    st.markdown("---")
    st.subheader("🏠 地址与物理特征")
    
    # 动态列排布
    addr_cols = st.columns(3)
    addr = addr_cols[0].text_input("街道地址 (DAG)", "29810 224TH AVE SE").upper()
    city = addr_cols[1].text_input("城市 (DAI)", "KENT").upper()
    zip_c = addr_cols[2].text_input("邮编 (DAK)", "98010")

    # 动态物理特征行
    phys_cols = st.columns(4)
    active_idx = 0
    
    h_val = "072"
    if not options['hide_height']:
        h_val = phys_cols[active_idx].text_input("身高 (英寸)", "072")
        active_idx += 1
    
    w_val = "175"
    if not options['hide_weight']:
        w_val = phys_cols[active_idx % 4].text_input("体重 (lb)", "175")
        active_idx += 1
        
    e_val = "BLU"
    if not options['hide_eyes']:
        e_val = phys_cols[active_idx % 4].text_input("眼色 (如 BLU)", "BLU").upper()
        active_idx += 1

    hair_val = "BRO"
    if not options['hide_hair']:
        hair_val = phys_cols[active_idx % 4].text_input("发色 (如 BRO)", "BRO").upper()
        active_idx += 1

    st.markdown("---")
    dd = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483").upper()
    audit_val = ""
    if not options['hide_audit']:
        audit_val = st.text_input("审计码 (DCJ)", "A020424988483").upper()

    if st.button("🚀 生成条码并分析", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'dob': dob, 'iss_date': iss, 'exp_date': exp,
            'rev_date': rev, 'sex': sex, 'address': addr, 'city': city,
            'zip': zip_c, 'height': h_val, 'weight': w_val, 'eyes': e_val, 
            'hair': hair_val, 'is_real_id': real_id, 'class': 'NONE',
            'dd_code': dd, 'audit': audit_val
        }
        
        try:
            raw_data = build_aamva_stream(inputs, options)
            res_c, data_c = st.columns([1, 1])
            
            with res_c:
                st.subheader("📊 条码预览")
                codes = encode(raw_data, columns=col_count, security_level=5)
                img = render_image(codes, scale=3)
                st.image(img)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("💾 下载图片", buf.getvalue(), f"{target_state}_DL.png", use_container_width=True)

            with data_c:
                st.subheader("📄 明文与 HEX 分析")
                st.text_area("原始明文流:", value=raw_data.decode('latin-1'), height=150)
                st.code("\n".join([(raw_data.hex().upper())[i:i+32] for i in range(0, len(raw_data.hex()), 32)]), language="text")

        except Exception as e:
            st.error(f"发生错误: {e}")

if __name__ == "__main__":
    main()
