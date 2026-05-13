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
st.title("💍 共同資金 キャッシュフロー・シミュレーター")
st.write("各イベントの発生タイミングを分散させ、資金ショート（残高マイナス）を防ぐ計画を立てましょう。")

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

# --- ③ イベントと時期の設定 ---
st.sidebar.subheader("③ イベント予算と発生時期")
st.sidebar.caption("※何ヶ月後にその支払いが発生するかを設定します")

# 引越し（初期費用は家賃ベースで自動計算）
st.sidebar.markdown("**🏠 引越し・新居**")
target_rent = st.sidebar.number_input("新居の想定家賃（万円/月）", 0, 100, 15, 1)
initial_housing_cost = target_rent * 5 # 敷・礼・仲・諸経費で家賃5ヶ月分と概算
month_moving = st.sidebar.slider("引越しの時期（ヶ月後）", 1, 60, 6)

# 指輪
st.sidebar.markdown("**💍 エンゲージリング**")
budget_ring = st.sidebar.number_input("リング予算（万円）", 0, 200, 50, 5)
month_ring = st.sidebar.slider("リング購入時期（ヶ月後）", 1, 60, 10)

# 家具・家電
st.sidebar.markdown("**🛋 家具・家電**")
budget_furniture = st.sidebar.number_input("家具家電予算（万円）", 0, 300, 80, 5)
month_furniture = st.sidebar.slider("家具購入時期（ヶ月後）", 1, 60, 7)

# 結婚式
st.sidebar.markdown("**⛪ 結婚式**")
budget_wedding = st.sidebar.number_input("結婚式 自己負担額（万円）", 0, 500, 200, 10)
month_wedding = st.sidebar.slider("結婚式の時期（ヶ月後）", 1, 60, 18)

# 新婚旅行
st.sidebar.markdown("**✈️ 新婚旅行**")
budget_honeymoon = st.sidebar.number_input("旅行予算（万円）", 0, 300, 60, 5)
month_honeymoon = st.sidebar.slider("旅行の時期（ヶ月後）", 1, 60, 20)

# ==========================================
# 3. キャッシュフロー計算ロジック（月次ループ）
# ==========================================
sim_months = 60 # 5年間（60ヶ月）のシミュレーション
cash_flow = []
min_balance = float('inf')
shortfall_month = -1

current_balance = total_current_assets

for m in range(0, sim_months + 1):
    expense_this_month = 0
    event_names = []
    
    # 0ヶ月目（現在）は積立なし、1ヶ月目から積立・運用開始
    if m > 0:
        # 1. 毎月の積立を足す
        current_balance += total_monthly_input
        # 2. 運用益を足す（月利）
        monthly_yield = (investment_yield / 100) / 12
        current_balance += current_balance * monthly_yield
        
    # 3. その月のイベント費用を引く（キャッシュアウト）
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

    current_balance -= expense_this_month
    
    # 最低残高とその月を記録
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
# 4. メイン画面表示
# ==========================================
st.subheader("診断結果：資金ショート判定")

total_expenses = initial_housing_cost + budget_ring + budget_furniture + budget_wedding + budget_honeymoon

if min_balance >= 0:
    st.success(f"✅ **クリア！** 現在の計画なら、すべてのイベントをこなしても資金ショートしません。（最も厳しい時でも残高 {int(min_balance)}万円 をキープします）")
    st.balloons()
else:
    st.error(f"🚨 **資金ショートの危険あり！** 今の計画だと、**{shortfall_month}ヶ月後** に資金がマイナス（最大不足額: {int(abs(min_balance))}万円）に陥ります。")
    st.write("💡 **改善案**: 以下のいずれかを調整してください。")
    st.markdown(f"- 毎月の積立（ボーナス含む）をあと **{math.ceil(abs(min_balance)/shortfall_month)}万円** 増やす")
    st.markdown("- 大きな支出（結婚式や引越し）の時期を数ヶ月**後ろにズラす**")
    st.markdown("- 各イベントの予算を下げる")

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💰 現在の合計貯蓄", f"{int(total_current_assets)} 万円")
with col2:
    st.metric("💸 5年間の総イベント費用", f"{int(total_expenses)} 万円")
with col3:
    st.metric("📈 5年後の予想資産残高", f"{int(df_cf.iloc[-1]['資産残高'])} 万円")

# --- グラフ描画（Plotlyでリッチに表現） ---
st.subheader("📊 資産残高（キャッシュフロー）の推移")

fig = go.Figure()
# 資産推移の折れ線
fig.add_trace(go.Scatter(x=df_cf["ヶ月後"], y=df_cf["資産残高"], mode='lines+markers', name='予想資産残高', line=dict(color='#4CAF50', width=3)))
# デッドライン（ゼロライン）
fig.add_trace(go.Scatter(x=[0, sim_months], y=[0, 0], mode='lines', name='資金ショートライン', line=dict(color='red', width=2, dash='dash')))

# イベント発生月にアノテーション（吹き出し）を追加
for index, row in df_cf[df_cf["イベント"] != ""].iterrows():
    fig.add_annotation(
        x=row["ヶ月後"], y=row["資産残高"],
        text=row["イベント"], showarrow=True,
        arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#636EFA",
        ax=0, ay=-40, font=dict(size=12, color="white"), bgcolor="#636EFA", opacity=0.8
    )

fig.update_layout(xaxis_title="現在からの経過月数", yaxis_title="資産残高（万円）", hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig, use_container_width=True)
# ========== 貼り付けここまで ==========

if __name__ == "__main__":
    pass
