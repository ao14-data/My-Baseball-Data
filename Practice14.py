import os
import re
from datetime import date
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --- ページ基本設定 ---
st.set_page_config(
    page_title="データ分析＋α",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSV_FILE = "baseball_data.csv"

# --- 超安定・シンプル化されたデザインCSS ---
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 5rem !important;
    }
    div.stSelectbox, div.stTextInput, div.stRadio {
        margin-bottom: 2px !important;
    }
    
    /* 5等分のカラムを綺麗に固定 */
    [data-testid="column"] {
        min-width: 0px !important;
        flex: 1 1 0px !important;
        padding: 0px 1px !important;
    }
    
    /* --- ボード全体のコンテナ --- */
    .catcher-board {
        background: #1b4d3e;
        border: 4px solid #333333;
        border-radius: 12px;
        padding: 12px;
        max-width: 440px;
        margin: 0 auto;
        box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    }
    
    /* ボタンの共通スタイル（クラッシュ防止のため軽量化） */
    .catcher-board div.stButton > button {
        padding: 2px 0px !important;
        font-size: 13px !important;
        font-weight: bold !important;
        height: 45px !important;
        min-height: 45px !important;
        margin: 1px !important;
        width: 100% !important;
    }
    
    [data-testid="stDataFrame"] {
        overflow-x: hidden !important;
    }
    [data-testid="stDataFrame"] > div {
        overflow-x: hidden !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- 初期データの生成／読み込み ---
def load_or_init_data():
  expected_columns = [
      "日付",
      "試合ID",
      "投手名",
      "打者名",
      "打者左右",
      "イニング",
      "アウト数",
      "ランナー",
      "ボール",
      "ストライク",
      "球種",
      "コース",
      "結果",
  ]

  if not os.path.exists(CSV_FILE):
    initial_data = pd.DataFrame([
        {
            "日付": "2026-10-18",
            "試合ID": "公式戦",
            "投手名": "あお",
            "打者名": "鈴木",
            "打者左右": "R",
            "イニング": "1回表",
            "アウト数": 0,
            "ランナー": "なし",
            "ボール": 0,
            "ストライク": 0,
            "球種": "ストレート",
            "コース": 13,
            "結果": "空振り",
        }
    ])
    initial_data.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

  df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")

  for col in expected_columns:
    if col not in df.columns:
      df[col] = "-"

  df = df[expected_columns]
  df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
  return df


df_data = load_or_init_data()

# --- タイトル ---
st.title("⚾ データ分析＋α")

# タブの作成
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 試合一覧",
    "📝 データ入力",
    "🗂️ 打席一覧・1球データ詳細",
    "🔥 配球ヒートマップ分析",
])


