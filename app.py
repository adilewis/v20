import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

# הגדרת תצוגת האתר (UI)
st.set_page_config(page_title="V20 Master Predictor", page_icon="⚽", layout="wide")

st.title("🏆 V20 Master Predictor - Pro Dashboard")
st.markdown("מערכת ניתוח הנתונים המתקדמת לזיהוי ערך סטטיסטי במשחקי כדורגל (מבוסס מנוע V20).")

# תפריט צדדי (Sidebar)
st.sidebar.header("הגדרות מערכת")
api_key = st.sidebar.text_input("הכנס מפתח API (מוצפן)", type="password", value="8c18c97267fd1e32b0be49849a2b4d83")
target_date = st.sidebar.date_input("בחר תאריך משחקים", datetime.today())

# ליגות
leagues_dict = {
    "Core": [283, 284, 39, 40, 140, 141, 78, 79, 135, 136, 61, 62, 88, 94, 144],
    "Added": [203, 197, 179, 345],
    "Europe_Cups": [2, 3, 848]
}
all_ids = [i for sub in leagues_dict.values() for i in sub]

headers = {'x-apisports-key': api_key}
url_fix = "https://v3.football.api-sports.io/fixtures"
url_standings = "https://v3.football.api-sports.io/standings"

@st.cache_data(ttl=3600) # שומר את הטבלאות בזיכרון של השרת לשעה כדי לחסוך קריאות API
def get_league_ranks():
    ranks = {}
    for lid in all_ids:
        if lid in [2, 3, 848]: continue
        try:
            res = requests.get(url_standings, headers=headers, params={"league": lid, "season": 2025}).json()
            standings = res.get('response', [])
            if standings:
                for team in standings[0]['league']['standings'][0]:
                    ranks[team['team']['id']] = team['rank']
        except: pass
        time.sleep(0.05)
    return ranks

