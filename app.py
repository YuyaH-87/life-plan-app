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

# ==========================================
# 1. セキュリティ設定
# ==========================================
APP_PASSWORD = "0729"

def check_password():
    if "login_success" not in st.session_state:
        st.session_state["login_success"] = False
    if not st.session_state["login_success"]:
        st.title("🔐 ライフプラン・ログイン")
        password_input = st.text_input("パスワードを入力", type="password")
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
st.set_page_config(page_title="共同資金シミュレーターPro", layout="wide")

is_report_mode = st.query_params.get("report_mode", "false").lower() == "true"

if not is_report_mode:
    st.title("💍 共同資金 キャッシュフロー・シミュレーター")
    st.write("各イベントの発生タイミングを分散させ、資金ショートを防ぐ計画を立てましょう。")

st.sidebar.header("📊 シミュレーション条件")

# --- ① 現在の資産 ---
st.sidebar.subheader("① 現在の貯蓄額")
current_self = st.sidebar.number_input("自分の現在の貯蓄（万円）", 0, 5000, 150, 10)
current_partner = st.sidebar.number_input("パートナーの現在の貯蓄（万円）", 0, 5000, 100, 10)
total_current_assets = current_self + current_partner

# --- ② 毎月の積立 ---
st.sidebar.subheader("② 毎月の積立・運用")
monthly_self = st.sidebar.number_input("自分の拠出（万円/月）", 0, 100, 10, 1)
monthly_partner = st.sidebar.number_input("パートナーの拠出（万円/月）", 0, 100, 10, 1)
annual_bonus = st.sidebar.number_input("年間の合計ボーナス拠出（万円/年）", 0, 500, 60, 10)
investment_yield = st.sidebar.slider("想定運用利回り（年利 %）", 0.0, 10.0, 3.0, 0.1)

monthly_bonus_equiv = annual_bonus / 12
total_monthly_input = monthly_self + monthly_partner + monthly_bonus_equiv

# --- ③ 基本イベント予算と発生時期 ---
st.sidebar.subheader("③ 基本イベント")

target_rent = st.sidebar.number_input("新居の想定家賃（万円/月）", 0, 100, 15, 1)
initial_housing_cost = target_rent * 5
month_moving = st.sidebar.slider("引越しの時期（ヶ月後）", 1, 60, 6)

budget_ring = st.sidebar.number_input("リング予算（万円）", 0, 200, 50, 5)
month_ring = st.sidebar.slider("リング購入時期（ヶ月後）", 1, 60, 10)

budget_furniture = st.sidebar.number_input("家具家電予算（万円）", 0, 300, 80, 5)
month_furniture = st.sidebar.slider("家具購入時期（ヶ月後）", 1, 60, 7)

budget_wedding = st.sidebar.number_input("結婚式 自己負担額（万円）", 0, 500, 200, 10)
month_wedding = st.sidebar.slider("結婚式の時期（ヶ月後）", 1, 60, 18)

budget_honeymoon = st.sidebar.number_input("旅行予算（万円）", 0, 300, 60, 5)
month_honeymoon = st.sidebar.slider("旅行の時期（ヶ月後）", 1, 60, 20)

# --- ④ カスタムイベント（自由追加） ---
st.sidebar.subheader("④ カスタムイベントの追加")
st.sidebar.caption("車の購入、教育資金、独立資金などを自由に追加できます")

# セッションステートにカスタムイベントの数を保存
if 'custom_events_count' not in st.session_state:
    st.session_state.custom_events_count = 0

# イベント追加ボタン
if st.sidebar.button("➕ イベントを追加"):
    st.session_state.custom_events_count += 1

# イベント削除ボタン（1つ以上ある場合のみ表示）
if st.session_state.custom_events_count > 0:
    if st.sidebar.button("➖ 最後のイベントを削除"):
        st.session_state.custom_events_count -= 1

custom_events = [] # 追加されたイベントを格納するリスト

# 追加された数だけ入力欄を生成
for i in range(st.session_state.custom_events_count):
    st.sidebar.markdown(f"**追加イベント {i+1}**")
    name = st.sidebar.text_input(f"イベント名", value=f"イベント{i+1}", key=f"name_{i}")
    budget = st.sidebar.number_input(f"費用（万円）", min_value=0, max_value=2000, value=100, step=10, key=f"budget_{i}")
    month = st.sidebar.slider(f"発生時期（ヶ月後）", 1, 120, 24, key=f"month_{i}") # 期間を最大10年(120ヶ月)に拡張
    
    if budget > 0: # 予算が0以上のものだけをリストに追加
        custom_events.append({"name": name, "budget": budget, "month": month})


# ==========================================
# 3. キャッシュフロー計算ロジック（月次ループ）
# ==========================================
# カスタムイベントで遠い未来が設定された場合に対応するため、シミュレーション期間を拡張
max_custom_month = max([ev["month"] for ev in custom_events]) if custom_events else 0
sim_months = max(60, max_custom_month + 6) # 最低5年、それ以上ならカスタムイベント+半年分を描画

