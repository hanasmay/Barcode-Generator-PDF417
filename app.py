# -*- coding: utf-8 -*-
import streamlit as st
import io
from PIL import Image

# --- 1. 依赖库加载 ---
try:
    from pdf417 import encode, render_image
except ImportError:
    st.error("缺失依赖库！请确保在 requirements.txt 中包含了 pdf417 和 Pillow")

# ==================== 2. AAMVA 50 州 IIN 数据库 ====================
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

# ==================== 3. 核心数据构建逻辑 ====================

def build_aamva_stream(inputs, options):
    iin = JURISDICTION_MAP[inputs['state']]
    # 锁死参数：AAMVA 09, JUR 00, Entry 01
    aamva_ver, jur_ver, num_entries = "09", "00", "01"

    body = [
        f"DAQ{inputs['dl_number']}\x0a",
        f"DCS{inputs['last_name']}\x0a",
        f"DDEN{inputs['first_name']}\x0a",
        f"DAC{inputs['middle_name']}\x0a",
        f"DDFN\x0aDAD\x0aDDGN\x0a",
        f"DCA{inputs['class']}\x0a",
        f"DBD{inputs['iss_date']}\x0a",
        f"DBB{inputs['dob']}\x0a",
        f"DBA{inputs['exp_date']}\x0a",
        f"DBC{inputs['sex']}\x0a"
    ]
    
    if not options['hide_height']: 
        body.append(f"DAU{inputs['height']} in\x0a")
    
    body.append(f"DAY{inputs['eyes']}\x0a")
    body.append(f"DAG{inputs['address']}\x0a")
    body.append(f"DAI{inputs['city']}\x0a")
    body.append(f"DAJ{inputs['state']}\x0a")
    
    zip_val = inputs['zip'].replace("-", "")
    if len(zip_val) == 5: zip_val += "0000"
    body.append(f"DAK{zip_val}  \x0a")
    body.append(f"DCF{inputs['dd_code']}\x0a")
    body.append(f"DCGUSA\x0aDDAF\x0a")
    body.append(f"DDB{inputs['rev_date']}\x0a")
    body.append(f"DDD1\x0a")
    
    if not options['hide_audit']: 
        body.append(f"DCJ{inputs['audit']}\x0a")
        
    body.append(f"DCU")

    # 计算子文件长度
    subfile_str = "DL" + "".join(body) + "\x0d"
    subfile_bytes = subfile_str.encode('latin-1')
    len_dl = len(subfile_bytes)

    # 组装 AAMVA 头部 (固定偏移 32)
    header_prefix = f"@\x0a\x1e\x0dANSI {iin}{aamva_ver}{jur_ver}{num_entries}"
    designator = f"DL0032{len_dl:04d}"
    
    return header_prefix.encode('latin-1') + designator.encode('latin-1') + b"\x0d" + subfile_bytes

# ==================== 4. 主界面布局 ====================

def main():
    st.set_page_config(page_title="PDF417 条码专家", layout="wide")
    st.markdown("<h2 style='text-align: center;'>PDF417 AAMVA 条码在线生成器</h2>", unsafe_allow_html=True)
    st.markdown("---")

    # 1. 侧边栏：配置参数
    with st.sidebar:
        st.subheader("⚙️ 全局配置")
        target_state = st.selectbox("选择州 (Jurisdiction)", list(JURISDICTION_MAP.items()), format_func=lambda x: x[0], index=47)[0]
        st.info(f"IIN: {JURISDICTION_MAP[target_state]} | 模式: 09/00/01")
        
        st.markdown("---")
        st.subheader("显示控制")
        hide_h = st.checkbox("隐藏身高 (DAU)", False)
        hide_a = st.checkbox("隐藏审计码 (DCJ)", True)
        options = {'hide_height': hide_h, 'hide_audit': hide_a}
        
        col_count = st.slider("条码列数 (Columns)", 9, 20, 13)

    # 2. 主界面：输入表单
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            ln = st.text_input("姓 (DCS)", "SOLOMON")
            fn = st.text_input("名 (DAC)", "DANIEL")
            mn = st.text_input("中间名", "NONE")
            dl = st.text_input("证件号 (DAQ)", "WDL0ALXD2K1B")
            sex = st.selectbox("性别", ["1", "2"], format_func=lambda x: "男 (1)" if x=="1" else "女 (2)")
        with col2:
            dob = st.text_input("生日 (MMDDYYYY)", "08081998")
            iss = st.text_input("签发日", "06062024")
            exp = st.text_input("过期日", "08082030")
            rev = st.text_input("版面日期", "11122019")
            dd_code = st.text_input("鉴别码 (DCF)", "WDL0ALXD2K1BA020424988483")

        st.markdown("#### 详细地址与特征")
        if not options['hide_height']:
            a1, a2, a3, a4 = st.columns([2, 1, 1, 1])
            addr = a1.text_input("街道地址 (DAG)", "29810 224TH AVE SE")
            city_v = a2.text_input("城市 (DAI)", "KENT")
            zip_v = a3.text_input("邮编 (DAK)", "98010")
            h_val = a4.text_input("身高 (英寸)", "072")
        else:
            a1, a2, a3 = st.columns([2, 1, 1])
            addr = a1.text_input("街道地址 (DAG)", "29810 224TH AVE SE")
            city_v = a2.text_input("城市 (DAI)", "KENT")
            zip_v = a3.text_input("邮编 (DAK)", "98010")
            h_val = "000"

        if not options['hide_audit']:
            audit_val = st.text_input("审计码 (DCJ)", "A020424988483")
        else:
            audit_val = ""

    # 3. 生成与分析区域
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 生成 AAMVA 条码并分析数据", type="primary", use_container_width=True):
        inputs = {
            'state': target_state, 'last_name': ln, 'first_name': fn, 'middle_name': mn,
            'dl_number': dl, 'dob': dob, 'iss_date': iss, 'exp_date': exp,
            'rev_date': rev, 'sex': sex, 'address': addr, 'city': city_v,
            'zip': zip_v, 'height': h_val, 'eyes': 'BLU', 'class': 'NONE',
            'dd_code': dd_code, 'audit': audit_val
        }
        
        try:
            raw_data = build_aamva_stream(inputs, options)
            
            st.markdown("---")
            res_col, data_col = st.columns([1, 1])
            
            with res_col:
                st.subheader("📊 条码预览")
                codes = encode(raw_data, columns=col_count, security_level=5)
                img = render_image(codes, scale=3)
                st.image(img)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.download_button("💾 下载图片 (PNG)", buf.getvalue(), f"{target_state}_DL.png", use_container_width=True)

            with data_col:
                st.subheader("📄 明文数据分析")
                # 解码为明文，不显示控制字符占位符
                plain_text = raw_data.decode('latin-1')
                st.text_area("原始明文流 (Plain Text):", value=plain_text, height=200)
                
                st.subheader("🔢 十六进制 (HEX)")
                hex_str = raw_data.hex().upper()
                st.code("\n".join([hex_str[i:i+32] for i in range(0, len(hex_str), 32)]), language="text")

        except Exception as e:
            st.error(f"生成失败: {e}")

if __name__ == "__main__":
    main()