if st.sidebar.button("🚀 הרץ ניתוח V20"):
    with st.spinner('סורק עשרות משחקים ומחשב חובות כיבוש... אנא המתן.'):
        team_ranks = get_league_ranks()
        date_str = target_date.strftime("%Y-%m-%d")
        res = requests.get(url_fix, headers=headers, params={"date": date_str}).json()
        matches = [m for m in res.get('response', []) if m['league']['id'] in all_ids]

        if not matches:
            st.warning(f"אין משחקים רלוונטיים בתאריך {date_str}.")
        else:
            b_pred, u_anal, s_break, ht_live, s_debt, c_debt = [], [], [], [], [], []
            
            # סרגל התקדמות ויזואלי ללקוח
            progress_text = "מנתח נתוני עומק..."
            my_bar = st.progress(0, text=progress_text)
            
            for index, match in enumerate(matches):
                h, a = match['teams']['home'], match['teams']['away']
                
                # לוגיקת V20 (מוסתרת למען קריאות - הלוגיקה זהה בדיוק לפייתון הקודם)
                def get_all_stats(t_id):
                    res_p = requests.get(url_fix, headers=headers, params={"team": t_id, "last": 20}).json()
                    past = [f for f in res_p.get('response', []) if f['fixture']['status']['short'] in ['FT', 'AET', 'PEN']]
                    if len(past) < 10: return None
                    b_list, u_list, res_list, ht_list = [], [], [], []
                    u_streak, r_streak, r_type, ht_active_count = 0, 0, None, 0
                    for i, f in enumerate(past[:10]):
                        ish = f['teams']['home']['id'] == t_id
                        total = (f['goals']['home'] or 0) + (f['goals']['away'] or 0)
                        b_list.append("Yes" if (f['goals']['home'] > 0 and f['goals']['away'] > 0) else "No")
                        u_list.append("U" if total < 1.5 else "O")
                        if total < 1.5 and u_streak == i: u_streak += 1
                        ht_sc = (f['score']['halftime']['home'] if ish else f['score']['halftime']['away']) or 0
                        ht_con = (f['score']['halftime']['away'] if ish else f['score']['halftime']['home']) or 0
                        ht_list.append(f"{ht_sc}:{ht_con}")
                        if ht_sc > 0 or ht_con > 0: ht_active_count += 1
                        rv = "W" if (ish and f['goals']['home']>f['goals']['away']) or (not ish and f['goals']['away']>f['goals']['home']) else "L" if (ish and f['goals']['home']<f['goals']['away']) or (not ish and f['goals']['away']<f['goals']['home']) else "D"
                        res_list.append(rv)
                        if i == 0: r_type = rv
                        if rv == r_type and r_streak == i: r_streak += 1
                    avg_sc = sum((f['goals']['home'] if f['teams']['home']['id'] == t_id else f['goals']['away']) or 0 for f in past) / len(past)
                    avg_con = sum((f['goals']['away'] if f['teams']['home']['id'] == t_id else f['goals']['home']) or 0 for f in past) / len(past)
                    debt_4 = avg_sc - (sum((f['goals']['home'] if f['teams']['home']['id'] == t_id else f['goals']['away']) or 0 for f in past[:4]) / 4)
                    con_debt_4 = avg_con - (sum((f['goals']['away'] if f['teams']['home']['id'] == t_id else f['goals']['home']) or 0 for f in past[:4]) / 4)
                    return {"b_l": " | ".join(b_list), "u_l": " | ".join(u_list), "r_l": " | ".join(res_list), "ht_l": " | ".join(ht_list), "u_s": u_streak, "r_s": r_streak, "r_t": r_type, "debt": debt_4, "c_debt": con_debt_4, "b_p": b_list.count("Yes")*10, "rank": team_ranks.get(t_id, "-"), "ht_active": ht_active_count, "avg_tot": sum((f['goals']['home'] or 0)+(f['goals']['away'] or 0) for f in past)/len(past)}

                h_s, a_s = get_all_stats(h['id']), get_all_stats(a['id'])
                time.sleep(0.05)
                
                if h_s and a_s:
                    bp = min(96, (h_s['b_p']+a_s['b_p'])/2 + (h_s['debt']+a_s['debt'])*18 + 15)
                    b_pred.append({"משחק": f"{h['name']} - {a['name']}", "מיקומים (ב/ח)": f"{h_s['rank']}/{a_s['rank']}", "בית 10אח'": h_s['b_l'], "חוץ 10אח'": a_s['b_l'], "סיכוי BTTS %": int(bp)})
                    for s, sn, on, os in [(h_s, h['name'], a['name'], a_s), (a_s, a['name'], h['name'], h_s)]:
                        if s['u_s'] > 0: u_anal.append({"קבוצה": sn, "נגד": on, "מיקומים (ק/נ)": f"{s['rank']}/{os['rank']}", "רצף אנדר": s['u_s'], "סיכוי שבירה O1.5 %": int(min(98, 55 + s['u_s']*10 + os['avg_tot']*5))})
                        if s['r_s'] >= 3: s_break.append({"קבוצה": sn, "רצף": f"{s['r_s']} {s['r_t']}", "נגד": on, "סיכוי שבירה %": int(min(95, s['r_s']*15+20))})
                    htp = min(98, (h_s['ht_active'] + a_s['ht_active'])*5 + 20)
                    ht_live.append({"משחק": f"{h['name']} - {a['name']}", "מיקומים (ב/ח)": f"{h_s['rank']}/{a_s['rank']}", "בית HT": h_s['ht_l'], "חוץ HT": a_s['ht_l'], "סיכוי לגול HT %": int(htp)})
                    s_debt.append({"משחק": f"{h['name']} - {a['name']}", "מיקומים (ב/ח)": f"{h_s['rank']}/{a_s['rank']}", "חוב משוקלל": round(h_s['debt'] + a_s['debt'], 2), "סיכוי לגול %": int(min(95, 45 + max(h_s['debt'], a_s['debt'])*25))})
                    c_debt.append({"משחק": f"{h['name']} - {a['name']}", "מיקומים (ב/ח)": f"{h_s['rank']}/{a_s['rank']}", "חוב ספיגה משוקלל": round(h_s['c_debt'] + a_s['c_debt'], 2), "סיכוי לספיגה %": int(min(95, 45 + max(h_s['c_debt'], a_s['c_debt'])*25))})

                my_bar.progress((index + 1) / len(matches), text=f"מנתח משחק {index + 1} מתוך {len(matches)}")
            
            time.sleep(1)
            my_bar.empty()
            st.success("הניתוח הושלם בהצלחה!")

            # יצירת ממשק הלשוניות של האתר
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "BTTS Predictions", "Under 1.5 Analysis", "Streak Breaker", 
                "Halftime Live", "Scoring Debt", "Conceding Debt"
            ])
            
            with tab1: st.dataframe(pd.DataFrame(b_pred).sort_values("סיכוי BTTS %", ascending=False) if b_pred else pd.DataFrame(), use_container_width=True)
            with tab2: st.dataframe(pd.DataFrame(u_anal).sort_values("רצף אנדר", ascending=False) if u_anal else pd.DataFrame(), use_container_width=True)
            with tab3: st.dataframe(pd.DataFrame(s_break).sort_values("סיכוי שבירה %", ascending=False) if s_break else pd.DataFrame(), use_container_width=True)
            with tab4: st.dataframe(pd.DataFrame(ht_live).sort_values("סיכוי לגול HT %", ascending=False) if ht_live else pd.DataFrame(), use_container_width=True)
            with tab5: st.dataframe(pd.DataFrame(s_debt).sort_values("חוב משוקלל", ascending=False) if s_debt else pd.DataFrame(), use_container_width=True)
            with tab6: st.dataframe(pd.DataFrame(c_debt).sort_values("חוב ספיגה משוקלל", ascending=False) if c_debt else pd.DataFrame(), use_container_width=True)
