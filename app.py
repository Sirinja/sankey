import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Sankey Rotation", layout="wide")
st.title("📊 Sankey Diagram - การโยกย้ายบุคลากร")

PALETTE = ["#005CAB", "#00AEEF", "#78BE20", "#002D72", "#6C757D"]

def repeat_palette(palette, n):
    k = (n // len(palette)) + 1
    return (palette * k)[:n]

def hex_to_rgba(hex_color: str, alpha: float = 0.45) -> str:
    c = hex_color.lstrip("#")
    r, g, b = (int(c[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"

def hex_luminance(hex_color: str) -> float:
    c = hex_color.lstrip("#")
    r, g, b = [int(c[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    def lin(x): return x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4
    r, g, b = lin(r), lin(g), lin(b)
    return 0.2126*r + 0.7152*g + 0.0722*b

def choose_font_color(node_colors):
    dark_ratio = sum(1 for c in node_colors if hex_luminance(c) < 0.5) / max(len(node_colors), 1)
    return "white" if dark_ratio >= 0.6 else "black"

uploaded = st.file_uploader("อัปโหลดไฟล์ Excel", type=["xlsx"])

if not uploaded:
    st.info("อัปโหลดไฟล์ Excel (.xlsx) เพื่อเริ่มต้น")
    st.stop()

try:
    xls = pd.ExcelFile(uploaded)
    sheet = st.selectbox("เลือกชีต", xls.sheet_names, index=min( xls.sheet_names.index("ตารางรายละเอียด") if "ตารางรายละเอียด" in xls.sheet_names else 0, len(xls.sheet_names)-1))
    header_row = st.number_input("แถวหัวตาราง (เริ่มที่ 0)", min_value=0, value=2, step=1)
    data = pd.read_excel(xls, sheet_name=sheet, header=header_row)
    if data.empty:
        st.warning("ชีตนี้ไม่มีข้อมูลหลังอ่านด้วยแถวหัวที่กำหนด ลองเปลี่ยนค่าแถวหัวตาราง")
        st.stop()

    # เดาคอลัมน์ที่น่าจะใช่
    def guess(prefix, default=None):
        for c in data.columns:
            if str(c).strip().startswith(prefix):
                return c
        return default

    col_old_default  = guess("ส่วนงานเดิม", data.columns[0])
    col_new_default  = guess("ส่วนงานใหม่", data.columns[min(1, len(data.columns)-1)])
    col_name_default = guess("คำนำหน้า", data.columns[min(2, len(data.columns)-1)])

    # ให้ผู้ใช้เลือกคอลัมน์
    COL_OLD  = st.selectbox("คอลัมน์ฝ่ายเดิม", options=list(data.columns), index=list(data.columns).index(col_old_default))
    COL_NEW  = st.selectbox("คอลัมน์ฝ่ายใหม่", options=list(data.columns), index=list(data.columns).index(col_new_default))
    COL_NAME = st.selectbox("คอลัมน์ชื่อบุคคล (ใช้ในโหมดแสดงชื่อ)", options=list(data.columns), index=list(data.columns).index(col_name_default))

    # ทำความสะอาดเบื้องต้น
    df = data[[COL_OLD, COL_NEW, COL_NAME]].copy()
    for c in [COL_OLD, COL_NEW, COL_NAME]:
        df[c] = df[c].astype(str).str.strip()
    df = df.replace({"": pd.NA}).dropna(subset=[COL_OLD, COL_NEW])

    if df.empty:
        st.warning("ไม่มีข้อมูลที่ทั้งฝ่ายเดิมและฝ่ายใหม่ไม่ว่าง")
        st.stop()

    # Filters
    c1, c2 = st.columns(2)
    with c1:
        sel_old = st.multiselect("เลือกฝ่ายเดิม", sorted(df[COL_OLD].unique()), default=sorted(df[COL_OLD].unique()))
    with c2:
        sel_new = st.multiselect("เลือกฝ่ายใหม่", sorted(df[COL_NEW].unique()), default=sorted(df[COL_NEW].unique()))

    df = df[df[COL_OLD].isin(sel_old) & df[COL_NEW].isin(sel_new)]
    if df.empty:
        st.warning("ไม่มีข้อมูลหลังกรองฝ่ายเดิม/ฝ่ายใหม่")
        st.stop()

    mode = st.radio("โหมดแสดงผล", ["ซ่อนชื่อ (ระดับฝ่าย)", "แสดงชื่อบุคคล"], horizontal=True)

    if mode == "ซ่อนชื่อ (ระดับฝ่าย)":
        flows = df.groupby([COL_OLD, COL_NEW], as_index=False).size().rename(columns={"size": "count"})
        if flows.empty:
            st.warning("ไม่มีคู่โยกย้ายสำหรับวาด Sankey")
            st.stop()

        left_order  = list(flows.groupby(COL_OLD)["count"].sum().sort_values(ascending=False).index)
        right_order = list(flows.groupby(COL_NEW)["count"].sum().sort_values(ascending=False).index)

        left_index  = {name: i for i, name in enumerate(left_order)}
        right_index = {name: i + len(left_order) for i, name in enumerate(right_order)}
        labels      = left_order + right_order

        sources = [left_index[o] for o in flows[COL_OLD]]
        targets = [right_index[n] for n in flows[COL_NEW]]
        values  = flows["count"].astype(int).tolist()

        node_colors = repeat_palette(PALETTE, len(labels))
        link_colors = [hex_to_rgba(node_colors[s], 0.45) for s in sources]
        font_color  = choose_font_color(node_colors)

        fig = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                label=labels, pad=18, thickness=18,
                color=node_colors,
                line=dict(color="rgba(0,0,0,0.25)", width=0.5),
                font=dict(color=font_color, size=14),
                hovertemplate="%{label}<extra></extra>"
            ),
            link=dict(
                source=sources, target=targets, value=values,
                color=link_colors,
                hovertemplate=(
                    COL_OLD + ": %{source.label}<br>"
                    + COL_NEW + ": %{target.label}<br>"
                    + "จำนวน: %{value}<extra></extra>"
                )
            )
        )])

    else:
        # แสดงชื่อบุคคล (ค่าลิงก์=1)
        d = df.dropna(subset=[COL_NAME]).copy()
        if d.empty:
            st.warning("คอลัมน์ชื่อบุคคลว่างทั้งหมด ไม่สามารถแสดงโหมดแสดงชื่อได้")
            st.stop()

        d["left_label"] = d[COL_OLD] + " : " + d[COL_NAME]
        sources_lbl = d["left_label"]
        targets_lbl = d[COL_NEW]
        values      = [1] * len(d)

        all_nodes = pd.Index(pd.concat([sources_lbl, targets_lbl]).unique())
        node_idx  = {name: i for i, name in enumerate(all_nodes)}

        source_ids = [node_idx[s] for s in sources_lbl]
        target_ids = [node_idx[t] for t in targets_lbl]

        node_colors = repeat_palette(PALETTE, len(all_nodes))
        link_colors = [hex_to_rgba(node_colors[s], 0.35) for s in source_ids]
        font_color  = choose_font_color(node_colors)

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                label=all_nodes.tolist(), pad=18, thickness=18,
                color=node_colors,
                line=dict(color="rgba(0,0,0,0.25)", width=0.5),
                font=dict(color=font_color, size=14),
                hovertemplate="%{label}<extra></extra>"
            ),
            link=dict(
                source=source_ids, target=target_ids, value=values,
                color=link_colors,
                hovertemplate=(
                    COL_OLD + ": %{source.label}<br>"
                    + COL_NEW + ": %{target.label}<extra></extra>"
                )
            )
        )])

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error("เกิดข้อผิดพลาดในการประมวลผลไฟล์ กรุณาตรวจสอบว่าเลือกชีต/แถวหัว/คอลัมน์ถูกต้อง")
    st.exception(e)  # แสดงรายละเอียดในหน้าแอปเพื่อดีบั๊กได้ทันที
