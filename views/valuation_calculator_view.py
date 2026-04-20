"""
Justified P/E Calculator — with DB-backed company picker.

Flow:
  1. User picks a stock from the 52-week-high DB (512 stocks, latest date).
  2. P/E pre-fills instantly from DB (no network).
  3. Optional "Fetch details" loads ROCE + EPS history from Screener.in.
  4. All sliders are fully overridable.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd
import streamlit as st

from config import DB_PATH
from mcap_tier_utils import TIER_LABELS, add_mcap_tier_col, get_mcap_tier
from screener_fetch import CompanyData, fetch_company_data, search_companies


# ── DB helpers ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _load_db_companies() -> pd.DataFrame:
    """All companies from the latest DB snapshot, ordered by market cap desc."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT name, nse_code, industry,
                   market_cap  AS market_cap_cr,
                   pe, roe
            FROM   highs
            WHERE  date = (SELECT MAX(date) FROM highs)
              AND  nse_code IS NOT NULL
              AND  nse_code != ''
            ORDER  BY market_cap DESC
            """,
            conn,
        )
    df = add_mcap_tier_col(df, col="market_cap_cr")
    return df


# ── Math helpers ──────────────────────────────────────────────────────────────

def _justified_pe_single(roce: float, coe: float, g: float) -> float | None:
    if roce <= 0 or coe <= g:
        return None
    return (1 - g / roce) / (coe - g)


def _justified_pe_two_stage(
    roce_high: float, coe: float, g_high: float, cap: int,
    roce_terminal: float, g_terminal: float,
) -> float | None:
    if coe <= g_terminal or roce_high <= 0 or roce_terminal <= 0:
        return None
    b = min(g_high / roce_high, 1.0)
    stage1 = sum((1 - b) * (1 + g_high) ** (t - 1) / (1 + coe) ** t for t in range(1, cap + 1))
    b_t = min(g_terminal / roce_terminal, 1.0)
    pe_t = (1 - b_t) / (coe - g_terminal)
    stage2 = pe_t * (1 + g_high) ** cap / (1 + coe) ** cap
    return stage1 + stage2


def _sensitivity_df(
    coe: float, g: float, cap_values: list[int], roce_values: list[float],
    roce_terminal_pct: int, g_terminal: float,
) -> pd.DataFrame:
    rows = []
    for cap in cap_values:
        row = {}
        for roce in roce_values:
            val = _justified_pe_two_stage(
                roce, coe, g, cap,
                roce * roce_terminal_pct / 100, g_terminal,
            )
            row[f"{roce*100:.0f}%"] = round(val, 1) if val else "—"
        rows.append(row)
    df = pd.DataFrame(rows, index=[f"{c}y" for c in cap_values])
    df.index.name = "CAP \\ ROCE"
    return df


def _color_pe(val):
    try:
        v = float(val)
        if v < 20:   return "background-color:#d4edda;color:#155724"
        elif v < 35: return "background-color:#fff3cd;color:#856404"
        elif v < 55: return "background-color:#fde8d8;color:#7d3c0f"
        else:        return "background-color:#f8d7da;color:#721c24"
    except (TypeError, ValueError):
        return ""


# ── Company picker ────────────────────────────────────────────────────────────

def _render_company_picker(all_companies: pd.DataFrame) -> pd.Series | None:
    """
    Sidebar company picker with two modes:
      • DB (52-week-high tracked stocks) — instant, pre-filled P/E
      • Screener.in search — any listed company
    Returns a pd.Series with at least {name, nse_code, pe, roe, market_cap_cr, mcap_tier}.
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("Company Picker")

    mode = st.sidebar.radio(
        "Source",
        ["From 52-Week-High DB", "Search any company"],
        key="calc_mode",
        horizontal=True,
    )

    # ── Mode A: DB ────────────────────────────────────────────────────────────
    if mode == "From 52-Week-High DB":
        tier_sel = st.sidebar.multiselect(
            "MCap Tier", TIER_LABELS, default=TIER_LABELS, key="calc_mcap"
        )
        filtered = all_companies[all_companies["mcap_tier"].isin(tier_sel)] if tier_sel else all_companies

        industries = sorted(filtered["industry"].dropna().unique())
        ind_sel = st.sidebar.selectbox("Industry", ["All"] + industries, key="calc_industry")
        if ind_sel != "All":
            filtered = filtered[filtered["industry"] == ind_sel]

        search = st.sidebar.text_input("Search by name / symbol", key="calc_search").strip().lower()
        if search:
            mask = (
                filtered["name"].str.lower().str.contains(search, na=False)
                | filtered["nse_code"].str.lower().str.contains(search, na=False)
            )
            filtered = filtered[mask]

        st.sidebar.caption(f"{len(filtered)} stocks match")
        if filtered.empty:
            st.sidebar.warning("No stocks match — relax filters.")
            return None

        def _label(row):
            tier = row["mcap_tier"].split(" ", 1)[-1]
            pe_str = f"PE {row['pe']:.0f}x" if pd.notna(row["pe"]) else "PE n/a"
            return f"{row['nse_code']} — {row['name']}  ({tier}, {pe_str})"

        labels = filtered.apply(_label, axis=1).tolist()
        label_to_idx = {lbl: i for i, lbl in enumerate(labels)}
        chosen = st.sidebar.selectbox("Select company", labels, key="calc_company_select")
        return filtered.iloc[label_to_idx[chosen]]

    # ── Mode B: Screener.in search ────────────────────────────────────────────
    else:
        query = st.sidebar.text_input("Company name or NSE symbol", key="calc_screener_query").strip()
        if not query:
            st.sidebar.caption("Type a name or symbol to search Screener.in.")
            return None

        results = search_companies(query)  # lru_cached
        if not results or "error" in results[0]:
            err = results[0].get("error", "No results") if results else "No results"
            st.sidebar.warning(f"Search failed: {err}")
            return None

        options = {f"{r['symbol']} — {r['name']}": r["symbol"] for r in results if r.get("symbol")}
        if not options:
            st.sidebar.info("No results.")
            return None

        chosen_label = st.sidebar.selectbox("Select", list(options.keys()), key="calc_screener_select")
        chosen_symbol = options[chosen_label]
        chosen_name = results[[r["symbol"] for r in results].index(chosen_symbol)]["name"]

        # Return a minimal Series so the rest of main() works unchanged
        return pd.Series({
            "name": chosen_name,
            "nse_code": chosen_symbol,
            "pe": None,        # will be filled after Screener.in fetch
            "roe": None,
            "market_cap_cr": None,
            "mcap_tier": "—",
            "industry": "—",
            "_screener_only": True,   # flag: no DB data available
        })