cash_flow = []
min_balance = float('inf')
shortfall_month = -1

current_balance = total_current_assets
total_custom_expenses = sum([ev["budget"] for ev in custom_events])
total_expenses = initial_housing_cost + budget_ring + budget_furniture + budget_wedding + budget_honeymoon + total_custom_expenses

for m in range(0, sim_months + 1):
    expense_this_month = 0
    event_names = []
    
    if m > 0:
        current_balance += total_monthly_input
        monthly_yield = (investment_yield / 100) / 12
        current_balance += current_balance * monthly_yield
        
    # 基本イベントの判定
    if m == month_moving:
        expense_this_month += initial_housing_cost
        event_names.append(f"引越し({int(initial_housing_cost)}万)")
    if m == month_ring:
        expense_this_month += budget_ring
        event_names.append(f"指輪({int(budget_ring)}万)")
    if m == month_furniture:
        expense_this_month += budget_furniture
        event_names.append(f"家具({int(budget_furniture)}万)")
    if m == month_wedding:
        expense_this_month += budget_wedding
        event_names.append(f"結婚式({int(budget_wedding)}万)")
    if m == month_honeymoon:
        expense_this_month += budget_honeymoon
        event_names.append(f"旅行({int(budget_honeymoon)}万)")
        
    # カスタムイベントの判定
    for ev in custom_events:
        if m == ev["month"]:
            expense_this_month += ev["budget"]
            event_names.append(f"{ev['name']}({ev['budget']}万)")

    current_balance -= expense_this_month
    
    if current_balance < min_balance:
        min_balance = current_balance
        if current_balance < 0 and shortfall_month == -1:
            shortfall_month = m

    cash_flow.append({
        "ヶ月後": m,
        "資産残高": current_balance,
        "支出": expense_this_month,
        "イベント": " + ".join(event_names) if event_names else ""
    })

df_cf = pd.DataFrame(cash_flow)

# ==========================================
# 4. メイン画面・レポート表示
# ==========================================

if is_report_mode:
    st.title("📋 シミュレーション・レポート")
    st.write("この画面をスクリーンショットして保存してください。")
    
    st.subheader("💡 サマリー")
    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("総イベント予算", f"{int(total_expenses)} 万円")
    col_r2.metric("毎月の合計積立", f"{int(monthly_self + monthly_partner)} 万円")
    col_r3.metric(f"{int(sim_months/12)}年後の予想残高", f"{int(df_cf.iloc[-1]['資産残高'])} 万円")
    
    if min_balance >= 0:
        st.success("✅ **判定：クリア！** すべてのイベントをこなしても資金はショートしません。")
    else:
        st.error(f"🚨 **判定：資金ショートの危険あり！** {shortfall_month}ヶ月後に資金がマイナスになります。")
    
    st.divider()
    
else:
    st.subheader("診断結果：資金ショート判定")
    if min_balance >= 0:
        st.success(f"✅ **クリア！** 現在の計画なら、すべてのイベントをこなしても資金ショートしません。（最も厳しい時でも残高 {int(min_balance)}万円 をキープします）")
    else:
        st.error(f"🚨 **資金ショートの危険あり！** 今の計画だと、**{shortfall_month}ヶ月後** に資金がマイナス（最大不足額: {int(abs(min_balance))}万円）に陥ります。")

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 現在の合計貯蓄", f"{int(total_current_assets)} 万円")
    with col2:
        st.metric("💸 総イベント費用", f"{int(total_expenses)} 万円")
    with col3:
        st.metric(f"📈 {int(sim_months/12)}年後の予想残高", f"{int(df_cf.iloc[-1]['資産残高'])} 万円")

# --- グラフ描画（共通） ---
if not is_report_mode:
    st.subheader("📊 資産残高（キャッシュフロー）の推移")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_cf["ヶ月後"], y=df_cf["資産残高"], mode='lines+markers', name='予想資産残高', line=dict(color='#4CAF50', width=3)))
fig.add_trace(go.Scatter(x=[0, sim_months], y=[0, 0], mode='lines', name='資金ショートライン', line=dict(color='red', width=2, dash='dash')))

for index, row in df_cf[df_cf["イベント"] != ""].iterrows():
    fig.add_annotation(
        x=row["ヶ月後"], y=row["資産残高"],
        text=row["イベント"], showarrow=True,
        arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#636EFA",
        ax=0, ay=-40, font=dict(size=12, color="white"), bgcolor="#636EFA", opacity=0.8
    )

fig.update_layout(xaxis_title="現在からの経過月数", yaxis_title="資産残高（万円）", hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig, use_container_width=True)


# --- レポートモード切替 ---
if not is_report_mode:
    st.divider()
    st.markdown("### 📷 パートナーに共有する")
    if st.button("🖨️ スクショ用レポート画面を開く"):
        st.query_params["report_mode"] = "true"
        st.rerun()
        
if is_report_mode:
    if st.button("⬅️ 入力画面に戻る"):
        st.query_params["report_mode"] = "false"
        st.rerun()
# ========== 貼り付けここまで ==========

if __name__ == "__main__":
    pass
