import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ======================
# Config & Theme (NHSO)
# ======================
st.set_page_config(page_title="Sankey Rotation – NHSO Theme", layout="wide")
st.title("📊 Sankey Diagram – การโยกย้ายบุคลากร (NHSO Theme)")

# NHSO brand palette
NHSO_COLORS = [
    "#005CAB",  # ฟ้าเข้ม
    "#00AEEF",  # ฟ้าอ่อน
    "#78BE20",  # เขียว
    "#002D72",  # น้ำเงินเข้ม
    "#6C757D",  # เทา
]

def repeat_palette(palette, n):
    k = (n // len(palette)) + 1
    return (palette * k)[:n]

def hex_to_rgba(hex_color: str, alpha: float = 0.45) -> str:
    c = hex_color.lstrip("#")
    r, g, b = (int(c[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"

# ======================
# Core Sankey builders
# ======================
def sankey_departments(df, col_old, col_new, title="ซ่อนชื่อ (ระดับฝ่าย) – NHSO Theme"):
    flows = (
        df.groupby([col_old, col_new], as_index=False)
          .size()
          .rename(columns={"size": "count"})
    )

    # Sort
    left_order  = list(flows.groupby(col_old)["count"].sum().sort_values(ascending=False).index)
    right_order = list(flows.groupby(col_new)["count"].sum().sort_values(ascending=False).index)

    left_idx  = {name: i for i, name in enumerate(left_order)}
    right_idx = {name: i + len(left_order) for i, name in enumerate(right_order)}
    labels    = left_order + right_order

    flows_sorted = (
        flows.assign(
            _l=flows[col_old].map({k: i for i, k in enumerate(left_order)}),
            _r=flows[col_new].map({k: i for i, k in enumerate(right_order)}),
        )
        .sort_values(["_l", "_r"])
    )

    sources = [left_idx[o]  for o in flows_sorted[col_old]]
    targets = [right_idx[n] for n in flows_sorted[col_new]]
    values  = flows_sorted["count"].tolist()

    node_colors = repeat_palette(NHSO_COLORS, len(labels))
    link_colors = [hex_to_rgba(node_colors[s], 0.45) for s in sources]

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=18, thickness=18,
            label=labels,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>"
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            hovertemplate=(
                col_old + ": %{source.label}<br>"
                + col_new + ": %{target.label}<br>"
                + "จำนวน: %{value}<extra></extra>"
            )
        ),
    )])

    fig.update_layout(title=title, font=dict(size=12))
    return fig

def sankey_with_names(df, col_old, col_new, col_name, title="แสดงชื่อบุคคล – NHSO Theme"):
    d = df.dropna(subset=[col_name]).copy()
    d["left_label"] = d[col_old] + " : " + d[col_name]

    sources_lbl = d["left_label"]
    targets_lbl = d[col_new]
    values      = [1] * len(d)

    all_nodes = pd.Index(pd.concat([sources_lbl, targets_lbl]).unique())
    node_idx  = {name: i for i, name in enumerate(all_nodes)}

    sources = [node_idx[s] for s in sources_lbl]
    targets = [node_idx[t] for t in targets_lbl]

    node_colors = repeat_palette(NHSO_COLORS, len(all_nodes))
    link_colors = [hex_to_rgba(node_colors[s], 0.35) for s in sources]

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=18, thickness=18,
            label=all_nodes.tolist(),
            color=node_colors,
            hovertemplate="%{label}<extra></extra>"
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            hovertemplate=(
                col_old + ": %{source.label}<br>"
                + col_new + ": %{target.label}<extra></extra>"
            )
        ),
    )])

    fig.update_layout(title=title, font=dict(size=12))
    return fig

# ======================
# UI – Upload & Options
# ======================
uploaded = st.file_uploader("อัปโหลดไฟล์ Excel", type=["xlsx"])
if not uploaded:
    st.info("อัปโหลดไฟล์ Excel เพื่อเริ่มต้นใช้งานครับ (รองรับ .xlsx)")
    st.stop()

c_sheet, c_header = st.columns([2,1])
with c_sheet:
    SHEET = st.text_input("ชื่อชีต (ค่าเริ่มต้น: ตารางรายละเอียด)", value="ตารางรายละเอียด")
with c_header:
    HEADER_ROW = st.number_input("แถวหัวตาราง (เริ่มที่ 0)", min_value=0, value=2, step=1)

data = pd.read_excel(uploaded, sheet_name=SHEET, header=HEADER_ROW)

def guess_col(prefix: str, fallback: str = None):
    for c in data.columns:
        if str(c).strip().startswith(prefix):
            return c
    return fallback or data.columns[0]

COL_OLD  = st.selectbox("คอลัมน์ฝ่ายเดิม", options=list(data.columns),
                        index=list(data.columns).index("ส่วนงานเดิม") if "ส่วนงานเดิม" in data.columns else 0)
COL_NEW  = st.selectbox("คอลัมน์ฝ่ายใหม่", options=list(data.columns),
                        index=list(data.columns).index(guess_col("ส่วนงานใหม่")) if guess_col("ส่วนงานใหม่") in data.columns else 0)
COL_NAME = st.selectbox("คอลัมน์ชื่อบุคคล", options=list(data.columns),
                        index=list(data.columns).index("คำนำหน้า ชื่อ - สกุล") if "คำนำหน้า ชื่อ - สกุล" in data.columns else 0)

base_df = data[[COL_OLD, COL_NEW, COL_NAME]].dropna(subset=[COL_OLD, COL_NEW]).copy()

# Multi-select filters
c1, c2 = st.columns(2)
with c1:
    sel_old = st.multiselect("เลือกฝ่ายเดิม (หลายรายการได้)", sorted(base_df[COL_OLD].unique()),
                             default=sorted(base_df[COL_OLD].unique()))
with c2:
    sel_new = st.multiselect("เลือกฝ่ายใหม่ (หลายรายการได้)", sorted(base_df[COL_NEW].unique()),
                             default=sorted(base_df[COL_NEW].unique()))

filt_df = base_df[base_df[COL_OLD].isin(sel_old) & base_df[COL_NEW].isin(sel_new)]

mode = st.radio("โหมดแสดงผล", ["ซ่อนชื่อ (ระดับฝ่าย)", "แสดงชื่อบุคคล"], horizontal=True)

# ======================
# Render
# ======================
if len(filt_df) == 0:
    st.warning("ไม่มีข้อมูลหลังจากกรอง ลองเพิ่มตัวเลือกฝ่ายเดิม/ใหม่ดูนะครับ")
else:
    if mode == "ซ่อนชื่อ (ระดับฝ่าย)":
        fig = sankey_departments(filt_df, COL_OLD, COL_NEW)
    else:
        fig = sankey_with_names(filt_df, COL_OLD, COL_NEW, COL_NAME)

    st.plotly_chart(fig, use_container_width=True)

    # ดาวน์โหลด HTML
    html = fig.to_html(include_plotlyjs="cdn", full_html=True)
    st.download_button("💾 ดาวน์โหลดไฟล์ HTML", data=html, file_name="sankey_plot_nhso.html", mime="text/html")