# ── Screener detail card ──────────────────────────────────────────────────────

def _render_screener_card(cd: CompanyData) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Price", f"Rs {cd.current_price:,.0f}" if cd.current_price else "—")
    m2.metric("Market P/E", f"{cd.stock_pe:.1f}x" if cd.stock_pe else "—")
    m3.metric("ROCE (latest)", f"{cd.roce_current:.1f}%" if cd.roce_current else "—")
    m4.metric("EPS (TTM)", f"Rs {cd.eps_current:.2f}" if cd.eps_current else "—")

    ch1, ch2 = st.columns(2)
    with ch1:
        if cd.roce_history:
            st.caption("ROCE trend (%)")
            st.bar_chart(
                pd.DataFrame({"ROCE %": cd.roce_history}).T.T.rename_axis("Year"),
                height=160,
            )
        else:
            st.caption("ROCE history: not available (financial co or JS-rendered)")
    with ch2:
        if cd.eps_history:
            st.caption("EPS history (Rs)")
            st.bar_chart(
                pd.DataFrame({"EPS": cd.eps_history}).T.T.rename_axis("Year"),
                height=160,
            )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.title("Justified P/E Calculator")
    st.caption(
        "**Justified P/E = f(ROCE, CoE, g, CAP).** "
        "Growth only creates value when ROCE > CoE — at ROCE = CoE it is worth exactly zero."
    )

    all_companies = _load_db_companies()

    # ── Sidebar company picker ────────────────────────────────────────────────
    company_row = _render_company_picker(all_companies)

    # Sourced defaults (DB or screener-only)
    screener_only = company_row is not None and company_row.get("_screener_only", False)
    db_pe   = float(company_row["pe"])   if company_row is not None and pd.notna(company_row.get("pe") or float("nan"))  else None
    db_roe  = float(company_row["roe"])  if company_row is not None and pd.notna(company_row.get("roe") or float("nan")) else None
    db_name = company_row["name"]        if company_row is not None else None
    db_sym  = company_row["nse_code"]    if company_row is not None else None

    # ── Screener.in live fetch (optional) ─────────────────────────────────────
    screener_cd: CompanyData | None = st.session_state.get("calc_screener_cd")
    screener_sym: str | None = st.session_state.get("calc_screener_sym")

    # Clear cached data when user switches company
    if db_sym and screener_sym and screener_sym != db_sym:
        st.session_state["calc_screener_cd"] = None
        st.session_state["calc_screener_sym"] = None
        screener_cd = None

    if company_row is not None:
        # For screener-only companies, auto-trigger fetch if not yet loaded
        if screener_only and not screener_cd and db_sym:
            with st.spinner(f"Fetching {db_sym} from Screener.in..."):
                cd = fetch_company_data(db_sym)
            if not cd.error:
                st.session_state["calc_screener_cd"] = cd
                st.session_state["calc_screener_sym"] = db_sym
                screener_cd = cd

        with st.expander(
            f"Screener.in live data — **{db_name}** ({db_sym})",
            expanded=screener_cd is not None,
        ):
            if not screener_only:
                if st.button("Fetch ROCE & EPS history from Screener.in", key="fetch_btn"):
                    with st.spinner(f"Fetching {db_sym}..."):
                        cd = fetch_company_data(db_sym)
                    if cd.error:
                        st.error(f"Fetch failed: {cd.error}")
                    else:
                        st.session_state["calc_screener_cd"] = cd
                        st.session_state["calc_screener_sym"] = db_sym
                        screener_cd = cd
                        st.success("Loaded.")

            if screener_cd:
                _render_screener_card(screener_cd)
            elif screener_only:
                st.warning("Could not load data from Screener.in. Try a different symbol.")
            else:
                st.caption("P/E is pre-filled from the 52-week-high DB. Click above for ROCE & EPS history.")

    # ── Derive slider defaults ─────────────────────────────────────────────────
    default_roce = int(round(screener_cd.roce_current)) if screener_cd and screener_cd.roce_current else (
        int(round(db_roe)) if db_roe else 18
    )
    # P/E: DB first, then screener (screener-only mode), then fallback
    default_pe = (
        db_pe if db_pe
        else (screener_cd.stock_pe if screener_cd and screener_cd.stock_pe else 30.0)
    )
    default_g    = 10
    if screener_cd and screener_cd.eps_cagr_pct and 0 < screener_cd.eps_cagr_pct < 50:
        default_g = int(round(screener_cd.eps_cagr_pct))

    st.divider()

    # ── Parameter columns ─────────────────────────────────────────────────────
    col_params, col_results = st.columns([1, 2])

    with col_params:
        st.subheader("Parameters")

        if company_row is not None:
            tier = company_row.get("mcap_tier") or (
                get_mcap_tier(screener_cd.market_cap_cr) if screener_cd and screener_cd.market_cap_cr else "—"
            )
            mcap_cr = company_row.get("market_cap_cr") or (screener_cd.market_cap_cr if screener_cd else None)
            mcap_label = ""
            if mcap_cr:
                mcap_label = f"Rs {mcap_cr/1e5:.1f}L Cr" if mcap_cr >= 1e5 else f"Rs {mcap_cr:,.0f} Cr"
            ind = company_row.get("industry") or "—"
            st.markdown(f"**{db_name}** &nbsp; `{db_sym}` &nbsp; {tier} &nbsp; {mcap_label} &nbsp; {ind}")

        if screener_cd and screener_cd.roce_current:
            st.info(f"ROCE pre-filled from Screener.in: **{screener_cd.roce_current:.1f}%**")
        elif db_roe:
            st.info(f"No ROCE fetched yet — defaulting to ROE ({db_roe:.1f}%) as proxy. Fetch for accuracy.")

        roce = st.slider("ROCE (%)", 5, 45, default_roce, 1) / 100
        coe  = st.slider("CoE — Cost of Equity (%)", 7, 20, 11, 1) / 100
        g    = st.slider("Sustainable Growth Rate (%)", 0, 30, default_g, 1) / 100
        cap  = st.slider("CAP — Competitive Advantage Period (years)", 1, 20, 7, 1)

        st.divider()
        st.caption("Terminal assumptions")
        roce_t_pct = st.slider("Terminal ROCE (% of peak)", 40, 100, 70, 5)
        g_t_pct    = st.slider("Terminal Growth (% of CoE)", 30, 70, 45, 5)
        roce_t = roce * roce_t_pct / 100
        g_t    = coe  * g_t_pct  / 100

        st.divider()
        current_pe = st.number_input(
            "Market P/E (for reverse DCF)",
            min_value=1.0, max_value=500.0,
            value=default_pe, step=0.5,
        )
        if company_row is not None:
            st.caption(f"Pre-filled from DB snapshot ({db_name})")

    # ── Calculate ─────────────────────────────────────────────────────────────
    pe_single = _justified_pe_single(roce, coe, g)
    pe_two    = _justified_pe_two_stage(roce, coe, g, cap, roce_t, g_t)
    excess    = roce - coe

    with col_results:
        st.subheader("Result")

        color = "green" if excess > 0 else "red"
        signal = "Value-creative" if excess > 0 else "Value-neutral / destructive"
        st.markdown(
            f"**ROCE − CoE = {excess*100:.1f}%** &nbsp;"
            f'<span style="color:{color}">{signal}</span>',
            unsafe_allow_html=True,
        )

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Single-Stage P/E", f"{pe_single:.1f}x" if pe_single else "N/A",
                   help="Perpetuity formula. Requires g < CoE.")
        mc2.metric(f"Two-Stage P/E ({cap}y CAP)", f"{pe_two:.1f}x" if pe_two else "N/A",
                   help="High-growth phase + stable terminal.")
        if pe_two:
            gap = current_pe - pe_two
            mc3.metric(
                "Market vs Justified",
                f"{abs(gap):.1f}x {'above' if gap > 0 else 'below'}",
                delta=f"{gap / pe_two * 100:+.1f}%",
                delta_color="inverse",
            )

        if g >= coe:
            st.warning(f"Growth ({g*100:.0f}%) >= CoE ({coe*100:.0f}%): single-stage formula invalid — use two-stage.")
        if roce <= coe:
            st.error(f"ROCE ({roce*100:.0f}%) <= CoE ({coe*100:.0f}%): growth destroys value here.")
        elif excess < 0.03:
            st.warning("ROCE barely exceeds CoE — P/E is highly sensitive to small changes.")

        # ── Key drivers ───────────────────────────────────────────────────────
        with st.expander("What is driving the multiple?", expanded=True):
            d1, d2, d3 = st.columns(3)
            with d1:
                st.markdown("**1 · Excess Return**")
                st.markdown(
                    f"ROCE {roce*100:.0f}% − CoE {coe*100:.0f}% = **{excess*100:.1f}%**  \n"
                    "This spread is the engine. At zero spread, all growth is worthless."
                )
            with d2:
                st.markdown("**2 · Duration (CAP)**")
                for yrs in [5, 7, 10, 15]:
                    pv = _justified_pe_two_stage(roce, coe, g, yrs, roce_t, g_t)
                    marker = " ◀" if yrs == cap else ""
                    st.markdown(f"{yrs}y → **{pv:.1f}x**{marker}" if pv else f"{yrs}y → N/A{marker}")
            with d3:
                st.markdown("**3 · ROCE ladder**")
                for r in [0.12, 0.14, 0.18, 0.22, 0.26, 0.30]:
                    pv = _justified_pe_two_stage(r, coe, g, cap, r * roce_t_pct / 100, g_t)
                    marker = " ◀" if abs(r - roce) < 0.005 else ""
                    st.markdown(f"{r*100:.0f}% → **{pv:.1f}x**{marker}" if pv else f"{r*100:.0f}% → N/A{marker}")

        st.divider()

        # ── Sensitivity heatmap ───────────────────────────────────────────────
        st.subheader("Sensitivity: CAP × ROCE")
        st.caption(
            f"CoE = {coe*100:.0f}%  ·  Growth = {g*100:.0f}%  ·  "
            f"Terminal ROCE = {roce_t_pct}% of peak  ·  Terminal g = {g_t_pct}% of CoE"
        )
        sens = _sensitivity_df(coe, g, [3, 5, 7, 10, 12, 15],
                               [0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30],
                               roce_t_pct, g_t)
        st.dataframe(sens.style.map(_color_pe), use_container_width=True)
        st.caption("Green < 20x · Yellow 20–35x · Orange 35–55x · Red > 55x")

        # ── Reverse DCF ───────────────────────────────────────────────────────
        st.divider()
        st.subheader("Reverse DCF — what is the market pricing in?")
        rows = []
        for tr in np.arange(0.10, 0.36, 0.01):
            for tc in [5, 7, 10, 12, 15]:
                pv = _justified_pe_two_stage(tr, coe, g, tc, tr * roce_t_pct / 100, g_t)
                if pv and abs(pv - current_pe) / current_pe < 0.05:
                    rows.append({"Implied ROCE": f"{tr*100:.0f}%", "CAP (yrs)": tc, "Justified P/E": round(pv, 1)})
        if rows:
            st.markdown(f"At **{current_pe:.1f}x**, these ROCE × CAP combos are implied (±5%):")
            st.dataframe(
                pd.DataFrame(rows).drop_duplicates(subset=["Implied ROCE", "CAP (yrs)"]),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info(f"No ROCE (10–35%) × CAP (5–15y) combo produces ~{current_pe:.1f}x with current assumptions.")

        # ── Formula ───────────────────────────────────────────────────────────
        with st.expander("Formula reference"):
            st.markdown("""
**Single-stage:** `Justified P/E = (1 − g/ROCE) / (CoE − g)`
When ROCE = CoE, reduces to 1/CoE regardless of g — growth adds zero value.

**Two-stage:**
```
P/E = Σ(t=1..CAP)[ (1−g/ROCE)·(1+g)^(t−1) / (1+CoE)^t ]
    + [ (1−gₜ/ROCEₜ) / (CoE−gₜ) ] · (1+g)^CAP / (1+CoE)^CAP
```
**Key:** Growth × (ROCE − CoE) = value created per reinvested rupee.
At ROCE < CoE: growth actively destroys value.
""")
