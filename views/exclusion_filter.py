import streamlit as st
import pandas as pd
from not_interested_db import (
    get_not_interested,
    get_not_interested_codes,
    save_not_interested_list,
    clear_all_not_interested,
)

def render_exclusion_ui(daily_df: pd.DataFrame) -> pd.DataFrame:
    st.markdown("### 🚫 Not Interested Filter")

    # Step 1: Prepare unique ID per company
    df = daily_df.copy()
    df["code_key"] = df["nse_code"].fillna(df["bse_code"])
    df = df.dropna(subset=["code_key"]).drop_duplicates(subset=["code_key"])
    df = df.sort_values("name")

    # Step 2: Load existing exclusions
    existing_exclusions = get_not_interested()
    existing_codes = [row[0] for row in existing_exclusions]

    # Step 3: UI
    enable_filter = st.checkbox("Enable filter", value=True)

    with st.expander("✂️ Manage Excluded Companies", expanded=False):
        selected_to_exclude = st.multiselect(
            "Select companies to exclude:",
            options=df["code_key"],
            format_func=lambda code: f"{code} — {df.set_index('code_key').loc[code]['name']}",
            default=existing_codes,
        )

        reason = st.text_input("Reason (applies to all selected):", "")

        if st.button("💾 Save"):
            entries = [
                (
                    code,
                    df.set_index("code_key").loc[code]["name"],
                    reason.strip(),
                )
                for code in selected_to_exclude
            ]
            save_not_interested_list(entries)
            st.success("Saved.")

        if st.button("♻️ Reset Exclusion List"):
            clear_all_not_interested()
            st.success("Cleared all.")

    # Step 4: Apply filter
    if enable_filter and existing_codes:
        daily_df = daily_df[
            ~daily_df["nse_code"].isin(existing_codes) &
            ~daily_df["bse_code"].isin(existing_codes)
        ]

    # Step 5: Show excluded list
    with st.expander("📋 Show Excluded Companies", expanded=False):
        if not existing_exclusions:
            st.info("No exclusions.")
        else:
            st.dataframe(
                pd.DataFrame(existing_exclusions, columns=["Code", "Name", "Reason"]).sort_values("Name"),
                use_container_width=True
            )

    return daily_df
