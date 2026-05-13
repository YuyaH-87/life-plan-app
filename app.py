# -*- coding: utf-8 -*-
"""
アプリのエントリーポイントです。
必要な import や処理を、下の「貼り付けエリア」にそのまま貼り付けてください。
"""

# ========== ここから下にコードを貼り付け ==========
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import math
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ==========================================
# 1. セキュリティ設定
# ==========================================
# ログインパスワードを 0729 に変更しました
APP_PASSWORD = "0729"

def check_password():
    if "login_success" not in st.session_state:
        st.session_state["login_success"] = False
    if not st.session_state["login_success"]:
        st.title("🔐 ログイン")
        password_input = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if password_input == APP_PASSWORD:
                st.session_state["login_success"] = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return False
    return True

if not check_password():
    st.stop()

# ==========================================
# 2. 設定・UI
# ==========================================
# 名前を「ライフプランシミュレーター」に変更
st.set_page_config(page_title="ライフプランシミュレーター", layout="wide")

is_report_mode = st.query_params.get("report_mode", "false").lower() == "true"

if not is_report_mode:
    st.title("ライフプランシミュレーター")

# --- サイドバー入力 ---
st.sidebar.header("📊 シミュレーション条件")

st.sidebar.subheader("① 現在の貯蓄")
current_self = st.sidebar.number_input("自分（万円）", 0, 5000, 150, 10)
current_partner = st.sidebar.number_input("パートナー（万円）", 0, 5000, 100, 10)
total_current_assets = current_self + current_partner

st.sidebar.subheader("② 毎月の積立")
monthly_self = st.sidebar.number_input("自分の拠出（万円/月）", 0, 100, 10, 1)
monthly_partner = st.sidebar.number_input("パートナーの拠出（万円/月）", 0, 100, 10, 1)
annual_bonus = st.sidebar.number_input("年間のボーナス合計（万円）", 0, 500, 60, 10)
investment_yield = st.sidebar.slider("運用利回り（年利 %）", 0.0, 10.0, 3.0, 0.1)

st.sidebar.subheader("③ 基本イベント")
target_rent = st.sidebar.number_input("新居家賃（万円）", 0, 100, 15, 1)
initial_housing_cost = target_rent * 5
month_moving = st.sidebar.slider("引越し時期（ヶ月後）", 1, 60, 6)

budget_ring = st.sidebar.number_input("リング（万円）", 0, 200, 50, 5)
month_ring = st.sidebar.slider("リング購入時期（ヶ月後）", 1, 60, 10)

budget_furniture = st.sidebar.number_input("家具家電（万円）", 0, 300, 80, 5)
month_furniture = st.sidebar.slider("家具購入時期（ヶ月後）", 1, 60, 7)

budget_wedding = st.sidebar.number_input("結婚式 自己負担（万円）", 0, 500, 200, 10)
month_wedding = st.sidebar.slider("結婚式時期（ヶ月後）", 1, 60, 18)

budget_honeymoon = st.sidebar.number_input("旅行（万円）", 0, 300, 60, 5)
month_honeymoon = st.sidebar.slider("旅行時期（ヶ月後）", 1, 60, 20)

st.sidebar.subheader("④ カスタムイベント")
if 'custom_events_count' not in st.session_state:
    st.session_state.custom_events_count = 0
if st.sidebar.button("➕ 追加"):
    st.session_state.custom_events_count += 1
if st.session_state.custom_events_count > 0:
    if st.sidebar.button("➖ 削除"):
        st.session_state.custom_events_count -= 1

custom_events = []
for i in range(st.session_state.custom_events_count):
    st.sidebar.markdown(f"**カスタム {i+1}**")
    name = st.sidebar.text_input(f"名", value=f"イベント{i+1}", key=f"name_{i}")
    budget = st.sidebar.number_input(f"費", 0, 2000, 100, 10, key=f"budget_{i}")
    month = st.sidebar.slider(f"時", 1, 120, 24, key=f"month_{i}")
    if budget > 0:
        custom_events.append({"name": name, "budget": budget, "month": month})

# --- 日付計算用（今日から何ヶ月後かを表示用） ---
today = datetime.now()

# ==========================================
# 3. 計算ロジック
# ==========================================
max_custom_month = max([ev["month"] for ev in custom_events]) if custom_events else 0
sim_months = max(60, max_custom_month + 6)

total_monthly_input = monthly_self + monthly_partner + (annual_bonus / 12)
cash_flow = []
min_balance = float('inf')
shortfall_month = -1
current_balance = total_current_assets