# ==========================================
# 【タブ1】試合一覧
# ==========================================
with tab1:
  st.subheader("📋 試合一覧（ゲーム単位のサマリー）")

  df_all_games = pd.read_csv(CSV_FILE, encoding="utf-8-sig")

  if df_all_games.empty:
    st.info("登録されているデータはありません。")
  else:
    game_summary_list = []
    for (game_id, date_str), g_df in df_all_games.groupby(["試合ID", "日付"]):
      pitchers = ", ".join(g_df["投手名"].dropna().unique())
      total_pitches = len(g_df)
      unique_batters = g_df["打者名"].nunique()
      game_summary_list.append({
          "日付": date_str,
          "試合名": game_id,
          "登板投手": pitchers,
          "総投球数": total_pitches,
          "対戦打者数": unique_batters,
      })

    df_game_summary = pd.DataFrame(game_summary_list)

    st.markdown("##### 🏟️ 登録されている試合一覧")
    st.dataframe(df_game_summary, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("##### 🔍 特定の試合を選択して詳細を確認・エクスポート")
    unique_games = sorted(df_all_games["試合ID"].unique())
    selected_game_view = st.selectbox("詳細を見る試合を選択", unique_games)

    df_selected_game_data = df_all_games[
        df_all_games["試合ID"] == selected_game_view
    ]

    st.markdown(
        f"**【試合名: {selected_game_view}】の全投球データ ({len(df_selected_game_data)}球)**"
    )
    st.dataframe(
        df_selected_game_data, use_container_width=True, hide_index=True
    )

    csv_bytes = df_selected_game_data.to_csv(
        index=False, encoding="utf-8-sig"
    ).encode("utf-8-sig")
    st.download_button(
        label=f"📥 「{selected_game_view}」のデータをCSVでダウンロード",
        data=csv_bytes,
        file_name=f"baseball_data_{selected_game_view}.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ==========================================
# 【タブ2】データ入力フォーム
# ==========================================
with tab2:
  today = date.today()

  if "year" not in st.session_state:
    st.session_state.year = today.year
  if "month" not in st.session_state:
    st.session_state.month = today.month
  if "day" not in st.session_state:
    st.session_state.day = today.day

  if "game_id" not in st.session_state:
    st.session_state.game_id = "公式戦"
  if "pitcher_name" not in st.session_state:
    st.session_state.pitcher_name = "あお"

  if "lineup" not in st.session_state:
    st.session_state.lineup = [
        {"name": "鈴木", "side": "R"},
        {"name": "佐藤", "side": "L"},
        {"name": "高橋", "side": "R"},
        {"name": "田中", "side": "R"},
        {"name": "伊藤", "side": "L"},
        {"name": "渡辺", "side": "R"},
        {"name": "山本", "side": "L"},
        {"name": "中村", "side": "R"},
        {"name": "小林", "side": "R"},
    ]
  if "lineup_index" not in st.session_state:
    st.session_state.lineup_index = 0

  if "selected_course" not in st.session_state:
    st.session_state.selected_course = 13
  if "balls" not in st.session_state:
    st.session_state.balls = 0
  if "strikes" not in st.session_state:
    st.session_state.strikes = 0
  if "outs" not in st.session_state:
    st.session_state.outs = 0

  strike_zones = [7, 8, 9, 12, 13, 14, 17, 18, 19]

  with st.expander(
      "📅 試合情報（日付・試合名） & 👥 スタメン（1〜9番）編集",
      expanded=False,
  ):
    st.caption("📅 試合日")
    d_c1, d_c2, d_c3 = st.columns(3)
    years = list(range(2024, 2031))
    year_idx = (
        years.index(st.session_state.year)
        if st.session_state.year in years
        else years.index(today.year)
    )
    selected_year = d_c1.selectbox(
        "年", years, index=year_idx, label_visibility="collapsed"
    )

    months = list(range(1, 13))
    month_idx = (
        months.index(st.session_state.month)
        if st.session_state.month in months
        else months.index(today.month)
    )
    selected_month = d_c2.selectbox(
        "月", months, index=month_idx, label_visibility="collapsed"
    )

    days = list(range(1, 32))
    day_idx = (
        days.index(st.session_state.day)
        if st.session_state.day in days
        else days.index(today.day)
    )
    selected_day = d_c3.selectbox(
        "日", days, index=day_idx, label_visibility="collapsed"
    )

    try:
      formatted_date = date(selected_year, selected_month, selected_day)
    except ValueError:
      formatted_date = date(selected_year, selected_month, 28)

    st.session_state.year = selected_year
    st.session_state.month = selected_month
    st.session_state.day = selected_day

    raw_game_id = st.text_input("試合名", value=st.session_state.game_id)
    st.session_state.game_id = raw_game_id.strip() or "公式戦"

    st.markdown("---")
    st.markdown("##### 👥 スタメン（1〜9番）編集")
    new_lineup = []
    for row_idx in range(3):
      l_cols = st.columns(3)
      for col_idx in range(3):
        i = row_idx * 3 + col_idx
        with l_cols[col_idx]:
          p_info = st.session_state.lineup[i]
          c1, c2 = st.columns([2, 1])
          raw_name = c1.text_input(
              f"{i+1}番打者", value=p_info["name"], key=f"player_name_{i}"
          )
          p_side = c2.radio(
              f"打順{i+1}打席",
              ["R", "L", "S"],
              index=["R", "L", "S"].index(p_info["side"]),
              key=f"player_side_{i}",
              horizontal=True,
          )
          clean_name = raw_name.strip() or f"打者{i+1}"
          new_lineup.append({"name": clean_name, "side": p_side})

    st.session_state.lineup = new_lineup

  top_bar_col1, top_bar_col2, top_bar_col3 = st.columns([1.5, 2.5, 1.5])

  with top_bar_col1:
    raw_pitcher_name = st.text_input(
        "投手名", value=st.session_state.pitcher_name
    )
    st.session_state.pitcher_name = raw_pitcher_name.strip() or "あお"

  with top_bar_col2:
    lineup_labels = [
        f"{i+1}番: {p['name']} ({p['side']}打ち)"
        for i, p in enumerate(st.session_state.lineup)
    ]
    lineup_signature = "_".join(lineup_labels)

    selected_lineup_idx = st.selectbox(
        "現在の打者を選択",
        range(9),
        format_func=lambda i: lineup_labels[i],
        index=st.session_state.lineup_index,
        key=f"batter_select_box_{lineup_signature}",
    )

    if selected_lineup_idx != st.session_state.lineup_index:
      st.session_state.lineup_index = selected_lineup_idx
      selected_p = st.session_state.lineup[selected_lineup_idx]
      st.session_state.current_batter_side = (
          "L" if selected_p["side"] == "L" else "R"
      )
      st.rerun()

    active_player = st.session_state.lineup[st.session_state.lineup_index]
    st.session_state.batter_name = active_player["name"]

  with top_bar_col3:
    default_side = "L" if active_player["side"] == "L" else "R"
    side_options = ["R", "L"]

    if "current_batter_side" not in st.session_state:
      st.session_state.current_batter_side = default_side

    side_idx = (
        side_options.index(st.session_state.current_batter_side)
        if st.session_state.current_batter_side in side_options
        else side_options.index(default_side)
    )

    batter_side = st.radio(
        "打席", side_options, index=side_idx, horizontal=True
    )
    st.session_state.current_batter_side = batter_side

  info_col1, info_col2, info_col3 = st.columns(3)

  with info_col1:
    inning_options = [
        "1回表",
        "1回裏",
        "2回表",
        "2回裏",
        "3回表",
        "3回裏",
        "4回表",
        "4回裏",
        "5回表",
        "5回裏",
        "6回表",
        "6回裏",
        "7回表",
        "7回裏",
        "8回表",
        "8回裏",
        "9回表",
        "9回裏",
        "延長1回表〜",
    ]
    selected_inning = st.selectbox("イニング", inning_options)

  with info_col2:
    out_options = [0, 1, 2]
    selected_outs = st.selectbox(
        "アウト数", out_options, index=st.session_state.outs
    )
    st.session_state.outs = selected_outs

  with info_col3:
    runner_options = [
        "なし",
        "1塁",
        "2塁",
        "3塁",
        "1,2塁",
        "1,3塁",
        "2,3塁",
        "満塁",
    ]
    selected_runner = st.selectbox("ランナー", runner_options)

  st.markdown("---")

  det_col1, det_col2, det_col3 = st.columns([1.2, 1.8, 2.2])

  with det_col1:
    count_options = [
        "0-0",
        "1-0",
        "2-0",
        "3-0",
        "0-1",
        "1-1",
        "2-1",
        "3-1",
        "0-2",
        "1-2",
        "2-2",
        "3-2",
    ]
    current_count_str = f"{st.session_state.balls}-{st.session_state.strikes}"
    default_index = (
        count_options.index(current_count_str)
        if current_count_str in count_options
        else 0
    )
    selected_count = st.selectbox(
        "カウント", count_options, index=default_index
    )

    b_str, s_str = selected_count.split("-")
    st.session_state.balls = int(b_str)
    st.session_state.strikes = int(s_str)

  with det_col2:
    standard_pitch_types = [
        "ストレート",
        "カーブ",
        "スライダー",
        "カットボール",
        "フォーク",
        "チェンジアップ",
        "シンカー",
        "シュート",
        "その他（自由入力）",
    ]
    selected_p_type = st.selectbox("球種", standard_pitch_types)

    if selected_p_type == "その他（自由入力）":
      raw_custom_pitch = st.text_input(
          "球種名を入力", value="ツーシーム", key="custom_pitch"
      )
      pitch_type = raw_custom_pitch.strip() or "その他"
    else:
      pitch_type = selected_p_type

  with det_col3:
    is_curr_strike = st.session_state.selected_course in strike_zones

    base_result_options = [
        "ボール",
        "見逃しストライク",
        "空振り",
        "ファウル",
        "安打（レフト前）",
        "安打（センター前）",
        "安打（ライト前）",
        "長打（二塁打）",
        "長打（三塁打）",
        "本塁打",
        "ゴロアウト（内野）",
        "フライアウト（外野）",
        "空振り三振",
        "見逃し三振",
        "四球",
        "死球",
        "その他（野手選択など）",
    ]

    filtered_result_options = []
    for opt in base_result_options:
      if st.session_state.balls == 3 and opt == "ボール":
        continue
      if st.session_state.strikes == 2 and opt in [
          "見逃しストライク",
          "空振り",
      ]:
        continue
      filtered_result_options.append(opt)

    if is_curr_strike:
      default_target = (
          "見逃し三振" if st.session_state.strikes == 2 else "見逃しストライク"
      )
    else:
      default_target = "四球" if st.session_state.balls == 3 else "ボール"

    default_result_idx = (
        filtered_result_options.index(default_target)
        if default_target in filtered_result_options
        else 0
    )

    result = st.selectbox(
        "結果（打球方向含む）", filtered_result_options, index=default_result_idx
    )

  st.divider()

  is_curr_strike = st.session_state.selected_course in strike_zones
  zone_label = (
      "⚡ 【ストライクゾーン】" if is_curr_strike else "🛡️ 【ボールゾーン】"
  )

  st.markdown(
      f"##### 🥎 コース選択（📍 選択中: **{st.session_state.selected_course}番** {zone_label}）"
  )
  st.caption(
      "🎯 中央がストライクゾーン、外周がボールゾーンです（ワンタップで確実選択）"
  )

  st.markdown('<div class="catcher-board">', unsafe_allow_html=True)

  for r in range(5):
    cols = st.columns(5)
    for c in range(5):
      zone_num = r * 5 + c + 1
      is_selected = zone_num == st.session_state.selected_course
      is_strike = zone_num in strike_zones

      if is_selected:
        btn_kind = "primary"
        label = f"★ {zone_num}"
      else:
        btn_kind = "secondary"
        if is_strike:
          label = f"◆ {zone_num}"
        else:
          label = f"{zone_num}"

      with cols[c]:
        if st.button(
            label,
            key=f"zone_btn_{zone_num}",
            type=btn_kind,
            use_container_width=True,
        ):
          st.session_state.selected_course = zone_num
          st.rerun()

  st.markdown("</div>", unsafe_allow_html=True)

  st.markdown("<br>", unsafe_allow_html=True)

  if st.button("💾 この投球を登録して次へ", type="primary", use_container_width=True):
    current_b = st.session_state.balls
    current_s = st.session_state.strikes
    current_outs = st.session_state.outs

    new_data = pd.DataFrame([{
        "日付": str(formatted_date),
        "試合ID": st.session_state.game_id,
        "投手名": st.session_state.pitcher_name,
        "打者名": st.session_state.batter_name,
        "打者左右": batter_side,
        "イニング": selected_inning,
        "アウト数": current_outs,
        "ランナー": selected_runner,
        "ボール": current_b,
        "ストライク": current_s,
        "球種": pitch_type,
        "コース": st.session_state.selected_course,
        "結果": result,
    }])

    new_data.to_csv(
        CSV_FILE, mode="a", header=False, index=False, encoding="utf-8-sig"
    )

    is_at_bat_over = False

    if result == "ボール":
      if current_b < 3:
        st.session_state.balls += 1
      else:
        st.session_state.balls = 0
        st.session_state.strikes = 0
        current_outs = min(2, current_outs + 1)
        is_at_bat_over = True
    elif result in ["見逃しストライク", "空振り"]:
      if current_s < 2:
        st.session_state.strikes += 1
      else:
        st.session_state.balls = 0
        st.session_state.strikes = 0
        st.session_state.outs = (
            (current_outs + 1) if current_outs < 2 else 0
        )
        is_at_bat_over = True
    elif result == "ファウル":
      if current_s < 2:
        st.session_state.strikes += 1
    else:
      st.session_state.balls = 0
      st.session_state.strikes = 0
      if "アウト" in result or "三振" in result:
        st.session_state.outs = (current_outs + 1) if current_outs < 2 else 0
      is_at_bat_over = True

    if is_at_bat_over:
      next_index = (st.session_state.lineup_index + 1) % 9
      st.session_state.lineup_index = next_index
      next_player = st.session_state.lineup[next_index]
      st.session_state.current_batter_side = (
          "L" if next_player["side"] == "L" else "R"
      )

    new_b = st.session_state.balls
    new_s = st.session_state.strikes
    st.success(
        f"✅ 登録完了しました！ ➔ 次のカウント: 【 B: {new_b} - S: {new_s} 】"
    )

    st.markdown(
        """
        <script>
            window.scrollTo({top: 0, behavior: 'smooth'});
        </script>
        """,
        unsafe_allow_html=True,
    )
    st.rerun()

  st.markdown("<br><br><br>", unsafe_allow_html=True)


# ==========================================
# 共通関数: 統合フィルターパネル
# ==========================================
def render_comprehensive_filter(df, key_prefix="filter"):
  filtered_df = df.copy()

  with st.expander("🔍 絞り込みフィルターを開く", expanded=False):
    df["日付_dt"] = pd.to_datetime(df["日付"], errors="coerce")
    min_date = df["日付_dt"].min().date() if not df.empty else date.today()
    max_date = df["日付_dt"].max().date() if not df.empty else date.today()

    col_d1, col_d2 = st.columns(2)
    with col_d1:
      start_date = st.date_input(
          "開始日", value=min_date, key=f"{key_prefix}_start"
      )
    with col_d2:
      end_date = st.date_input(
          "終了日", value=max_date, key=f"{key_prefix}_end"
      )

    date_mask = (df["日付_dt"].dt.date >= start_date) & (
        df["日付_dt"].dt.date <= end_date
    )
    filtered_df = df[date_mask].drop(columns=["日付_dt"])

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    with f_col1:
      games = ["すべて"] + sorted(list(df["試合ID"].dropna().unique()))
      selected_game = st.selectbox("試合名", games, key=f"{key_prefix}_game")

      pitchers = ["すべて"] + sorted(list(df["投手名"].dropna().unique()))
      selected_pitcher = st.selectbox(
          "投手名", pitchers, key=f"{key_prefix}_pitcher"
      )

    with f_col2:
      batters = ["すべて"] + sorted(list(df["打者名"].dropna().unique()))
      selected_batter = st.selectbox(
          "打者名", batters, key=f"{key_prefix}_batter"
      )

      sides = ["すべて", "R", "L"]
      selected_side = st.selectbox("打席", sides, key=f"{key_prefix}_side")

    with f_col3:
      df_temp = filtered_df.copy()
      df_temp["カウント"] = (
          df_temp["ボール"].astype(str)
          + "-"
          + df_temp["ストライク"].astype(str)
      )
      counts = ["すべて"] + sorted(list(df_temp["カウント"].unique()))
      selected_count = st.selectbox(
          "カウント", counts, key=f"{key_prefix}_count"
      )

      pitch_types = ["すべて"] + sorted(list(df["球種"].dropna().unique()))
      selected_p_type = st.selectbox(
          "球種", pitch_types, key=f"{key_prefix}_ptype"
      )

    with f_col4:
      results = ["すべて"] + sorted(list(df["結果"].dropna().unique()))
      selected_result = st.selectbox(
          "投球結果", results, key=f"{key_prefix}_result"
      )

    if selected_game != "すべて":
      filtered_df = filtered_df[filtered_df["試合ID"] == selected_game]
    if selected_pitcher != "すべて":
      filtered_df = filtered_df[filtered_df["投手名"] == selected_pitcher]
    if selected_batter != "すべて":
      filtered_df = filtered_df[filtered_df["打者名"] == selected_batter]
    if selected_side != "すべて":
      filtered_df = filtered_df[filtered_df["打者左右"] == selected_side]
    if selected_count != "すべて":
      filtered_df["temp_cnt"] = (
          filtered_df["ボール"].astype(str)
          + "-"
          + filtered_df["ストライク"].astype(str)
      )
      filtered_df = filtered_df[filtered_df["temp_cnt"] == selected_count].drop(
          columns=["temp_cnt"]
      )
    if selected_p_type != "すべて":
      filtered_df = filtered_df[filtered_df["球種"] == selected_p_type]
    if selected_result != "すべて":
      filtered_df = filtered_df[filtered_df["結果"] == selected_result]

  return filtered_df


# ==========================================
# 【タブ3】打席一覧・1球データ詳細
# ==========================================
with tab3:
  st.subheader("🗂️ 打席一覧・1球データ詳細")

  df_all = pd.read_csv(CSV_FILE, encoding="utf-8-sig")

  if df_all.empty:
    st.info("登録されているデータはありません。")
  else:
    df_with_group = df_all.copy()
    group_id = 0
    df_with_group["group_id"] = 0

    for i in range(len(df_with_group)):
      if i > 0:
        prev = df_with_group.iloc[i - 1]
        curr = df_with_group.iloc[i]
        if (
            prev["試合ID"] != curr["試合ID"]
            or prev["投手名"] != curr["投手名"]
            or prev["打者名"] != curr["打者名"]
            or prev["日付"] != curr["日付"]
            or prev["イニング"] != curr["イニング"]
        ):
          group_id += 1
      df_with_group.iat[i, df_with_group.columns.get_loc("group_id")] = group_id

    df_matched_pitches = render_comprehensive_filter(
        df_with_group, key_prefix="tab3_filter"
    )

    if df_matched_pitches.empty:
      st.info("指定されたフィルター条件に一致するデータはありません。")
    else:
      matched_group_ids = df_matched_pitches["group_id"].unique()
      df_picked_at_bats = df_with_group[
          df_with_group["group_id"].isin(matched_group_ids)
      ]

      ab_summary_list = []
      for g_id, g_df in df_picked_at_bats.groupby("group_id"):
        last_row = g_df.iloc[-1]
        ab_summary_list.append({
            "打席ID": g_id,
            "日付": last_row["日付"],
            "試合名": last_row["試合ID"],
            "イニング": last_row["イニング"],
            "投手": last_row["投手名"],
            "打者": last_row["打者名"],
            "打順左右": last_row["打者左右"],
            "投球数": len(g_df),
            "最終結果": last_row["結果"],
        })

      df_ab_summary = pd.DataFrame(ab_summary_list)

      st.markdown(
          f"##### 📋 抽出された打席一覧（条件に合致する球が含まれる打席: **{len(df_ab_summary)}件**）"
      )
      st.dataframe(
          df_ab_summary.drop(columns=["打席ID"]),
          use_container_width=True,
          hide_index=True,
      )

      st.divider()

      st.markdown("#### 🔍 ピックアップされた打席を選択して詳細を確認")

      ab_options = {}
      for idx, row in df_ab_summary.iterrows():
        label = f"[{row['日付']} {row['試合名']} {row['イニング']}] 投手:{row['投手']} vs 打者:{row['打者']} ({row['投球数']}球 - 結果: {row['最終結果']})"
        ab_options[label] = row["打席ID"]

      selected_ab_label = st.selectbox(
          "詳細を見たい打席を選択", list(ab_options.keys())
      )
      selected_ab_id = ab_options[selected_ab_label]

      selected_pitches = df_with_group[
          df_with_group["group_id"] == selected_ab_id
      ].copy()
      selected_pitches["球数"] = [
          f"{i+1}球目" for i in range(len(selected_pitches))
      ]
      selected_pitches["カウント(B-S)"] = (
          selected_pitches["ボール"].astype(str)
          + "-"
          + selected_pitches["ストライク"].astype(str)
      )

      display_cols = [
          "球数",
          "イニング",
          "アウト数",
          "ランナー",
          "カウント(B-S)",
          "球種",
          "コース",
          "結果",
      ]
      st.markdown(f"**【選択中の打席の全配球詳細】** `{selected_ab_label}`")
      st.dataframe(
          selected_pitches[display_cols],
          use_container_width=True,
          hide_index=True,
      )

      st.divider()

      col_del1, col_del2 = st.columns(2)

      with col_del1:
        st.markdown("##### 🗑️ 選択中の打席を丸ごと削除")
        confirm_ab_delete = st.checkbox(
            "この打席の削除を確認する", key="ab_delete_check"
        )
        if st.button(
            "選択中の打席データを削除実行",
            type="primary",
            disabled=not confirm_ab_delete,
        ):
          df_real_updated = df_all.copy()
          for _, r in selected_pitches.iterrows():
            idx_match = df_real_updated[
                (df_real_updated["日付"] == r["日付"])
                & (df_real_updated["試合ID"] == r["試合ID"])
                & (df_real_updated["投手名"] == r["投手名"])
                & (df_real_updated["打者名"] == r["打者名"])
                & (df_real_updated["イニング"] == r["イニング"])
                & (df_real_updated["コース"] == r["コース"])
                & (df_real_updated["結果"] == r["結果"])
            ].index
            if not idx_match.empty:
              df_real_updated = df_real_updated.drop(index=idx_match[0])

          df_real_updated.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
          st.success("指定した打席のデータを削除しました。")
          st.rerun()

      with col_del2:
        st.markdown("##### ⚠️ 全データの一括クリア")
        confirm_clear = st.checkbox(
            "全データ削除を確認する（復元不可）", key="ab_clear_check"
        )
        if st.button(
            "全データ一括削除を実行",
            disabled=not confirm_clear,
            key="ab_clear_btn",
        ):
          empty_df = pd.DataFrame(
              columns=[
                  "日付",
                  "試合ID",
                  "投手名",
                  "打者名",
                  "打者左右",
                  "イニング",
                  "アウト数",
                  "ランナー",
                  "ボール",
                  "ストライク",
                  "球種",
                  "コース",
                  "結果",
              ]
          )
          empty_df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
          st.success("すべてのデータをクリアしました。")
          st.rerun()


# ==========================================
# 【タブ4】配球ヒートマップ分析 ＆ 各球種の投球割合集計
# ==========================================
with tab4:
  st.subheader("🔥 25分割 配球ヒートマップ分析 ＆ 球種割合")

  df_current = pd.read_csv(CSV_FILE, encoding="utf-8-sig")

  if df_current.empty:
    st.warning("データがまだ登録されていません。")
  else:
    df_filtered = render_comprehensive_filter(
        df_current, key_prefix="heatmap_filter"
    )

    if df_filtered.empty:
      st.info("指定されたフィルター条件に一致する投球データはありません。")
    else:
      total_pitches = len(df_filtered)

      st.divider()

      st.markdown("#### 📊 各球種の投球割合（集計）")

      pitch_summary = (
          df_filtered["球種"]
          .value_counts()
          .reset_index(name="投球数")
      )
      pitch_summary.columns = ["球種", "投球数"]
      pitch_summary["割合 (%)"] = (
          (pitch_summary["投球数"] / total_pitches) * 100
      ).round(1)

      sum_col1, sum_col2 = st.columns([1, 1.2])

      with sum_col1:
        st.dataframe(
            pitch_summary, use_container_width=True, hide_index=True
        )

      with sum_col2:
        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=pitch_summary["球種"],
                    values=pitch_summary["投球数"],
                    hole=0.4,
                    textinfo="label+percent",
                )
            ]
        )
        fig_pie.update_layout(
            title="球種割合グラフ",
            margin=dict(t=30, b=10, l=10, r=10),
            height=280,
        )
        st.plotly_chart(
            fig_pie,
            use_container_width=True,
            config={
                "scrollZoom": False,
                "displayModeBar": False,
                "staticPlot": True,
            },
        )

      st.divider()

      counts = np.zeros((5, 5))
      for course_num in df_filtered["コース"]:
        if 1 <= course_num <= 25:
          r = (course_num - 1) // 5
          c = (course_num - 1) % 5
          counts[r, c] += 1

      text_matrix = []
      for r_idx, row in enumerate(counts):
        row_texts = []
        for c_idx, val in enumerate(row):
          cnt = int(val)
          if total_pitches > 0:
            pct = (cnt / total_pitches) * 100
            row_texts.append(f"{pct:.1f}%")
          else:
            row_texts.append("0.0%")
        text_matrix.append(row_texts)

      x_vals = [1, 2, 3, 4, 5]
      y_vals = [1, 2, 3, 4, 5]

      fig = go.Figure(
          data=go.Heatmap(
              z=counts,
              x=x_vals,
              y=y_vals,
              colorscale="Reds",
              text=text_matrix,
              texttemplate="%{text}",
              textfont={"size": 14},
          )
      )

      fig.add_shape(
          type="rect",
          x0=1.5,
          y0=1.5,
          x1=4.5,
          y1=4.5,
          line=dict(color="yellow", width=5),
          layer="above",
      )

      fig.update_yaxes(autorange="reversed", dtick=1)
      fig.update_xaxes(dtick=1)

      fig.update_layout(
          title=f"投球コース分布 (条件合致 投球数: {total_pitches}球)",
          xaxis_title="コース(横)",
          yaxis_title="コース(縦)",
      )

      fig.update_xaxes(fixedrange=True)
      fig.update_yaxes(fixedrange=True)

      st.plotly_chart(
          fig,
          use_container_width=True,
          config={
              "scrollZoom": False,
              "displayModeBar": False,
              "staticPlot": True,
          },
      )