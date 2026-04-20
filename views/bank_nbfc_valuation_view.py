"""
Bank & NBFC Valuation Engine

Justified P/B, implied ROE, growth, and market expectations for financials.

Framework: ROE / Book Value / Residual Income — NOT ROCE-based industrial P/E.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd
import streamlit as st

from config import DB_PATH
from mcap_tier_utils import TIER_LABELS, add_mcap_tier_col
from screener_fetch import fetch_company_data, search_companies
from valuation.financials_defaults import (
    SUBTYPES,
    get_defaults,
    industry_to_subtype,
)
from valuation.financials_models import (
    implied_fade_years,
    implied_growth_from_pb,
    implied_roe_from_pb,
    justified_pb_fade_model,
    justified_pb_single_stage,
    justified_pb_two_stage,
    justified_pe_from_pb,
    sustainable_growth_rate,
)
from valuation.financials_sensitivity import (
    _color_pb,
    sensitivity_fade_terminal_roe,
    sensitivity_roe_coe,
    sensitivity_roe_growth,
)

# ── Financial industries present in the highs DB ──────────────────────────────

_FINANCIAL_INDUSTRIES = {
    "Private Sector Bank",
    "Public Sector Bank",
    "Other Bank",
    "Small Finance Bank",
    "Non Banking Financial Company (NBFC)",
    "Housing Finance Company",
    "Microfinance",
    "Financial Institution",
    "Financial Products Distributor",
}


# ── DB loader ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _load_financial_companies() -> pd.DataFrame:
    """Banks / NBFCs from the latest highs snapshot."""
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            """
            SELECT name, nse_code, industry,
                   market_cap  AS market_cap_cr,
                   current_price,
                   pe, pbv      AS pb,
                   roe
            FROM   highs
            WHERE  date = (SELECT MAX(date) FROM highs)
              AND  industry IN (
                    'Private Sector Bank','Public Sector Bank','Other Bank',
                    'Small Finance Bank',
                    'Non Banking Financial Company (NBFC)',
                    'Housing Finance Company','Microfinance',
                    'Financial Institution','Financial Products Distributor'
                   )
              AND  nse_code IS NOT NULL
              AND  nse_code != ''
            ORDER  BY market_cap DESC
            """,
            conn,
        )
    df = add_mcap_tier_col(df, col="market_cap_cr")
    df["subtype"] = df["industry"].map(industry_to_subtype).fillna("Other")
    return df


# ── Company picker ────────────────────────────────────────────────────────────

def _render_picker(all_companies: pd.DataFrame) -> pd.Series | None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Company Picker")

    mode = st.sidebar.radio(
        "Source",
        ["From DB (52-Week-High)", "Search any company"],
        key="fin_mode",
        horizontal=True,
    )

    if mode == "From DB (52-Week-High)":
        subtypes = sorted(all_companies["subtype"].unique())
        sub_sel = st.sidebar.multiselect("Subtype", subtypes, default=subtypes, key="fin_subtype")
        filtered = all_companies[all_companies["subtype"].isin(sub_sel)] if sub_sel else all_companies

        search = st.sidebar.text_input("Search name / symbol", key="fin_search").strip().lower()
        if search:
            mask = (
                filtered["name"].str.lower().str.contains(search, na=False)
                | filtered["nse_code"].str.lower().str.contains(search, na=False)
            )
            filtered = filtered[mask]

        st.sidebar.caption(f"{len(filtered)} companies match")
        if filtered.empty:
            st.sidebar.warning("No companies match — relax filters.")
            return None

        def _label(row):
            pb_str = f"P/B {row['pb']:.1f}x" if pd.notna(row.get("pb")) else "P/B n/a"
            roe_str = f"ROE {row['roe']:.0f}%" if pd.notna(row.get("roe")) else ""
            return f"{row['nse_code']} — {row['name']}  ({row['subtype']}, {pb_str}, {roe_str})"

        labels = filtered.apply(_label, axis=1).tolist()
        chosen = st.sidebar.selectbox("Select company", labels, key="fin_db_select")
        idx = labels.index(chosen)
        return filtered.iloc[idx]

    else:
        query = st.sidebar.text_input("Company name or NSE symbol", key="fin_screener_query").strip()
        if not query:
            st.sidebar.caption("Type a name or symbol to search Screener.in.")
            return None

        results = search_companies(query)
        if not results or "error" in results[0]:
            err = results[0].get("error", "No results") if results else "No results"
            st.sidebar.warning(f"Search failed: {err}")
            return None

        options = {f"{r['symbol']} — {r['name']}": r["symbol"] for r in results if r.get("symbol")}
        if not options:
            st.sidebar.info("No results.")
            return None

        chosen_label = st.sidebar.selectbox("Select", list(options.keys()), key="fin_screener_select")
        chosen_symbol = options[chosen_label]
        chosen_name = next(r["name"] for r in results if r.get("symbol") == chosen_symbol)

        return pd.Series({
            "name": chosen_name,
            "nse_code": chosen_symbol,
            "industry": "—",
            "subtype": "Other",
            "pb": None,
            "pe": None,
            "roe": None,
            "market_cap_cr": None,
            "current_price": None,
            "mcap_tier": "—",
            "_screener_only": True,
        })


# ── Screener data card ────────────────────────────────────────────────────────

def _render_screener_card(cd) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Price", f"₹{cd.current_price:,.0f}" if cd.current_price else "—")
    m2.metric("P/E", f"{cd.stock_pe:.1f}x" if cd.stock_pe else "—")
    m3.metric("ROE", f"{cd.roe_current:.1f}%" if cd.roe_current else "—")
    m4.metric("Book Value / sh", f"₹{cd.book_value:,.0f}" if cd.book_value else "—")

    if cd.roce_history or cd.eps_history:
        ch1, ch2 = st.columns(2)
        with ch1:
            if cd.roce_history:
                st.caption("ROE / ROCE trend (%)")
                st.bar_chart(pd.DataFrame({"ROE %": cd.roce_history}).T.T.rename_axis("Year"), height=150)
        with ch2:
            if cd.eps_history:
                st.caption("EPS history (₹)")
                st.bar_chart(pd.DataFrame({"EPS": cd.eps_history}).T.T.rename_axis("Year"), height=150)


# ── Interpretation helper ─────────────────────────────────────────────────────

def _interpret_pb(current_pb: float | None, justified_pb: float | None) -> str:
    if current_pb is None or justified_pb is None or justified_pb <= 0:
        return ""
    ratio = current_pb / justified_pb
    if ratio < 0.85:
        return "Pessimistic — market prices in below-justified value; potential margin of safety."
    elif ratio < 1.15:
        return "Roughly fair — market P/B aligns with modelled justified P/B."
    elif ratio < 1.5:
        return "Optimistic — market expects above-base ROE or longer franchise duration."
    else:
        return "Heroic — market assumptions appear stretched; verify ROE/duration inputs."


def _interpret_reverse(implied_roe: float | None, base_roe: float, coe: float) -> str:
    if implied_roe is None:
        return "Cannot be derived (CoE ≤ g or P/B ≤ 0)."
    spread = implied_roe - coe
    if implied_roe < coe:
        return f"Market implies ROE {implied_roe*100:.1f}% < CoE {coe*100:.1f}% — value-destructive expectation."
    elif spread < 0.02:
        return f"Market implies ROE {implied_roe*100:.1f}% ≈ CoE — near-zero excess return expected."
    elif implied_roe > base_roe * 1.25:
        return f"Market implies ROE {implied_roe*100:.1f}% — meaningfully above base ROE ({base_roe*100:.1f}%); optimistic."
    else:
        return f"Market implies ROE {implied_roe*100:.1f}% — broadly in line with base ROE ({base_roe*100:.1f}%)."


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.title("Bank & NBFC Valuation Engine")
    st.caption(
        "**Justified P/B = f(ROE, CoE, g).** "
        "Value is created only when ROE > CoE — the residual income spread. "
        "P/E is derived, not primary."
    )

    all_companies = _load_financial_companies()

    # ── Sidebar: subtype selector (influences defaults) ───────────────────────
    st.sidebar.subheader("Subtype")
    subtype = st.sidebar.selectbox("Lender type", SUBTYPES, key="fin_subtype_manual")

    # ── Company picker ────────────────────────────────────────────────────────
    company_row = _render_picker(all_companies)

    screener_only = company_row is not None and company_row.get("_screener_only", False)
    db_pb   = float(company_row["pb"])   if company_row is not None and pd.notna(company_row.get("pb") or float("nan"))  else None
    db_roe  = float(company_row["roe"])  if company_row is not None and pd.notna(company_row.get("roe") or float("nan")) else None
    db_name = company_row["name"]        if company_row is not None else None
    db_sym  = company_row["nse_code"]    if company_row is not None else None

    # Auto-set subtype when a DB company is selected
    if company_row is not None and not screener_only and "subtype" in company_row:
        detected = company_row["subtype"]
        if detected in SUBTYPES:
            subtype = detected

    defs = get_defaults(subtype)

    # ── Screener.in live fetch ─────────────────────────────────────────────────
    screener_cd = st.session_state.get("financials_cd")
    screener_sym = st.session_state.get("financials_symbol")

    if db_sym and screener_sym and screener_sym != db_sym:
        st.session_state["financials_cd"] = None
        st.session_state["financials_symbol"] = None
        screener_cd = None

    if company_row is not None:
        if screener_only and not screener_cd and db_sym:
            with st.spinner(f"Fetching {db_sym} from Screener.in..."):
                cd = fetch_company_data(db_sym)
            if not cd.error:
                st.session_state["financials_cd"] = cd
                st.session_state["financials_symbol"] = db_sym
                screener_cd = cd

        with st.expander(
            f"Screener.in live data — **{db_name}** ({db_sym})",
            expanded=screener_cd is not None,
        ):
            if not screener_only:
                if st.button("Fetch live details from Screener.in", key="fin_fetch_btn"):
                    with st.spinner(f"Fetching {db_sym}..."):
                        cd = fetch_company_data(db_sym)
                    if cd.error:
                        st.error(f"Fetch failed: {cd.error}")
                    else:
                        st.session_state["financials_cd"] = cd
                        st.session_state["financials_symbol"] = db_sym
                        screener_cd = cd
                        st.success("Loaded.")
            if screener_cd:
                _render_screener_card(screener_cd)
            elif screener_only:
                st.warning("Could not load data from Screener.in.")
            else:
                st.caption("Click above to pull live ROE, book value, and EPS history.")

    # ── Derive defaults from available data ───────────────────────────────────
    roe_pct_default = int(round((db_roe or defs["default_roe"]) * 100))
    if screener_cd and screener_cd.roe_current:
        roe_pct_default = int(round(screener_cd.roe_current))

    pb_market_default = round(db_pb or (screener_cd.stock_pe * (db_roe or defs["default_roe"]) if screener_cd and screener_cd.stock_pe else 2.0), 1)

    st.divider()

    # ── Layout ────────────────────────────────────────────────────────────────
    col_params, col_results = st.columns([1, 2])

    with col_params:
        st.subheader("Parameters")

        if company_row is not None:
            mcap_cr = company_row.get("market_cap_cr")
            mcap_label = ""
            if mcap_cr and pd.notna(mcap_cr):
                mcap_label = f"₹{mcap_cr/1e5:.1f}L Cr" if mcap_cr >= 1e5 else f"₹{mcap_cr:,.0f} Cr"
            st.markdown(f"**{db_name}** &nbsp; `{db_sym}` &nbsp; {subtype} &nbsp; {mcap_label}")

        valuation_mode = st.radio(
            "Valuation mode",
            ["Single-Stage P/B", "Two-Stage P/B", "Fade Model", "Reverse Valuation"],
            key="fin_val_mode",
            horizontal=False,
        )

        st.markdown("**Core assumptions**")
        roe_pct    = st.slider("ROE (%)", 5, 40, roe_pct_default, 1)
        retention  = st.slider("Retention Ratio (%)", 20, 100, int(defs["default_retention"] * 100), 5)
        coe_pct    = st.slider("Cost of Equity — CoE (%)", 8, 22, int(defs["base_coe"] * 100), 1)

        override_g = st.checkbox("Override growth manually", key="fin_override_g")
        auto_g_pct = int(round(roe_pct * retention / 100))
        if override_g:
            g_pct = st.slider("Sustainable Growth (%)", 0, 25, auto_g_pct, 1)
        else:
            g_pct = auto_g_pct
            st.caption(f"Auto growth: ROE {roe_pct}% × Retention {retention}% = **{g_pct}%**")

        roe   = roe_pct   / 100
        coe   = coe_pct   / 100
        g     = g_pct     / 100
        ret   = retention / 100

        show_multistage = valuation_mode in ("Two-Stage P/B", "Fade Model", "Reverse Valuation")
        if show_multistage:
            st.divider()
            st.markdown("**Multi-stage assumptions**")
            fade_years   = st.slider("Fade duration (years)", 2, 20, defs["default_fade_years"], 1)
            t_roe_pct    = st.slider("Terminal ROE (%)", 8, 25, int(defs["terminal_roe"] * 100), 1)
            t_growth_pct = st.slider("Terminal Growth (%)", 3, 12, int(defs["terminal_growth"] * 100), 1)
            roe_t = t_roe_pct    / 100
            g_t   = t_growth_pct / 100
        else:
            fade_years = defs["default_fade_years"]
            roe_t = defs["terminal_roe"]
            g_t   = defs["terminal_growth"]

        st.divider()
        st.markdown("**Market inputs**")
        current_pb = st.number_input(
            "Current Market P/B",
            min_value=0.1, max_value=50.0,
            value=float(pb_market_default), step=0.1,
        )
        if company_row is not None and db_pb:
            st.caption(f"Pre-filled from DB: {db_name}")

    # ── Calculations ──────────────────────────────────────────────────────────
    pb_single = justified_pb_single_stage(roe, coe, g)
    pb_two    = justified_pb_two_stage(roe, coe, g, fade_years, roe_t, g_t)
    pb_fade   = justified_pb_fade_model(roe, roe_t, g, g_t, coe, fade_years)

    if valuation_mode == "Single-Stage P/B":
        primary_pb = pb_single
    elif valuation_mode == "Two-Stage P/B":
        primary_pb = pb_two
    elif valuation_mode == "Fade Model":
        primary_pb = pb_fade
    else:
        primary_pb = pb_single  # reverse uses single-stage as anchor

    justified_pe = justified_pe_from_pb(primary_pb, roe) if primary_pb else None
    excess = roe - coe

    # ── Results panel ─────────────────────────────────────────────────────────
    with col_results:
        st.subheader("Result")

        color  = "green" if excess > 0 else "red"
        signal = "Value-creative" if excess > 0 else "Value-neutral / destructive"
        st.markdown(
            f"**ROE − CoE = {excess*100:.1f}%** &nbsp;"
            f'<span style="color:{color}">{signal}</span>',
            unsafe_allow_html=True,
        )

        # Warnings
        if coe <= g:
            st.warning(f"Growth ({g*100:.0f}%) ≥ CoE ({coe*100:.0f}%): single-stage formula invalid.")
        if roe <= coe:
            st.error(f"ROE ({roe*100:.0f}%) ≤ CoE ({coe*100:.0f}%): no economic value creation.")
        elif excess < 0.02:
            st.warning("ROE barely exceeds CoE — P/B is highly sensitive to small input changes.")
        if g > sustainable_growth_rate(roe, ret) * 1.2:
            st.warning(f"Manual growth ({g*100:.0f}%) materially exceeds sustainable ({auto_g_pct}%).")

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Current P/B", f"{current_pb:.1f}x")
        mc2.metric("Justified P/B", f"{primary_pb:.2f}x" if primary_pb else "N/A",
                   help=f"Mode: {valuation_mode}")
        mc3.metric("Justified P/E", f"{justified_pe:.1f}x" if justified_pe else "N/A",
                   help="Derived: Justified P/B ÷ ROE")
        if primary_pb:
            gap = current_pb - primary_pb
            mc4.metric(
                "Market vs Justified",
                f"{abs(gap):.2f}x {'above' if gap > 0 else 'below'}",
                delta=f"{gap / primary_pb * 100:+.1f}%",
                delta_color="inverse",
            )

        if primary_pb:
            st.info(_interpret_pb(current_pb, primary_pb))

        # ── Tabs ──────────────────────────────────────────────────────────────
        tab_summary, tab_sens, tab_reverse, tab_formula = st.tabs([
            "Summary", "Sensitivity", "Reverse Valuation", "Formula Reference",
        ])

        # ── Summary ───────────────────────────────────────────────────────────
        with tab_summary:
            s1, s2, s3 = st.columns(3)
            with s1:
                st.markdown("**ROE ladder** (current CoE & g)")
                for r in [0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.25]:
                    pb = justified_pb_single_stage(r, coe, g)
                    marker = " ◀" if abs(r - roe) < 0.005 else ""
                    st.markdown(f"ROE {r*100:.0f}% → **{pb:.2f}x**{marker}" if pb else f"ROE {r*100:.0f}% → N/A{marker}")
            with s2:
                st.markdown("**CoE ladder** (current ROE & g)")
                for c in [0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.18]:
                    pb = justified_pb_single_stage(roe, c, g)
                    marker = " ◀" if abs(c - coe) < 0.005 else ""
                    st.markdown(f"CoE {c*100:.0f}% → **{pb:.2f}x**{marker}" if pb else f"CoE {c*100:.0f}% → N/A{marker}")
            with s3:
                st.markdown("**Fade duration ladder** (two-stage)")
                for y in [3, 5, 7, 8, 10, 12, 15]:
                    pb = justified_pb_two_stage(roe, coe, g, y, roe_t, g_t)
                    marker = " ◀" if y == fade_years else ""
                    st.markdown(f"{y}y → **{pb:.2f}x**{marker}" if pb else f"{y}y → N/A{marker}")

        # ── Sensitivity ───────────────────────────────────────────────────────
        with tab_sens:
            st.subheader("ROE × CoE → Justified P/B")
            st.caption(f"Growth fixed at {g*100:.1f}%")
            df1 = sensitivity_roe_coe(g)
            st.dataframe(df1.style.map(_color_pb), use_container_width=True)

            st.divider()
            st.subheader("ROE × Growth → Justified P/B")
            st.caption(f"CoE fixed at {coe*100:.0f}%")
            df2 = sensitivity_roe_growth(coe)
            st.dataframe(df2.style.map(_color_pb), use_container_width=True)

            if show_multistage:
                st.divider()
                st.subheader("Fade Years × Terminal ROE → Justified P/B")
                st.caption(f"Current ROE = {roe*100:.0f}%  ·  CoE = {coe*100:.0f}%  ·  g_high = {g*100:.0f}%  ·  g_terminal = {g_t*100:.1f}%")
                df3 = sensitivity_fade_terminal_roe(roe, coe, g, g_t)
                st.dataframe(df3.style.map(_color_pb), use_container_width=True)

            st.caption("Green < 1.5x · Yellow 1.5–2.5x · Orange 2.5–4x · Red > 4x")

        # ── Reverse Valuation ──────────────────────────────────────────────────
        with tab_reverse:
            st.subheader("Reverse Valuation — what is the market pricing in?")
            st.caption(f"Solving for implied inputs at current market P/B = **{current_pb:.1f}x**")

            imp_roe = implied_roe_from_pb(current_pb, coe, g)
            imp_g   = implied_growth_from_pb(current_pb, roe, coe)
            imp_fade = implied_fade_years(current_pb, roe, coe, g, roe_t, g_t) if show_multistage else None

            r1, r2, r3 = st.columns(3)
            r1.metric(
                "Implied ROE",
                f"{imp_roe*100:.1f}%" if imp_roe else "—",
                help="From single-stage P/B at current g and CoE",
            )
            r2.metric(
                "Implied Growth",
                f"{imp_g*100:.1f}%" if imp_g else "—",
                help="From single-stage P/B at current ROE and CoE",
            )
            if show_multistage:
                r3.metric(
                    "Implied Fade Duration",
                    f"{imp_fade}y" if imp_fade else "—",
                    help="Two-stage P/B closest to current market P/B",
                )

            st.markdown("**Interpretation**")
            st.info(_interpret_reverse(imp_roe, roe, coe))

            if imp_g is not None:
                sust = sustainable_growth_rate(roe, ret)
                label = "reasonable" if imp_g <= sust * 1.1 else "above sustainable — optimistic"
                st.markdown(f"Implied growth **{imp_g*100:.1f}%** vs sustainable growth **{sust*100:.1f}%** → *{label}*")

            # Sweep table: which ROCE × fade year combos produce current P/B
            if show_multistage:
                st.divider()
                st.markdown(f"**Two-stage combos within ±5% of {current_pb:.1f}x:**")
                rows = []
                for tr in np.arange(0.10, 0.30, 0.01):
                    for y in [3, 5, 7, 8, 10, 12, 15]:
                        pb = justified_pb_two_stage(tr, coe, g, y, roe_t, g_t)
                        if pb and abs(pb - current_pb) / current_pb < 0.05:
                            rows.append({
                                "Implied ROE": f"{tr*100:.0f}%",
                                "Fade (yrs)": y,
                                "Justified P/B": f"{pb:.2f}x",
                            })
                if rows:
                    st.dataframe(
                        pd.DataFrame(rows).drop_duplicates(subset=["Implied ROE", "Fade (yrs)"]),
                        use_container_width=True, hide_index=True,
                    )
                else:
                    st.info("No ROE (10–30%) × Fade (3–15y) combo produces ≈ current P/B with these assumptions.")

        # ── Formula Reference ──────────────────────────────────────────────────
        with tab_formula:
            st.markdown("""
**Sustainable Growth**
```
g = ROE × Retention
```

**Single-Stage Justified P/B**
```
P/B = (ROE − g) / (CoE − g)
```
When ROE = CoE: P/B = 1.0 regardless of growth — excess growth adds zero value.
When ROE < CoE: P/B < 1 — equity is worth less than book.

**Derived Justified P/E**
```
P/E = Justified P/B / ROE
```

**Residual Income (Two-Stage) Framework**
```
P₀ = B₀ + Σ(t=1..n) [ (ROEₜ − CoE) × B_{t−1} ] / (1+CoE)ᵗ
   + Terminal RI / (CoE − g_terminal) × (1+g_high)ⁿ / (1+CoE)ⁿ
```
Where:
- B₀ = current book value per share
- (ROEₜ − CoE) × B_{t-1} = residual income in period t
- Terminal RI fades toward long-run equilibrium

**Key principle:**
| ROE vs CoE | Economic Meaning |
|---|---|
| ROE > CoE | Value creation — franchise worth P/B > 1 |
| ROE = CoE | No excess return — P/B = 1 |
| ROE < CoE | Value destruction — P/B < 1 |
""")


if __name__ == "__main__":
    main()