for m in range(0, sim_months + 1):
    expense = 0
    names = []
    if m > 0:
        current_balance += total_monthly_input
        current_balance += current_balance * ((investment_yield / 100) / 12)
    
    if m == month_moving: expense += initial_housing_cost; names.append(f"引越し({int(initial_housing_cost)}万)")
    if m == month_ring: expense += budget_ring; names.append(f"指輪({int(budget_ring)}万)")
    if m == month_furniture: expense += budget_furniture; names.append(f"家具({int(budget_furniture)}万)")
    if m == month_wedding: expense += budget_wedding; names.append(f"結婚式({int(budget_wedding)}万)")
    if m == month_honeymoon: expense += budget_honeymoon; names.append(f"旅行({int(budget_honeymoon)}万)")
    for ev in custom_events:
        if m == ev["month"]: expense += ev["budget"]; names.append(f"{ev['name']}({ev['budget']}万)")

    current_balance -= expense
    if current_balance < min_balance:
        min_balance = current_balance
        if current_balance < 0 and shortfall_month == -1: shortfall_month = m
    
    target_date = today + relativedelta(months=m)
    cash_flow.append({
        "ヶ月後": m, 
        "日付": target_date.strftime("%Y年%m月"),
        "資産残高": current_balance, 
        "イベント": " + ".join(names) if names else ""
    })

df_cf = pd.DataFrame(cash_flow)

# ==========================================
# 4. レポート表示
# ==========================================
if is_report_mode:
    st.title("📋 ライフプラン報告レポート")
    
    # A. 結論（日付を具体化）
    st.subheader("🏁 判定結果")
    if min_balance >= 0:
        last_month_text = df_cf.iloc[-1]['日付']
        st.success(f"✅ **達成可能です**: シミュレーション終了時点（{last_month_text}）まで、一度も資金ショートすることなく計画を完遂できます。")
    else:
        sf_date = (today + relativedelta(months=shortfall_month)).strftime("%Y年%m月")
        st.error(f"🚨 **資金不足の可能性**: {shortfall_month}ヶ月後（{sf_date}）に、現在の貯蓄と積立ペースでは資金が不足する見込みです。")
    
    # B. 入力変数の一覧
    st.subheader("📝 シミュレーションの前提条件")
    
    # 変数のサマリー
    st.markdown("**【資産・積立設定】**")
    st.write(f"・初期合計資産: {int(total_current_assets)}万円 (自分:{current_self}万 / 相手:{current_partner}万)")
    st.write(f"・毎月の合計積立: {int(monthly_self+monthly_partner)}万円 (自分:{monthly_self}万 / 相手:{monthly_partner}万)")
    st.write(f"・ボーナス積立: 年間{annual_bonus}万円 / 想定運用利回り: {investment_yield}%")

    # 全イベント費用リスト（時期の重複を排除し、ここに日付を統合）
    st.markdown("**【予定されている支出リスト】**")
    event_data = [
        ["引越し初期費用", f"{int(initial_housing_cost)}万円", f"{month_moving}ヶ月後 ({(today + relativedelta(months=month_moving)).strftime('%Y/%m')})"],
        ["エンゲージリング", f"{budget_ring}万円", f"{month_ring}ヶ月後 ({(today + relativedelta(months=month_ring)).strftime('%Y/%m')})"],
        ["家具・家電購入", f"{budget_furniture}万円", f"{month_furniture}ヶ月後 ({(today + relativedelta(months=month_furniture)).strftime('%Y/%m')})"],
        ["結婚式(自己負担)", f"{budget_wedding}万円", f"{month_wedding}ヶ月後 ({(today + relativedelta(months=month_wedding)).strftime('%Y/%m')})"],
        ["新婚旅行", f"{budget_honeymoon}万円", f"{month_honeymoon}ヶ月後 ({(today + relativedelta(months=month_honeymoon)).strftime('%Y/%m')})"]
    ]
    for ev in custom_events:
        ev_date = (today + relativedelta(months=ev['month'])).strftime('%Y/%m')
        event_data.append([ev['name'], f"{ev['budget']}万円", f"{ev['month']}ヶ月後 ({ev_date})"])
    
    df_ev = pd.DataFrame(event_data, columns=["イベント名", "予算", "予定時期"])
    st.table(df_ev)

    if st.button("⬅️ 編集画面に戻る"):
        st.query_params["report_mode"] = "false"
        st.rerun()

# ==========================================
# 5. 通常画面表示
# ==========================================
else:
    st.subheader("判定")
    if min_balance >= 0:
        st.success(f"✅ 目標達成可能 (最低残高: {int(min_balance)}万)")
    else:
        sf_date_simple = (today + relativedelta(months=shortfall_month)).strftime("%Y/%m")
        st.error(f"🚨 {shortfall_month}ヶ月後（{sf_date_simple}）に不足見込み")

    # グラフ描画
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_cf["ヶ月後"], y=df_cf["資産残高"], mode='lines+markers', name='資産残高', line=dict(color='#4CAF50', width=2), hovertemplate='%{x}ヶ月後: %{y}万円'))
    fig.add_trace(go.Scatter(x=[0, sim_months], y=[0, 0], mode='lines', name='ゼロライン', line=dict(color='red', width=1, dash='dash')))

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="ヶ月後"),
        yaxis=dict(title="万円")
    )
    st.plotly_chart(fig, use_container_width=True, config={'responsive': True})

    if st.button("🖨️ スクショ用レポートを開く"):
        st.query_params["report_mode"] = "true"
        st.rerun()
# ========== 貼り付けここまで ==========

if __name__ == "__main__":
    pass
