import io
import re
from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Invesmate Seminar Analytics Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.stApp {
    background:
      radial-gradient(circle at top right, rgba(99,102,241,.14), transparent 28%),
      radial-gradient(circle at top left, rgba(6,182,212,.10), transparent 24%),
      linear-gradient(180deg, #08101d 0%, #0b1220 100%);
}
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}
.kpi-card {
    background: linear-gradient(180deg, rgba(19,25,41,.96), rgba(12,18,32,.96));
    border: 1px solid rgba(99,102,241,.14);
    border-radius: 18px;
    padding: 18px;
    text-align: left;
    border-top: 3px solid var(--accent, #6366f1);
    box-shadow: 0 14px 32px rgba(2,6,23,.25);
}
.kpi-label {font-size: 11px; color: #7f8aa3; text-transform: uppercase; letter-spacing: .08em; font-weight: 700;}
.kpi-value {font-size: 30px; font-weight: 800; color: #edf2ff; margin: 6px 0 3px; letter-spacing: -.03em;}
.kpi-sub {font-size: 11px; color: #94a3b8;}
.section-header {
    font-size: 16px; font-weight: 800; color: #eef2ff; border-left: 4px solid #6366f1;
    padding-left: 12px; margin: 8px 0 16px 0;
}
.hero {
    background: linear-gradient(135deg, rgba(99,102,241,.18), rgba(6,182,212,.12));
    border: 1px solid rgba(99,102,241,.22);
    border-radius: 20px;
    padding: 20px 24px;
    margin-bottom: 14px;
}
.hero-title {font-size: 28px; font-weight: 800; color: #e5e7eb; margin-bottom: 4px;}
.hero-sub {color: #94a3b8; font-size: 13px;}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
[data-testid="stDateInputField"] {
    background: rgba(15,23,42,.88) !important;
    border: 1px solid rgba(148,163,184,.14) !important;
    border-radius: 12px !important;
}
label[data-testid="stWidgetLabel"] {
    color: #94a3b8 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: .06em !important;
}
.stMultiSelect [data-baseweb="tag"] {
    background: rgba(99,102,241,.16) !important;
    border: 1px solid rgba(99,102,241,.25) !important;
    border-radius: 999px !important;
}
button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 700 !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 1px solid rgba(148,163,184,.12);
}
.stTabs [data-baseweb="tab"] {
    background: rgba(15,23,42,.55);
    border-radius: 12px 12px 0 0;
    color: #94a3b8;
    font-weight: 700;
    padding: .7rem 1rem;
}
.stTabs [aria-selected="true"] {
    color: #eef2ff !important;
    background: rgba(99,102,241,.15) !important;
    border-bottom: 2px solid #6366f1 !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(148,163,184,.10);
    border-radius: 16px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

CHART_COLORS = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
    "#ef4444", "#f97316", "#ec4899", "#14b8a6", "#a855f7",
    "#3b82f6", "#84cc16",
]
PTI_MATCH = "Power Of Trading & Investing Combo Course"
CREDENTIALS = {"admin": "admin123", "invesmate": "invesmate@2024"}

# =========================================================
# HELPERS
# =========================================================
def clean_mobile(x):
    if pd.isna(x):
        return None
    s = re.sub(r"\D", "", str(x))
    return s[-10:] if len(s) >= 10 else None

def parse_date_series(series):
    for fmt in ["%d-%b-%Y", "%d-%b-%y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%b-%d-%Y", "%d %b %Y"]:
        parsed = pd.to_datetime(series, format=fmt, errors="coerce")
        if parsed.notna().any():
            return parsed
    return pd.to_datetime(series, errors="coerce", dayfirst=True)

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)

def fmt_inr(n):
    try:
        n = float(n)
        if n >= 1e7:
            return f"₹{n/1e7:.2f}Cr"
        if n >= 1e5:
            return f"₹{n/1e5:.2f}L"
        return f"₹{n:,.0f}"
    except Exception:
        return "₹0"

def load_excel_or_csv(file_obj, filename=None):
    name = (filename or "").lower()
    try:
        if name.endswith(".csv"):
            try:
                return pd.read_csv(file_obj)
            except Exception:
                file_obj.seek(0)
                return pd.read_csv(file_obj, encoding="latin1")
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(file_obj, sheet_name=0)
        try:
            return pd.read_excel(file_obj, sheet_name=0)
        except Exception:
            file_obj.seek(0)
            try:
                return pd.read_csv(file_obj)
            except Exception:
                file_obj.seek(0)
                return pd.read_csv(file_obj, encoding="latin1")
    except Exception as e:
        raise ValueError(f"Error reading file ({filename}): {e}") from e

def detect_col(df, candidates, required=False):
    norm = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        key = cand.strip().lower()
        if key in norm:
            return norm[key]
    if required:
        st.warning(f"Missing column from candidates: {candidates}")
    return None

def normalize_status(raw):
    raw = str(raw).strip().lower()
    if raw in ["active", "success", "completed", "paid"]:
        return "Active"
    if raw in ["inactive", "cancelled", "canceled", "failed", "refund", "refunded"]:
        return "Inactive"
    return raw.title() if raw else ""

def kpi_card(label, value, sub="", accent="#6366f1"):
    return f"""
    <div class="kpi-card" style="border-top-color:{accent}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>"""

def unique_nonblank(series):
    if series is None:
        return []
    vals = sorted(pd.Series(series).dropna().astype(str).map(str.strip).replace("", pd.NA).dropna().unique().tolist())
    return vals

# =========================================================
# DETAIL TABLE HELPER
# =========================================================
def render_section_student_details(title, df, extra_cols=None, key_prefix="sec"):
    st.markdown(f'<div class="section-header">👥 {title} — Student Details</div>', unsafe_allow_html=True)
    if df is None or df.empty:
        st.info("No student records available for the current filters.")
        return

    base_cols = [
        "name", "mobile", "place", "seminar_date_str", "session", "trainer",
        "seat_book_amount", "converted", "primary_course", "primary_order_date_str",
        "primary_paid", "primary_due", "primary_status", "webinar_type", "lead_source",
        "lead_status", "stage_name", "lead_owner", "match_reason"
    ]
    cols = [c for c in base_cols if c in df.columns]
    if extra_cols:
        for c in extra_cols:
            if c in df.columns and c not in cols:
                cols.append(c)

    show = df[cols].copy()
    if "converted" in show.columns:
        show["converted"] = show["converted"].map({True: "✅ Yes", False: "❌ No"})
    for c in ["seat_book_amount", "primary_paid", "additional_paid", "total_revenue"]:
        if c in show.columns:
            show[c] = show[c].apply(lambda x: fmt_inr(x) if pd.notna(x) and float(x) > 0 else "—")
    if "primary_due" in show.columns:
        show["primary_due"] = show["primary_due"].apply(lambda x: fmt_inr(x) if pd.notna(x) and float(x) > 0 else "₹0")
    if "additional_courses" in show.columns:
        show["additional_courses"] = show["additional_courses"].apply(lambda x: " | ".join(x) if isinstance(x, list) and x else "—")
    if "all_courses" in show.columns:
        show["all_courses"] = show["all_courses"].apply(lambda x: " | ".join(x) if isinstance(x, list) and x else "—")

    rename_map = {
        "name": "Name", "mobile": "Mobile", "place": "Location", "seminar_date_str": "Seminar Date",
        "session": "Session", "trainer": "Trainer", "seat_book_amount": "Seat Book Amt",
        "converted": "Converted", "primary_course": "Primary Course", "primary_order_date_str": "Order Date",
        "primary_paid": "Primary Paid", "primary_due": "Due", "primary_status": "Status",
        "webinar_type": "Lead Type", "lead_source": "Lead Source", "lead_status": "Lead Status",
        "stage_name": "Stage", "lead_owner": "Owner", "additional_courses": "Other Purchased Courses",
        "additional_paid": "Other Courses Revenue", "match_reason": "Match Reason",
        "total_revenue": "Total Revenue", "all_courses": "All Purchased Courses",
        "lead_service_name": "Lead Service",
    }
    show = show.rename(columns=rename_map)

    search = st.text_input(f"Search in {title} student details", key=f"{key_prefix}_search")
    if search:
        mask = show.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        show = show[mask]

    st.caption(f"{len(show)} students")
    st.dataframe(show, use_container_width=True, hide_index=True, height=380)
    st.download_button(
        f"⬇️ Download {title} Students CSV",
        show.to_csv(index=False).encode(),
        f"{key_prefix}_students.csv",
        "text/csv",
        key=f"{key_prefix}_dl"
    )

# =========================================================
# CORE DATA LOGIC
# =========================================================
@st.cache_data(show_spinner=False)
def process_data(sem_bytes, conv_bytes, leads_bytes, sem_name, conv_name, leads_name):
    sem = load_excel_or_csv(io.BytesIO(sem_bytes), sem_name)
    sem.columns = [str(c).strip() for c in sem.columns]

    c_mobile = detect_col(sem, ["Mobile", "Phone", "mobile", "phone", "Contact"])
    c_altmob = detect_col(sem, ["Alternate Number", "Alt Mobile", "alternate_number", "Alternate Mobile", "Alternative Mobile"])
    c_name = detect_col(sem, ["NAME", "Name", "Student Name", "name"])
    c_place = detect_col(sem, ["Place", "Location", "Venue", "City", "place"])
    c_trainer = detect_col(sem, ["Trainer / Presenter", "Trainer", "Presenter", "trainer"])
    c_semdate = detect_col(sem, ["Seminar Date", "Date", "seminar_date", "Event Date"])
    c_session = detect_col(sem, ["Session", "session", "Batch", "Time"])
    c_attended = detect_col(sem, ["Is Attended ?", "Attended", "is_attended", "attended"])
    c_amount = detect_col(sem, ["Amount Paid"], required=True)
    if c_amount is None:
        st.error("Amount Paid column not found in Seminar file")
        st.stop()

    sem["mobile_clean"] = sem[c_mobile].apply(clean_mobile) if c_mobile else None
    sem["alt_mobile_clean"] = sem[c_altmob].apply(clean_mobile) if c_altmob else None
    sem["seminar_date"] = parse_date_series(sem[c_semdate]) if c_semdate else pd.NaT
    sem["seat_book_amount"] = safe_numeric(sem[c_amount])
    sem["attended_flag"] = sem[c_attended].astype(str).str.strip().str.upper().isin(["YES", "TRUE", "1", "Y"]) if c_attended else False

    attendees = sem[
        ((sem["attended_flag"]) | (sem["seat_book_amount"] > 0)) &
        ((sem["mobile_clean"].notna()) | (sem["alt_mobile_clean"].notna()))
    ].copy().reset_index(drop=True)

    conv = load_excel_or_csv(io.BytesIO(conv_bytes), conv_name)
    conv.columns = [str(c).strip() for c in conv.columns]

    cc_mobile = detect_col(conv, ["phone", "Phone", "mobile", "Mobile", "Contact"])
    cc_service = detect_col(conv, ["service_name", "Service Name", "Course", "course_name", "ServiceName"])
    cc_orderdt = detect_col(conv, ["order_date", "Order Date", "OrderDate", "Date"])
    cc_payrec = detect_col(conv, ["payment_received", "Payment Received", "PaymentReceived", "amount_paid"])
    cc_gst = detect_col(conv, ["total_gst", "GST", "gst", "TotalGST"])
    cc_due = detect_col(conv, ["total_due", "Due", "total_due_amount", "TotalDue"])
    cc_trainer = detect_col(conv, ["trainer", "Trainer"])
    cc_salesrep = detect_col(conv, ["sales_rep_name", "Sales Rep", "SalesRep", "sales_rep"])
    cc_mode = detect_col(conv, ["payment_mode", "Payment Mode", "mode"])
    cc_status = detect_col(conv, ["status", "Status"])
    cc_orderid = detect_col(conv, ["orderID", "Order ID", "order_id", "OrderId"])

    conv["mobile_clean"] = conv[cc_mobile].apply(clean_mobile) if cc_mobile else None
    conv["order_date_clean"] = pd.to_datetime(conv[cc_orderdt], errors="coerce", utc=True).dt.tz_localize(None) if cc_orderdt else pd.NaT
    conv["payment_received"] = safe_numeric(conv[cc_payrec]) if cc_payrec else 0
    conv["total_gst"] = safe_numeric(conv[cc_gst]) if cc_gst else 0
    conv["total_due"] = safe_numeric(conv[cc_due]) if cc_due else 0
    conv["paid_amount"] = conv["payment_received"]
    conv["service_name_clean"] = conv[cc_service].astype(str).str.strip() if cc_service else ""
    conv["trainer_clean"] = conv[cc_trainer].astype(str).str.strip() if cc_trainer else ""
    conv["sales_rep_clean"] = conv[cc_salesrep].astype(str).str.strip() if cc_salesrep else ""
    conv["payment_mode_clean"] = conv[cc_mode].astype(str).str.strip() if cc_mode else ""
    conv["status_clean"] = conv[cc_status].astype(str).str.strip() if cc_status else ""
    conv["order_id_clean"] = conv[cc_orderid].astype(str).str.strip() if cc_orderid else ""

    leads = load_excel_or_csv(io.BytesIO(leads_bytes), leads_name)
    leads.columns = [str(c).strip() for c in leads.columns]

    lc_mobile = detect_col(leads, ["phone", "Phone", "mobile", "Mobile"])
    lc_convfrom = detect_col(leads, ["converted_from", "ConvertedFrom", "lead_type", "LeadType"])
    lc_source = detect_col(leads, ["leadsource", "lead_source", "LeadSource", "Source"])
    lc_campaign = detect_col(leads, ["campaign_name", "Campaign", "CampaignName"])
    lc_status = detect_col(leads, ["leadstatus", "lead_status", "LeadStatus", "Status"])
    lc_stage = detect_col(leads, ["stage_name", "StageName", "Stage"])
    lc_owner = detect_col(leads, ["leadownername", "LeadOwner", "lead_owner", "Owner"])
    lc_state = detect_col(leads, ["state", "State", "Province"])
    lc_attempted = detect_col(leads, ["Attempted/Unattempted", "attempted", "Attempted"])
    lc_service = detect_col(leads, ["servicename", "ServiceName", "service_name", "service"])
    lc_email = detect_col(leads, ["email", "Email"])
    lc_remarks = detect_col(leads, ["remarks", "Remarks", "Notes"])
    lc_name = detect_col(leads, ["name", "Name", "StudentName"])

    leads["mobile_clean"] = leads[lc_mobile].apply(clean_mobile) if lc_mobile else None
    leads["lead_service_clean"] = leads[lc_service].astype(str).str.strip() if lc_service else ""

    def get_best_lead(possible_mobiles: List[str], purchased_courses: List[str], primary_course: str):
        blank = {
            "webinar_type": "", "lead_source": "", "campaign_name": "", "lead_status": "",
            "stage_name": "", "lead_owner": "", "state": "", "attempted": "",
            "lead_service_name": "", "email": "", "remarks": "", "lead_name": ""
        }
        if not possible_mobiles or leads.empty:
            return blank

        lead_rows = leads[leads["mobile_clean"].isin(possible_mobiles)].copy()
        if lead_rows.empty:
            return blank

        chosen = pd.DataFrame()
        if primary_course:
            chosen = lead_rows[lead_rows["lead_service_clean"].str.lower() == str(primary_course).strip().lower()]
        if chosen.empty and purchased_courses:
            wanted = {str(c).strip().lower() for c in purchased_courses if str(c).strip()}
            chosen = lead_rows[lead_rows["lead_service_clean"].str.lower().isin(wanted)]
        if chosen.empty:
            chosen = lead_rows.iloc[[0]]

        r = chosen.iloc[0]

        def gs(col):
            return str(r[col]).strip() if col and col in r.index and pd.notna(r[col]) else ""

        wt = gs(lc_convfrom)
        if not wt:
            src = gs(lc_source)
            wt = "Webinar" if "WBN" in src.upper() else ("Non Webinar" if src else "")

        blank.update({
            "webinar_type": wt,
            "lead_source": gs(lc_source),
            "campaign_name": gs(lc_campaign),
            "lead_status": gs(lc_status),
            "stage_name": gs(lc_stage),
            "lead_owner": gs(lc_owner),
            "state": gs(lc_state),
            "attempted": gs(lc_attempted),
            "lead_service_name": gs("lead_service_clean"),
            "email": gs(lc_email),
            "remarks": gs(lc_remarks),
            "lead_name": gs(lc_name),
        })
        return blank

    rows, order_rows = [], []

    for _, row in attendees.iterrows():
        mob = row.get("mobile_clean")
        alt_mob = row.get("alt_mobile_clean")
        possible_mobiles = [m for m in [mob, alt_mob] if m]
        sem_dt = row["seminar_date"]

        entry = {
            "name": str(row.get(c_name, "")).strip() if c_name else "",
            "mobile": mob or alt_mob or "",
            "primary_mobile": mob or "",
            "alternate_mobile": alt_mob or "",
            "place": str(row.get(c_place, "")).strip() if c_place else "",
            "trainer": str(row.get(c_trainer, "")).strip() if c_trainer else "",
            "seminar_date": sem_dt,
            "session": str(row.get(c_session, "")).strip().upper() if c_session else "",
            "attended": bool(row.get("attended_flag", False)),
            "seat_book_amount": float(row.get("seat_book_amount", 0) or 0),
            "seat_booked": bool(float(row.get("seat_book_amount", 0) or 0) > 0),
            "primary_course": "",
            "primary_order_date": pd.NaT,
            "primary_paid": 0.0,
            "primary_due": 0.0,
            "primary_gst": 0.0,
            "primary_mode": "",
            "primary_status": "",
            "additional_courses": [],
            "additional_paid": 0.0,
            "all_courses": [],
            "total_revenue": 0.0,
            "converted": False,
            "trainer_conv": "",
            "sales_rep": "",
            "match_reason": "",
        }

        all_mobile_orders = conv[conv["mobile_clean"].isin(possible_mobiles)].sort_values("order_date_clean").copy() if possible_mobiles else pd.DataFrame()
        valid = all_mobile_orders.copy()

        if not possible_mobiles:
            entry["match_reason"] = "No mobile"
        elif all_mobile_orders.empty:
            entry["match_reason"] = "Mobile mismatch / no conversion row"
        else:
            if pd.notna(sem_dt) and all_mobile_orders["order_date_clean"].notna().any():
                after_cnt = int((all_mobile_orders["order_date_clean"] >= sem_dt).sum())
                entry["match_reason"] = "Matched (post seminar)" if after_cnt > 0 else "Matched (pre seminar)"
            else:
                entry["match_reason"] = "Matched"

        if not all_mobile_orders.empty:
            entry["primary_status"] = normalize_status(all_mobile_orders.iloc[-1]["status_clean"])

        if not valid.empty:
            entry["converted"] = True
            valid_after = valid[valid["order_date_clean"] >= sem_dt].copy() if pd.notna(sem_dt) else pd.DataFrame()
            primary_pool = valid_after if not valid_after.empty else valid
            pti_pool = primary_pool[primary_pool["service_name_clean"].str.contains(PTI_MATCH, na=False, case=False)]
            primary = pti_pool.iloc[0] if not pti_pool.empty else primary_pool.iloc[0]

            entry["primary_course"] = primary["service_name_clean"]
            entry["primary_order_date"] = primary["order_date_clean"]
            entry["primary_paid"] = float(primary["paid_amount"])
            entry["primary_due"] = float(primary["total_due"])
            entry["primary_gst"] = float(primary["total_gst"])
            entry["primary_mode"] = str(primary["payment_mode_clean"]).strip()
            entry["trainer_conv"] = str(primary["trainer_clean"]).strip()
            entry["sales_rep"] = str(primary["sales_rep_clean"]).strip()

            others = valid[valid.index != primary.name].copy()
            entry["additional_courses"] = list(others["service_name_clean"].dropna().astype(str).str.strip().unique())
            entry["additional_paid"] = float(others["paid_amount"].sum())
            entry["all_courses"] = list(valid["service_name_clean"].dropna().astype(str).str.strip().unique())
            entry["total_revenue"] = float(valid["paid_amount"].sum())

            for _, o in valid.iterrows():
                order_rows.append({
                    "name": entry["name"],
                    "mobile": entry["mobile"],
                    "place": entry["place"],
                    "seminar_date": sem_dt,
                    "seminar_date_str": sem_dt.strftime("%Y-%m-%d") if pd.notna(sem_dt) else "",
                    "course": str(o["service_name_clean"]).strip(),
                    "order_date": o["order_date_clean"],
                    "order_date_str": o["order_date_clean"].strftime("%Y-%m-%d") if pd.notna(o["order_date_clean"]) else "",
                    "paid_amount": float(o["paid_amount"]),
                    "total_due": float(o["total_due"]),
                    "total_gst": float(o["total_gst"]),
                    "payment_mode": str(o["payment_mode_clean"]).strip(),
                    "status": normalize_status(o["status_clean"]),
                    "sales_rep": str(o["sales_rep_clean"]).strip(),
                    "trainer_conv": str(o["trainer_clean"]).strip(),
                    "is_primary": bool(o.name == primary.name),
                    "order_id": str(o["order_id_clean"]).strip(),
                })

        entry.update(get_best_lead(possible_mobiles, entry["all_courses"], entry["primary_course"]))
        rows.append(entry)

    df = pd.DataFrame(rows)
    orders_df = pd.DataFrame(order_rows)

    if df.empty:
        df = pd.DataFrame(columns=[
            "name", "mobile", "primary_mobile", "alternate_mobile", "place", "trainer",
            "seminar_date", "session", "attended", "seat_book_amount", "seat_booked",
            "primary_course", "primary_order_date", "primary_paid", "primary_due",
            "primary_gst", "primary_mode", "primary_status", "additional_courses",
            "additional_paid", "all_courses", "total_revenue", "converted",
            "trainer_conv", "sales_rep", "webinar_type", "lead_source", "campaign_name",
            "lead_status", "stage_name", "lead_owner", "state", "attempted",
            "lead_service_name", "email", "remarks", "lead_name", "match_reason"
        ])

    for col in [
        "webinar_type", "lead_source", "campaign_name", "lead_status",
        "stage_name", "lead_owner", "state", "attempted", "lead_service_name",
        "email", "remarks", "lead_name", "match_reason"
    ]:
        if col not in df.columns:
            df[col] = ""

    df["seminar_date_str"] = pd.to_datetime(df["seminar_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    df["primary_order_date_str"] = pd.to_datetime(df["primary_order_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    df["due_zero"] = safe_numeric(df["primary_due"]) <= 0
    df["additional_course_count"] = df["additional_courses"].apply(lambda x: len(x) if isinstance(x, list) else 0)

    if not orders_df.empty:
        lead_meta = df[[
            "mobile", "webinar_type", "lead_source", "campaign_name", "lead_status",
            "stage_name", "lead_owner", "state", "attempted", "lead_service_name"
        ]].drop_duplicates("mobile")
        orders_df = orders_df.merge(lead_meta, on="mobile", how="left")
        orders_df["due_zero"] = safe_numeric(orders_df["total_due"]) <= 0

    return df, orders_df

# =========================================================
# RENDERERS
# =========================================================
def render_kpis(fdf):
    conv = fdf[fdf["converted"]].copy()
    total = len(fdf)
    n_conv = len(conv)
    rate = f"{(n_conv/total*100):.1f}%" if total else "0%"
    primary_paid = conv["primary_paid"].sum()
    additional_rev = conv["additional_paid"].sum()
    total_revenue = conv["total_revenue"].sum()
    total_due = conv["primary_due"].sum()
    fp = len(conv[conv["primary_due"] <= 0])
    hd = len(conv[conv["primary_due"] > 0])
    uniq_c = fdf["primary_course"].replace("", pd.NA).dropna().nunique()
    wbn = len(fdf[fdf["webinar_type"] == "Webinar"])
    non_wbn = len(fdf[fdf["webinar_type"] == "Non Webinar"])
    seat_book_count = len(fdf[fdf["seat_book_amount"] > 0])
    seat_book_amount = fdf["seat_book_amount"].sum()
    attempted = len(fdf[fdf["attempted"] == "Attempted"])
    unattempted = len(fdf[fdf["attempted"] == "Unattempted"])
    pti_buyers = len(conv[conv["primary_course"].astype(str).str.contains(PTI_MATCH, na=False, case=False)])
    cross_sellers = len(conv[conv["additional_course_count"] > 0])

    rows = [
        [
            ("Total Attendees", total, "Seminar rows after filters", "#6366f1"),
            ("Converted", n_conv, "Matched conversion rows", "#10b981"),
            ("Conversion Rate", rate, "Attendee → matched conversion", "#06b6d4"),
            ("Primary Revenue", fmt_inr(primary_paid), "Primary course only", "#f59e0b"),
            ("Other Courses Revenue", fmt_inr(additional_rev), "Additional purchased courses", "#a855f7"),
        ],
        [
            ("Total Revenue", fmt_inr(total_revenue), "Primary + other courses", "#22c55e"),
            ("Total Due", fmt_inr(total_due), "Outstanding dues", "#ef4444"),
            ("Seat Booked Count", seat_book_count, "Seminar Amount Paid > 0", "#14b8a6"),
            ("Seat Booked Amount", fmt_inr(seat_book_amount), "From seminar Amount Paid", "#3b82f6"),
            ("Unique Courses", uniq_c, "Distinct primary courses", "#8b5cf6"),
        ],
        [
            ("Fully Paid", fp, "Due ≤ 0", "#10b981"),
            ("Has Due", hd, "Pending balance", "#ef4444"),
            ("Webinar Leads", wbn, "Matched leads", "#06b6d4"),
            ("Non-Webinar Leads", non_wbn, "Matched leads", "#f97316"),
            ("Avg Revenue / Converted", fmt_inr(total_revenue/n_conv if n_conv else 0), "Total revenue per converted", "#f59e0b"),
        ],
        [
            ("Attempted Leads", attempted, "Lead intelligence", "#10b981"),
            ("Unattempted Leads", unattempted, "Lead intelligence", "#ef4444"),
            ("PTI Buyers", pti_buyers, "Primary PTI course", "#6366f1"),
            ("Cross-Sell Students", cross_sellers, "Bought >1 course", "#a855f7"),
            ("Cross-Sell Rate", f"{(cross_sellers/n_conv*100):.1f}%" if n_conv else "0%", "Converted → multi-course", "#06b6d4"),
        ],
    ]

    for row in rows:
        cols = st.columns(5)
        for i, (lbl, val, sub, clr) in enumerate(row):
            cols[i].markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

def render_overview(fdf):
    st.markdown('<div class="section-header">📅 Trends & Location Analysis</div>', unsafe_allow_html=True)

    bydate = fdf.groupby("seminar_date_str").agg(
        Attendees=("attended", "count"),
        Converted=("converted", "sum"),
        Revenue=("total_revenue", "sum"),
        SeatBookedAmount=("seat_book_amount", "sum"),
    ).reset_index()

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_bar(x=bydate["seminar_date_str"], y=bydate["Attendees"], name="Attendees")
        fig.add_bar(x=bydate["seminar_date_str"], y=bydate["Converted"], name="Converted")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", barmode="group", height=320)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.line(bydate, x="seminar_date_str", y="Revenue", markers=True, title="Revenue by Seminar Date")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320)
        st.plotly_chart(fig, use_container_width=True)

    byloc = fdf.groupby("place").agg(
        Attendees=("attended", "count"),
        Converted=("converted", "sum"),
        Revenue=("total_revenue", "sum"),
        SeatBookedAmount=("seat_book_amount", "sum"),
    ).reset_index().sort_values("Attendees", ascending=False).head(12)

    c3, c4 = st.columns(2)
    with c3:
        fig = go.Figure()
        fig.add_bar(x=byloc["place"], y=byloc["Attendees"], name="Attendees")
        fig.add_bar(x=byloc["place"], y=byloc["Converted"], name="Converted")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", barmode="group", height=320)
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        fig = px.bar(byloc.sort_values("Revenue", ascending=True), x="Revenue", y="place", orientation="h", title="Total Revenue by Location")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    c5, c6, c7 = st.columns(3)
    sess = fdf.groupby("session").size().reset_index(name="Count")
    with c5:
        if not sess.empty:
            fig = px.pie(sess, names="session", values="Count", title="Session Split", hole=0.4, color_discrete_sequence=CHART_COLORS)
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=280)
            st.plotly_chart(fig, use_container_width=True)
    lt = fdf.groupby("webinar_type").size().reset_index(name="Count")
    lt = lt[lt["webinar_type"].astype(str).str.strip() != ""]
    with c6:
        if not lt.empty:
            fig = px.pie(lt, names="webinar_type", values="Count", title="Webinar vs Non-Webinar", hole=0.4, color_discrete_sequence=CHART_COLORS)
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=280)
            st.plotly_chart(fig, use_container_width=True)
    with c7:
        fig = px.bar(byloc.sort_values("SeatBookedAmount", ascending=True), x="SeatBookedAmount", y="place", orientation="h", title="Seat Booked Amount by Location")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">👨‍🏫 Trainer Performance</div>', unsafe_allow_html=True)
    trainer = fdf.groupby("trainer").agg(
        Attendees=("attended", "count"),
        Converted=("converted", "sum"),
        Revenue=("total_revenue", "sum"),
        SeatBookedAmount=("seat_book_amount", "sum"),
    ).reset_index().sort_values("Attendees", ascending=False)
    c8, c9 = st.columns(2)
    with c8:
        fig = px.bar(trainer.head(12), x="trainer", y="Attendees", color="Converted", title="Trainer Attendees vs Converted")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, xaxis_tickangle=-30, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c9:
        fig = px.bar(trainer.head(12), x="Revenue", y="trainer", orientation="h", title="Revenue by Trainer")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

def render_courses(fdf):
    conv = fdf[fdf["converted"]].copy()
    if conv.empty:
        st.info("No converted students in current filter.")
        return

    byc = conv.groupby("primary_course").agg(
        Students=("attended", "count"),
        PrimaryRevenue=("primary_paid", "sum"),
        OtherRevenue=("additional_paid", "sum"),
        TotalRevenue=("total_revenue", "sum"),
        Due=("primary_due", "sum"),
        FullyPaid=("due_zero", "sum"),
    ).reset_index().sort_values("Students", ascending=False)
    byc["Share %"] = (byc["Students"] / byc["Students"].sum() * 100).round(1) if byc["Students"].sum() else 0

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(byc.head(12), x="Students", y="primary_course", orientation="h", title="Course-wise Student Count")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=360, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.pie(byc.head(10), names="primary_course", values="Students", title="Course Share by Student Count", hole=0.35, color_discrete_sequence=CHART_COLORS)
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=360)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig = px.bar(byc.head(12), x="TotalRevenue", y="primary_course", orientation="h", title="Total Revenue by Primary Course")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        fig = px.bar(byc.head(10), x="primary_course", y=["PrimaryRevenue", "OtherRevenue"], title="Primary vs Other Revenue", barmode="stack")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340, xaxis_tickangle=-30, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    c5, c6 = st.columns(2)
    with c5:
        fig = px.bar(byc.head(12), x="Due", y="primary_course", orientation="h", title="Outstanding Due by Course")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c6:
        fig = px.bar(byc.head(12), x="primary_course", y=["Students", "FullyPaid"], title="Students vs Fully Paid", barmode="group")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340, xaxis_tickangle=-30, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    display = byc.copy()
    for col in ["PrimaryRevenue", "OtherRevenue", "TotalRevenue", "Due"]:
        display[col] = display[col].apply(fmt_inr)
    display = display.rename(columns={"primary_course": "Primary Course"})
    st.dataframe(display, use_container_width=True, hide_index=True)

def render_combo(fdf, orders_df):
    pti_df = fdf[fdf["primary_course"].astype(str).str.contains(PTI_MATCH, na=False, case=False)].copy()
    with_other = pti_df[pti_df["additional_courses"].apply(lambda x: len(x) if isinstance(x, list) else 0) > 0].copy()

    cols = st.columns(5)
    stats = [
        ("PTI Buyers", len(pti_df), "Primary PTI course", "#6366f1"),
        ("Also Bought Other Course", len(with_other), "Cross-sell buyers", "#10b981"),
        ("PTI Revenue", fmt_inr(pti_df["primary_paid"].sum()), "Primary PTI revenue", "#f59e0b"),
        ("Other Course Revenue", fmt_inr(pti_df["additional_paid"].sum()), "Non-PTI after PTI", "#a855f7"),
        ("PTI Total Revenue", fmt_inr(pti_df["total_revenue"].sum()), "PTI buyers all-course revenue", "#22c55e"),
    ]
    for i, (lbl, val, sub, clr) in enumerate(stats):
        cols[i].markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

    if with_other.empty:
        st.info("No PTI buyers with other purchased courses in current filter.")
        return

    later_orders = pd.DataFrame()
    if orders_df is not None and not orders_df.empty:
        later_orders = orders_df[
            orders_df["mobile"].isin(with_other["mobile"]) &
            (~orders_df["is_primary"])
        ].copy()

    c1, c2 = st.columns(2)
    if not later_orders.empty:
        add_summary = later_orders.groupby("course").agg(Students=("mobile", "nunique"), Revenue=("paid_amount", "sum")).reset_index().sort_values("Students", ascending=False)
        with c1:
            fig = px.bar(add_summary.head(10), x="Students", y="course", orientation="h", title="Other Courses Bought After PTI")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340, yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.bar(add_summary.head(10), x="Revenue", y="course", orientation="h", title="Other Course Revenue After PTI")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340, yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    render_section_student_details(
        "PTI Cross-Sell",
        with_other,
        extra_cols=["additional_courses", "additional_paid", "total_revenue", "all_courses", "lead_service_name"],
        key_prefix="pti"
    )

def render_leads(fdf):
    cols = st.columns(5)
    lead_stats = [
        ("Leads Matched", len(fdf[fdf["lead_source"] != ""]), "Any lead row matched", "#6366f1"),
        ("Webinar", len(fdf[fdf["webinar_type"] == "Webinar"]), "Matched leads", "#06b6d4"),
        ("Non-Webinar", len(fdf[fdf["webinar_type"] == "Non Webinar"]), "Matched leads", "#8b5cf6"),
        ("Attempted", len(fdf[fdf["attempted"] == "Attempted"]), "Lead intelligence", "#10b981"),
        ("Unattempted", len(fdf[fdf["attempted"] == "Unattempted"]), "Lead intelligence", "#ef4444"),
    ]
    for i, (lbl, val, sub, clr) in enumerate(lead_stats):
        cols[i].markdown(kpi_card(lbl, val, sub, clr), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    src = fdf[fdf["lead_source"] != ""].groupby("lead_source").size().reset_index(name="Count").sort_values("Count", ascending=True).tail(12)
    with c1:
        if not src.empty:
            fig = px.bar(src, x="Count", y="lead_source", orientation="h", title="Lead Source Distribution")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=340, yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    lsvc = fdf[fdf["lead_service_name"] != ""].groupby("lead_service_name").size().reset_index(name="Count")
    with c2:
        if not lsvc.empty:
            fig = px.pie(lsvc, names="lead_service_name", values="Count", title="Lead Service Distribution", hole=0.4, color_discrete_sequence=CHART_COLORS)
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=340)
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    owner_df = fdf[fdf["lead_owner"] != ""].groupby("lead_owner").agg(Leads=("attended", "count"), Converted=("converted", "sum")).reset_index().sort_values("Leads", ascending=True).tail(10)
    with c3:
        if not owner_df.empty:
            fig = go.Figure()
            fig.add_bar(x=owner_df["Leads"], y=owner_df["lead_owner"], name="Leads", orientation="h")
            fig.add_bar(x=owner_df["Converted"], y=owner_df["lead_owner"], name="Converted", orientation="h")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", barmode="group", height=320, yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    stage_df = fdf[fdf["stage_name"] != ""].groupby("stage_name").size().reset_index(name="Count").sort_values("Count", ascending=True).tail(10)
    with c4:
        if not stage_df.empty:
            fig = px.bar(stage_df, x="Count", y="stage_name", orientation="h", title="Lead Stage Distribution")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320, yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    render_section_student_details(
        "Lead Intelligence",
        fdf[(fdf["lead_source"].astype(str).str.strip() != "") | (fdf["webinar_type"].astype(str).str.strip() != "")],
        extra_cols=["email", "remarks", "lead_service_name", "all_courses", "total_revenue"],
        key_prefix="leadsec"
    )

def render_journey(fdf):
    st.markdown('<div class="section-header">🗺️ Student Journey Revenue Flow</div>', unsafe_allow_html=True)
    conv = fdf[fdf["converted"]].copy()
    if not conv.empty:
        flow = pd.DataFrame({
            "Stage": ["Seminar Attendees", "Seat Booked", "Converted", "PTI Buyers", "Cross-Sell Students"],
            "Count": [
                len(fdf),
                int((fdf["seat_book_amount"] > 0).sum()),
                len(conv),
                int(conv["primary_course"].astype(str).str.contains(PTI_MATCH, na=False, case=False).sum()),
                int((conv["additional_course_count"] > 0).sum()),
            ]
        })
        fig = px.bar(flow, x="Stage", y="Count", title="Student Journey Funnel")
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320)
        st.plotly_chart(fig, use_container_width=True)

    render_section_student_details(
        "Student Journey",
        fdf,
        extra_cols=["all_courses", "additional_courses", "additional_paid", "total_revenue", "lead_service_name"],
        key_prefix="journeysec"
    )

def render_tables(fdf, orders_df):
    tab1, tab2, tab3 = st.tabs(["📋 Attendee Master", "✅ Converted Students", "📦 All Orders Summary"])
    with tab1:
        show = fdf[["name", "mobile", "place", "seminar_date_str", "session", "trainer", "seat_book_amount", "converted",
                    "primary_course", "primary_paid", "primary_due", "primary_status", "match_reason"]].copy()
        show["seat_book_amount"] = show["seat_book_amount"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
        show["converted"] = show["converted"].map({True: "✅ Yes", False: "❌ No"})
        show["primary_paid"] = show["primary_paid"].apply(lambda x: fmt_inr(x) if x > 0 else "—")
        show["primary_due"] = show["primary_due"].apply(lambda x: fmt_inr(x) if x > 0 else "₹0")
        show.columns = ["Name", "Mobile", "Location", "Seminar Date", "Session", "Trainer", "Seat Book Amt", "Converted", "Primary Course", "Primary Paid", "Due", "Status", "Match Reason"]
        st.dataframe(show, use_container_width=True, hide_index=True, height=420)
    with tab2:
        conv = fdf[fdf["converted"]].copy()
        show2 = conv[["name", "mobile", "place", "seminar_date_str", "primary_course", "primary_order_date_str", "primary_paid",
                      "additional_courses", "additional_paid", "total_revenue", "all_courses", "primary_status", "lead_service_name"]].copy()
        show2["primary_paid"] = show2["primary_paid"].apply(fmt_inr)
        show2["additional_paid"] = show2["additional_paid"].apply(fmt_inr)
        show2["total_revenue"] = show2["total_revenue"].apply(fmt_inr)
        show2["additional_courses"] = show2["additional_courses"].apply(lambda x: " | ".join(x) if isinstance(x, list) and x else "—")
        show2["all_courses"] = show2["all_courses"].apply(lambda x: " | ".join(x) if isinstance(x, list) and x else "—")
        show2.columns = ["Name", "Mobile", "Location", "Seminar Date", "Primary Course", "Primary Order Date", "Primary Paid",
                         "Other Purchased Courses", "Other Courses Revenue", "Total Revenue", "All Purchased Courses", "Status", "Lead Service"]
        st.dataframe(show2, use_container_width=True, hide_index=True, height=420)
    with tab3:
        if orders_df is None or orders_df.empty:
            st.info("No order records available.")
        else:
            st.dataframe(orders_df, use_container_width=True, hide_index=True, height=420)

# =========================================================
# LOGIN / UPLOAD
# =========================================================
def login_page():
    st.markdown("""
    <div style="text-align:center;margin-top:60px;margin-bottom:30px">
      <div style="font-size:48px">📊</div>
      <h1 style="font-size:26px;font-weight:800;color:#e2e8f0;margin:8px 0">Invesmate Analytics</h1>
      <p style="color:#64748b;font-size:14px">Seminar Performance Dashboard</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In →", use_container_width=True)
            if submitted:
                if CREDENTIALS.get(username) == password:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try admin / admin123")

def upload_page():
    st.markdown('<div class="section-header">📁 Upload Data Files</div>', unsafe_allow_html=True)
    st.markdown("Upload seminar, conversion and leads files.")
    c1, c2, c3 = st.columns(3)
    with c1:
        sem_file = st.file_uploader("📋 Seminar Updated Sheet", type=["xlsx", "xls", "csv"], key="sem_file")
    with c2:
        conv_file = st.file_uploader("💰 Conversion List", type=["xlsx", "xls", "csv"], key="conv_file")
    with c3:
        leads_file = st.file_uploader("🎯 Leads Report", type=["xlsx", "xls", "csv"], key="leads_file")

    if sem_file and conv_file and leads_file:
        if st.button("🚀 Build Dashboard", use_container_width=True, type="primary"):
            with st.spinner("Processing files and building analytics…"):
                df, orders_df = process_data(
                    sem_file.read(), conv_file.read(), leads_file.read(),
                    sem_file.name, conv_file.name, leads_file.name,
                )
                st.session_state["df"] = df
                st.session_state["orders_df"] = orders_df
                st.session_state["files_loaded"] = True
                st.rerun()
    else:
        missing = []
        if not sem_file: missing.append("Seminar Sheet")
        if not conv_file: missing.append("Conversion List")
        if not leads_file: missing.append("Leads Report")
        st.info(f"Waiting for: {', '.join(missing)}")

# =========================================================
# MAIN
# =========================================================
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "files_loaded" not in st.session_state:
        st.session_state["files_loaded"] = False
    if "df" not in st.session_state:
        st.session_state["df"] = None
    if "orders_df" not in st.session_state:
        st.session_state["orders_df"] = None

    if not st.session_state["logged_in"]:
        login_page()
        return

    st.markdown("""
    <div class="hero">
      <div class="hero-title">Invesmate Seminar Analytics Pro</div>
      <div class="hero-sub">Your required business logic is preserved: PTI is treated first when purchased, other courses are separated, total revenue includes both/all courses, and lead details try to match the purchased course. Expanded KPI and chart coverage is included.</div>
    </div>
    """, unsafe_allow_html=True)

    toolbar = st.columns([1, 1, 5])
    if toolbar[0].button("Upload / reload data", use_container_width=True):
        st.session_state["files_loaded"] = False
        st.session_state["df"] = None
        st.session_state["orders_df"] = None
        st.rerun()
    if toolbar[1].button("Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["files_loaded"] = False
        st.session_state["df"] = None
        st.session_state["orders_df"] = None
        st.rerun()

    if not st.session_state["files_loaded"] or st.session_state["df"] is None:
        upload_page()
        return

    df = st.session_state["df"]
    orders_df = st.session_state["orders_df"]

    fdf = render_filters_top(df)
    filtered_orders = filter_orders_by_attendees(orders_df, fdf)

    if fdf.empty:
        st.warning("No data matches current filters.")
        return

    render_section_student_details(
        "Filtered Students",
        fdf,
        extra_cols=["all_courses", "additional_courses", "additional_paid", "total_revenue", "lead_service_name"],
        key_prefix="filteredtop"
    )

    tabs = st.tabs(["📊 Overview", "📚 Course Analysis", "🔗 PTI Cross-Sell", "🎯 Lead Intelligence", "🗺️ Student Journey", "📋 Data Tables"])
    with tabs[0]:
        st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)
        render_kpis(fdf)
        st.markdown("---")
        render_overview(fdf)
    with tabs[1]:
        render_courses(fdf)
    with tabs[2]:
        render_combo(fdf, filtered_orders)
    with tabs[3]:
        render_leads(fdf)
    with tabs[4]:
        render_journey(fdf)
    with tabs[5]:
        render_tables(fdf, filtered_orders)

if __name__ == "__main__":
    main()
