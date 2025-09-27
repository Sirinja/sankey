import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ------------------------
# Config
# ------------------------
st.set_page_config(page_title="Sankey Rotation", layout="wide")
st.title("📊 Sankey Diagram - การโยกย้ายบุคลากร")

# ------------------------
# Helpers (palette & font)
# ------------------------
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

# ------------------------
# App
# ------------------------
uploaded = st.file_uploader("อัปโหลดไฟล์ Excel", type=["xlsx"])
if uploaded:
    sheet_name = "ตารางรายละเอียด"
    data = pd.read_excel(uploaded, sheet_name=sheet_name, header=2)

    COL_OLD  = "ส่วนงานเดิม"
    COL_NAME = "คำนำหน้า ชื่อ - สกุล"
    COL_NEW  = [c for c in data.columns if str(c).startswith("ส่วนงานใหม่")][0]

    df = data[[COL_OLD, COL_NEW, COL_NAME]].dropna(subset=[COL_OLD, COL_NEW])

    # 🔹 Filter panels
    sel_old = st.multiselect("เลือกฝ่ายเดิม", sorted(df[COL_OLD].unique()), default=sorted(df[COL_OLD].unique()))
    sel_new = st.multiselect("เลือกฝ่ายใหม่", sorted(df[COL_NEW].unique()), default=sorted(df[COL_NEW].unique()))

    df = df[df[COL_OLD].isin(sel_old) & df[COL_NEW].isin(sel_new)]

    mode = st.radio("โหมดแสดงผล", ["ซ่อนชื่อ (ระดับฝ่าย)", "แสดงชื่อบุคคล"])

    if mode == "ซ่อนชื่อ (ระดับฝ่าย)":
        flows = (
            df.groupby([COL_OLD, COL_NEW], as_index=False)
              .size()
              .rename(columns={"size": "count"})
        )

        left_order = list(flows.groupby(COL_OLD)["count"].sum().sort_values(ascending=False).index)
        right_order = list(flows.groupby(COL_NEW)["count"].sum().sort_values(ascending=False).index)

        left_index = {name: i for i, name in enumerate(left_order)}
        right_index = {name: i + len(left_order) for i, name in enumerate(right_order)}
        labels = left_order + right_order

        sources = [left_index[o] for o in flows[COL_OLD]]
        targets = [right_index[n] for n in flows[COL_NEW]]
        values  = flows["count"].tolist()

        node_colors = repeat_palette(PALETTE, len(labels))
        link_colors = [hex_to_rgba(node_colors[s], 0.45) for s in sources]
        font_color  = choose_font_color(node_colors)

        fig = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                label=labels, pad=18, thickness=18,
                color=node_colors,
                line=dict(color="rgba(0,0,0,0.25)", width=0.5),
                font=dict(color=font_color, size=14),  # <<< ฟอนต์ขนาด 14
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

    else:  # แสดงชื่อบุคคล
        df["left_label"] = df[COL_OLD] + " : " + df[COL_NAME]
        sources_lbl = df["left_label"]
        targets_lbl = df[COL_NEW]
        values      = [1] * len(df)

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
                font=dict(color=font_color, size=16),  # <<< ฟอนต์ขนาด 14
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
