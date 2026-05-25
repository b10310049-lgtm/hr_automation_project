"""
HR 招募戰情室 - Streamlit 全體應徵者群像分析儀表板
包含：即時 Google Sheets 資料同步、全體應徵者數據、招募漏斗 KPI、Plotly 視覺化圖表、市場技能供需地圖
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gspread
from google.oauth2.service_account import Credentials

# ========== 頁面與主題設定 ==========
st.set_page_config(page_title="HR 招募戰情室", layout="wide")
st.title("📊 HR 招募戰情室 (全體應徵者群像分析)")

UI_THEME = {
    'TITLE_COLOR': '#154360',
    'BG_COLOR': '#FDFDFD',
    'PRIMARY': '#1B4F72',
    'SECONDARY': '#2E86C1',
    'PIE_COLORS': ['#154360', "#46799B", "#8DC5EA", "#87A4B7", "#96B6CB"],
    'GRID_STYLE': '#F2F2F2',
    'SKILL_BAR_COLOR': '#2874A6'
}

# ========== 1. 即時抓取 Google Sheets 資料 ==========
@st.cache_data(ttl="1d")  
def load_data_from_sheets():
    SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds.json", scopes=SCOPE)
    gs_client = gspread.authorize(creds)
    sheet = gs_client.open("HR後台_應徵者追蹤表").sheet1
    
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        return df
    return pd.DataFrame()

with st.spinner('正在從雲端同步最新招募數據...'):
    df_raw = load_data_from_sheets()

if df_raw.empty:
    st.warning("目前試算表中沒有招募資料。")
    st.stop()

# ========== 2. 資料清洗與轉換 ==========
df_raw = df_raw[df_raw['name'].astype(str).str.strip() != ""]

if df_raw.empty:
    st.warning("⚠️ 經過資料清洗後，未發現任何有效的應徵者數據。")
    st.stop()

df_all = df_raw.copy()

df_all['score'] = pd.to_numeric(df_all['score'], errors='coerce')
df_all['expected_salary'] = pd.to_numeric(df_all['expected_salary'], errors='coerce')
df_all['total_experience_years'] = pd.to_numeric(df_all['total_experience_years'], errors='coerce')
df_all['applied_at'] = pd.to_datetime(df_all['applied_at'], errors='coerce')

# ==================== 🎯 側邊欄動態篩選器 ====================
st.sidebar.header("🎯 招募數據篩選器")

job_list = ["全部"] + list(df_all['job_applied'].dropna().unique())
selected_job = st.sidebar.selectbox("選擇職缺", job_list)

time_filter = st.sidebar.radio("選擇時間區間", ["全部", "近一週", "近三週"])

if selected_job != "全部":
    df_all = df_all[df_all['job_applied'] == selected_job]

current_time = pd.to_datetime('today')
if time_filter == "近一週":
    df_all = df_all[df_all['applied_at'] >= (current_time - pd.Timedelta(days=7))]
elif time_filter == "近三週":
    df_all = df_all[df_all['applied_at'] >= (current_time - pd.Timedelta(days=21))]

if df_all.empty:
    st.sidebar.error("此篩選條件下無符合的應徵者資料。")
    st.stop()

# ==================== 🏆 招募漏斗 KPI 數據卡 ====================
st.markdown("### 📈 招募漏斗轉換率 (Recruitment Funnel)")

total_applicants = len(df_all)
invited_statuses = ['已發面邀未回覆', '面試排程已確認', '已錄取', '婉拒offer']
invited_count = len(df_all[df_all['status'].isin(invited_statuses)])
hired_count = len(df_all[df_all['status'] == '已錄取'])

invited_rate = f"{int((invited_count / total_applicants) * 100)}%" if total_applicants > 0 else "0%"
hired_rate = f"{int((hired_count / total_applicants) * 100)}%" if total_applicants > 0 else "0%"

col1, col2, col3 = st.columns(3)
col1.metric("👥 總應徵人數", f"{total_applicants} 人")
col2.metric("✉️ 進入面試階段", f"{invited_count} 人", f"面試轉換率: {invited_rate}")
col3.metric("🎉 最終錄取人數", f"{hired_count} 人", f"錄取轉換率: {hired_rate}")

st.divider()

def segment_experience(years):
    try:
        val = float(years)
        if val <= 2: return '0-2年'
        elif val <= 5: return '3-5年'
        else: return '5年以上'
    except:
        return '未知'

df_all['年資分組'] = df_all['total_experience_years'].apply(segment_experience)

# ========== 3. 建立頂部主要群像分析圖表 (Subplots) ==========
fig = make_subplots(
    rows=3, 
    cols=2,
    subplot_titles=(
        "<b>應徵者學歷組成 </b>", "<b>應徵者年資分布 </b>", 
        "<b>期待薪資分布 </b>", "<b>AI 評分分佈 </b>",
        "<b>評分與期待薪資關係圖 </b>", "<b>指標統計摘要 </b>"
    ),
    vertical_spacing=0.12, 
    horizontal_spacing=0.12,
    specs=[
        [{"type": "pie"}, {"type": "bar"}],
        [{"type": "xy"}, {"type": "xy"}],
        [{"type": "xy"}, {"type": "table"}]
    ]
)

# (1) 學歷組成
edu_counts = df_all['highest_education'].value_counts()
fig.add_trace(go.Pie(
    labels=edu_counts.index, 
    values=edu_counts.values, 
    hole=.55,
    textinfo='label+percent',
    insidetextorientation='horizontal',
    marker=dict(colors=UI_THEME['PIE_COLORS'], line=dict(color=UI_THEME['BG_COLOR'], width=2))
), row=1, col=1)

# (2) 工作年資分布條形圖
exp_order = ['0-2年', '3-5年', '5年以上']
exp_counts = df_all['年資分組'].value_counts().reindex(exp_order).fillna(0)
fig.add_trace(go.Bar(
    x=exp_counts.index, 
    y=exp_counts.values, 
    marker_color=UI_THEME['PRIMARY'], 
    width=0.45,
    text=exp_counts.values, 
    textposition='outside'
), row=1, col=2)

# (3) 期待薪資分布直方圖 
fig.add_trace(go.Histogram(
    x=df_all['expected_salary'], 
    xbins=dict(size=10000),
    marker_color=UI_THEME['SECONDARY'], 
    marker_line=dict(color='white', width=1), 
    opacity=0.9
), row=2, col=1)

# (4) AI 評分分布直方圖
fig.add_trace(go.Histogram(
    x=df_all['score'], 
    xbins=dict(size=5),
    marker_color=UI_THEME['PRIMARY'],
    marker_line=dict(color='white', width=1)
), row=2, col=2)

# (5) 評分與薪資關係散佈圖
fig.add_trace(go.Scatter(
    x=df_all['score'], 
    y=df_all['expected_salary'], 
    mode='markers',
    marker=dict(size=12, color=UI_THEME['SECONDARY'], opacity=0.7, line=dict(width=1, color='white')),
    text=df_all['name'], 
    hovertemplate="<b>姓名: %{text}</b><br>分數: %{x}分<br>薪資: %{y:,.0f}元<extra></extra>"
), row=3, col=1)

# (6) 數據統計表
metrics_list = ['期待薪資 (Salary)', '工作年資 (Exp)', 'AI 評分 (Score)']
avg_data = [
    f"{df_all['expected_salary'].mean():,.0f}", 
    f"{df_all['total_experience_years'].mean():.1f} 年", 
    f"{df_all['score'].mean():.1f}"
]
med_data = [
    f"{df_all['expected_salary'].median():,.0f}", 
    f"{df_all['total_experience_years'].median():.1f} 年", 
    f"{df_all['score'].median():.1f}"
]

fig.add_trace(go.Table(
    header=dict(
        values=['<b>分析指標</b>', '<b>平均數 (Avg)</b>', '<b>中位數 (Med)</b>'],
        fill_color=UI_THEME['PRIMARY'], 
        align='center', 
        font=dict(color='white', size=14)
    ),
    cells=dict(
        values=[metrics_list, avg_data, med_data],
        fill_color='#F4F6F7', 
        align='center', 
        font=dict(size=13), 
        height=35
    )
), row=3, col=2)

fig.update_layout(
    title_text="<b>HR 全體應徵者市場數據報告</b>",
    title_font=dict(size=26, color=UI_THEME['TITLE_COLOR']),
    template="plotly_white", 
    height=1200, 
    showlegend=False, 
    paper_bgcolor=UI_THEME['BG_COLOR']
)

for r in [1, 2]:
    for c in [1, 2]:
        if not (r == 1 and c == 1):
            fig.update_yaxes(dtick=1, tickformat='d', row=r, col=c)

fig.update_yaxes(title_text="期待薪資 (TWD)", row=3, col=1, dtick=None, tickformat=',.0f')
fig.update_xaxes(title_text="AI 綜合評分 (0-100)", row=3, col=1)
fig.update_xaxes(title_text="薪資範圍 ", row=2, col=1)
fig.update_xaxes(title_text="AI 評分分數 ", row=2, col=2)

st.plotly_chart(fig, use_container_width=True)

# ==================== 🛠️ 4. 核心技能供需地圖 (Skills Inventory) ====================
st.markdown("### 📡 核心技能供需地圖 (Skills Market Inventory)")

# 將 skills_extracted 欄位用半形逗號拆分，並展開計算頻率
df_skills = df_all['skills_extracted'].astype(str).str.split(',')
df_exploded = df_skills.explode().str.strip()

# 過濾掉空值或異常資料
df_exploded = df_exploded[df_exploded != ""]
skill_counts = df_exploded.value_counts().reset_index()
skill_counts.columns = ['Skill', 'Count']

# 篩選前 15 大熱門關鍵字
top_skills = skill_counts.head(15).sort_values(by='Count', ascending=True)

# 建立獨立的水平橫條圖
fig_skills = go.Figure()
fig_skills.add_trace(go.Bar(
    y=top_skills['Skill'],
    x=top_skills['Count'],
    orientation='h',
    marker_color=UI_THEME['SKILL_BAR_COLOR'],
    text=top_skills['Count'],
    textposition='outside',
    width=0.6
))

fig_skills.update_layout(
    title_text="<b>目前求職市場應徵者具備技能排行 (Top 15 Skills)</b>",
    title_font=dict(size=18, color=UI_THEME['TITLE_COLOR']),
    template="plotly_white",
    height=550,
    xaxis=dict(title="具備此技能之應徵者人數", dtick=5),
    yaxis=dict(title="技能關鍵字標籤"),
    paper_bgcolor=UI_THEME['BG_COLOR'],
    margin=dict(l=150, r=50, t=80, b=50)
)

st.plotly_chart(fig_skills, use_container_width=True)


# 手動強制更新按鈕
st.divider()
if st.button("🔄 手動同步最新 Google Sheets 數據"):
    st.cache_data.clear()
    st.rerun()