
import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="U.S. Funding Conditions",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA = Path("data")


# ============================================================
# STYLE
# ============================================================

st.markdown("""
<style>

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

[data-testid="stMetricValue"] {
    font-size: 1.65rem;
}

[data-testid="stMetricLabel"] {
    font-size: 0.90rem;
}

.small-note {
    font-size: 0.82rem;
    color: #888;
}

.section-note {
    font-size: 0.88rem;
    color: #888;
    margin-bottom: 0.8rem;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA LOADERS
# ============================================================

@st.cache_data
def load_data():

    rates = pd.read_csv(
        DATA / "raw_rates.csv",
        index_col=0,
        parse_dates=True
    )

    spreads = pd.read_csv(
        DATA / "spreads.csv",
        index_col=0,
        parse_dates=True
    )

    cp = pd.read_csv(
        DATA / "cp_monitor.csv",
        index_col=0,
        parse_dates=True
    )

    latest_rates = pd.read_csv(
        DATA / "latest_rates.csv"
    )

    latest_spreads = pd.read_csv(
        DATA / "latest_spreads.csv"
    )

    latest_cp = pd.read_csv(
        DATA / "latest_cp.csv"
    )

    quality = pd.read_csv(
        DATA / "data_quality.csv"
    )

    with open(DATA / "metadata.json", "r") as f:
        metadata = json.load(f)

    return (
        rates,
        spreads,
        cp,
        latest_rates,
        latest_spreads,
        latest_cp,
        quality,
        metadata
    )


(
    rates,
    spreads,
    cp,
    latest_rates,
    latest_spreads,
    latest_cp,
    quality,
    metadata
) = load_data()


# ============================================================
# HELPERS
# ============================================================

def line_chart(
    df,
    columns,
    title,
    ytitle,
    zero_line=False
):

    fig = go.Figure()

    for col in columns:

        if col not in df.columns:
            continue

        x = df[col].dropna()

        fig.add_trace(
            go.Scatter(
                x=x.index,
                y=x.values,
                mode="lines",
                name=col,
                line=dict(width=1.6)
            )
        )

    if zero_line:
        fig.add_hline(
            y=0,
            line_dash="dot",
            opacity=0.5
        )

    fig.update_layout(
        title=title,
        yaxis_title=ytitle,
        xaxis_title="",
        hovermode="x unified",
        height=480,
        margin=dict(l=20, r=20, t=55, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )

    return fig


def get_rate(name):

    row = latest_rates[
        latest_rates["Series"] == name
    ]

    if row.empty:
        return np.nan, None

    return (
        float(row.iloc[0]["Current"]),
        str(row.iloc[0]["Date"])
    )


def get_spread(name):

    row = latest_spreads[
        latest_spreads["Spread"] == name
    ]

    if row.empty:
        return None

    return row.iloc[0]


def regime_from_composite(z):

    if pd.isna(z):
        return "N/A"

    if z >= 2:
        return "Extreme Stress"

    if z >= 1:
        return "Elevated Stress"

    if z <= -1:
        return "Compressed"

    return "Normal"


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("U.S. Funding Conditions")

page = st.sidebar.radio(
    "Section",
    [
        "Overview",
        "Funding Basis",
        "Commercial Paper",
        "Cross-Market Funding",
        "Persistence",
        "Data & Methodology"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    "Federal Reserve Bank of New York / "
    "Federal Reserve / FRED"
)


# ============================================================
# HEADER
# ============================================================

st.title("U.S. Funding Conditions")

st.caption(
    "Short-term funding, repo-market basis, commercial-paper "
    "credit conditions and persistence."
)


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":

    # --------------------------------------------------------
    # CURRENT POLICY / FUNDING RATES
    # --------------------------------------------------------

    st.subheader("Current Funding Rates")

    names = [
        "SOFR",
        "EFFR",
        "IORB",
        "ON_RRP",
        "TGCR",
        "BGCR"
    ]

    cols = st.columns(6)

    for c, name in zip(cols, names):

        value, date = get_rate(name)

        with c:

            st.metric(
                name.replace("_", " "),
                f"{value:.2f}%"
                if pd.notna(value)
                else "N/A"
            )

            if date:
                st.caption(date)


    # --------------------------------------------------------
    # KEY BASIS
    # --------------------------------------------------------

    st.divider()
    st.subheader("Key Funding Basis")

    key_spreads = [
        "SOFR-EFFR",
        "TGCR-SOFR",
        "SOFR-IORB",
        "EFFR-IORB",
        "SOFR-ON_RRP"
    ]

    cols = st.columns(len(key_spreads))

    for c, name in zip(cols, key_spreads):

        row = get_spread(name)

        with c:

            if row is not None:

                st.metric(
                    name,
                    f"{row['Current_bp']:.1f} bp"
                )

                st.caption(
                    f"1Y z: {row['Z_1Y']:.2f}"
                )


    # --------------------------------------------------------
    # CP STRESS
    # --------------------------------------------------------

    st.divider()
    st.subheader("Commercial-Paper Credit Conditions")

    composite = (
        cp["CP_Stress_Composite"]
        .dropna()
    )

    latest_composite = composite.iloc[-1]
    latest_date = composite.index[-1]

    cp30 = latest_cp[
        latest_cp["Maturity"] == "30D"
    ].iloc[0]

    cp60 = latest_cp[
        latest_cp["Maturity"] == "60D"
    ].iloc[0]

    cp90 = latest_cp[
        latest_cp["Maturity"] == "90D"
    ].iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "CP Stress Composite",
        f"{latest_composite:.2f}σ"
    )

    c1.caption(
        regime_from_composite(
            latest_composite
        )
    )

    c2.metric(
        "30D A2/P2 − AA",
        f"{cp30['Spread_bp']:.0f} bp"
    )

    c2.caption(
        f"1Y z: {cp30['Z_1Y']:.2f}"
    )

    c3.metric(
        "60D A2/P2 − AA",
        f"{cp60['Spread_bp']:.0f} bp"
    )

    c3.caption(
        f"1Y z: {cp60['Z_1Y']:.2f}"
    )

    c4.metric(
        "90D A2/P2 − AA",
        f"{cp90['Spread_bp']:.0f} bp"
    )

    c4.caption(
        f"1Y z: {cp90['Z_1Y']:.2f}"
    )


    # --------------------------------------------------------
    # COMPOSITE CHART
    # --------------------------------------------------------

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=composite.index,
            y=composite.values,
            mode="lines",
            name="CP Stress Composite"
        )
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        opacity=0.5
    )

    fig.add_hline(
        y=1,
        line_dash="dash",
        opacity=0.35
    )

    fig.add_hline(
        y=-1,
        line_dash="dash",
        opacity=0.35
    )

    fig.update_layout(
        title="Commercial-Paper Funding Stress Composite",
        yaxis_title="Z-score",
        xaxis_title="",
        hovermode="x unified",
        height=500,
        margin=dict(l=20, r=20, t=55, b=20)
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.caption(
        f"Latest composite observation: "
        f"{latest_date.date()}"
    )


# ============================================================
# FUNDING BASIS
# ============================================================

elif page == "Funding Basis":

    st.subheader("Funding & Repo Basis")

    basis_groups = {

        "Overnight / Repo": [
            "SOFR-EFFR",
            "TGCR-SOFR",
            "BGCR-TGCR"
        ],

        "Administered Rate Basis": [
            "SOFR-IORB",
            "EFFR-IORB",
            "SOFR-ON_RRP"
        ]
    }

    group = st.radio(
        "Basis family",
        list(basis_groups.keys()),
        horizontal=True
    )

    selected = st.multiselect(
        "Series",
        basis_groups[group],
        default=basis_groups[group]
    )

    st.plotly_chart(
        line_chart(
            spreads,
            selected,
            group,
            "Basis points",
            zero_line=True
        ),
        use_container_width=True
    )


    # --------------------------------------------------------
    # CURRENT ANALYTICS TABLE
    # --------------------------------------------------------

    table = latest_spreads[
        latest_spreads["Spread"].isin(
            basis_groups[group]
        )
    ].copy()

    cols = [
        "Spread",
        "End",
        "Current_bp",
        "Percentile",
        "Z_Full",
        "Z_1Y",
        "AR1_phi",
        "HalfLife_obs",
        "ADF_p",
        "Regime"
    ]

    table = table[cols]

    table.columns = [
        "Spread",
        "Date",
        "Current (bp)",
        "Hist. Percentile",
        "Full Z",
        "1Y Z",
        "AR(1)",
        "Half-Life",
        "ADF p",
        "Regime"
    ]

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# COMMERCIAL PAPER
# ============================================================

elif page == "Commercial Paper":

    st.subheader("Commercial-Paper Credit")

    cp_credit_cols = [
        "A2P2-AA_NF_30D",
        "A2P2-AA_NF_60D",
        "A2P2-AA_NF_90D"
    ]

    st.plotly_chart(
        line_chart(
            spreads,
            cp_credit_cols,
            "A2/P2 − AA Nonfinancial Commercial Paper",
            "Basis points",
            zero_line=True
        ),
        use_container_width=True
    )


    # --------------------------------------------------------
    # CURRENT CP TABLE
    # --------------------------------------------------------

    display_cp = latest_cp.copy()

    display_cp = display_cp[
        [
            "Maturity",
            "Date",
            "Spread_bp",
            "Z_1Y",
            "Z_3Y",
            "Pct_1Y",
            "Vol_63D",
            "AR1_1Y",
            "HalfLife_1Y",
            "Regime"
        ]
    ]

    display_cp.columns = [
        "Maturity",
        "Date",
        "Spread (bp)",
        "1Y Z",
        "3Y Z",
        "1Y Percentile",
        "63D Vol",
        "1Y AR(1)",
        "1Y Half-Life",
        "Regime"
    ]

    st.dataframe(
        display_cp,
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # OTHER CP RELATIONSHIPS
    # --------------------------------------------------------

    st.divider()
    st.subheader("Sector & Term Structure")

    option = st.radio(
        "View",
        [
            "AA Financial − AA Nonfinancial",
            "CP Term Structure"
        ],
        horizontal=True
    )

    if option == "AA Financial − AA Nonfinancial":

        cols = [
            "AA_FIN-AA_NF_30D",
            "AA_FIN-AA_NF_60D",
            "AA_FIN-AA_NF_90D"
        ]

    else:

        cols = [
            "AA_FIN_90D-30D",
            "AA_NF_90D-30D",
            "A2P2_NF_90D-30D"
        ]

    st.plotly_chart(
        line_chart(
            spreads,
            cols,
            option,
            "Basis points",
            zero_line=True
        ),
        use_container_width=True
    )


# ============================================================
# CROSS-MARKET FUNDING
# ============================================================

elif page == "Cross-Market Funding":

    st.subheader("Commercial Paper vs Overnight Funding")

    st.caption(
        "Compares term commercial-paper rates with overnight "
        "money-market benchmarks. These spreads contain credit, "
        "liquidity and maturity / expected-policy-rate effects "
        "and should not be interpreted as pure credit spreads."
    )

    # --------------------------------------------------------
    # BENCHMARK SELECTION
    # --------------------------------------------------------

    benchmark = st.radio(
        "Overnight benchmark",
        ["SOFR", "EFFR"],
        horizontal=True
    )

    cp_type = st.radio(
        "Commercial-paper category",
        [
            "AA Financial",
            "AA Nonfinancial",
            "A2/P2 Nonfinancial"
        ],
        horizontal=True
    )


    # --------------------------------------------------------
    # MAP CP SERIES
    # --------------------------------------------------------

    cp_map = {

        "AA Financial": {
            "30D": "AA_FIN_30D",
            "60D": "AA_FIN_60D",
            "90D": "AA_FIN_90D"
        },

        "AA Nonfinancial": {
            "30D": "AA_NF_30D",
            "60D": "AA_NF_60D",
            "90D": "AA_NF_90D"
        },

        "A2/P2 Nonfinancial": {
            "30D": "A2P2_NF_30D",
            "60D": "A2P2_NF_60D",
            "90D": "A2P2_NF_90D"
        }
    }


    # --------------------------------------------------------
    # CONSTRUCT PAIRWISE SPREADS
    #
    # No forward filling.
    # Each tenor uses dates where BOTH series are observed.
    # --------------------------------------------------------

    cross = pd.DataFrame()

    for tenor, cp_col in cp_map[cp_type].items():

        pair = pd.concat(
            [
                rates[cp_col],
                rates[benchmark]
            ],
            axis=1,
            join="inner"
        ).dropna()

        cross[
            f"{tenor} CP − {benchmark}"
        ] = (
            pair[cp_col]
            - pair[benchmark]
        ) * 100


    # --------------------------------------------------------
    # CURRENT ANALYTICS
    # --------------------------------------------------------

    rows = []

    for col in cross.columns:

        x = cross[col].dropna()

        if len(x) == 0:
            continue

        current = x.iloc[-1]

        mean = x.mean()
        sd = x.std()

        z_full = (
            (current - mean) / sd
            if sd > 0
            else np.nan
        )

        x1 = x.iloc[-252:]

        sd1 = x1.std()

        z_1y = (
            (current - x1.mean()) / sd1
            if len(x1) > 1 and sd1 > 0
            else np.nan
        )

        percentile = (
            (x <= current).mean() * 100
        )

        rows.append({

            "Spread": col,

            "Date":
                x.index[-1].date(),

            "Current (bp)":
                current,

            "Historical Mean (bp)":
                mean,

            "Historical Percentile":
                percentile,

            "Full Z":
                z_full,

            "1Y Z":
                z_1y,

            "Start":
                x.index[0].date(),

            "Observations":
                len(x)
        })


    cross_snapshot = pd.DataFrame(rows)


    # --------------------------------------------------------
    # CURRENT CARDS
    # --------------------------------------------------------

    if len(cross_snapshot):

        metric_cols = st.columns(
            len(cross_snapshot)
        )

        for c, (_, row) in zip(
            metric_cols,
            cross_snapshot.iterrows()
        ):

            with c:

                st.metric(
                    row["Spread"],
                    f"{row['Current (bp)']:.0f} bp"
                )

                st.caption(
                    f"1Y z: {row['1Y Z']:.2f} | "
                    f"Pct: {row['Historical Percentile']:.0f}%"
                )


    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    st.plotly_chart(
        line_chart(
            cross,
            list(cross.columns),
            f"{cp_type} CP − {benchmark}",
            "Basis points",
            zero_line=True
        ),
        use_container_width=True
    )


    # --------------------------------------------------------
    # ANALYTICS TABLE
    # --------------------------------------------------------

    st.dataframe(
        cross_snapshot.round({
            "Current (bp)": 1,
            "Historical Mean (bp)": 1,
            "Historical Percentile": 1,
            "Full Z": 2,
            "1Y Z": 2
        }),
        use_container_width=True,
        hide_index=True
    )


    # --------------------------------------------------------
    # RATE LEVEL COMPARISON
    # --------------------------------------------------------

    st.divider()

    st.subheader("Rate-Level Comparison")

    level_panel = pd.DataFrame()

    level_panel[benchmark] = rates[benchmark]

    for tenor, cp_col in cp_map[cp_type].items():

        level_panel[
            f"{cp_type} {tenor}"
        ] = rates[cp_col]


    st.plotly_chart(
        line_chart(
            level_panel,
            list(level_panel.columns),
            f"{cp_type} vs {benchmark}",
            "Rate (%)",
            zero_line=False
        ),
        use_container_width=True
    )


    st.info(
        "Interpretation: CP minus overnight funding is a broad "
        "corporate funding premium. Because CP is term unsecured "
        "funding while SOFR is overnight secured funding and EFFR "
        "is overnight unsecured interbank funding, the spread is "
        "not a maturity-matched pure credit premium."
    )


# ============================================================
# PERSISTENCE
# ============================================================

elif page == "Persistence":

    st.subheader("Commercial-Paper Persistence")

    maturity = st.selectbox(
        "Maturity",
        ["30D", "60D", "90D"]
    )

    ar_col = f"CP_{maturity}_AR1_1Y"
    hl_col = f"CP_{maturity}_HalfLife_1Y"

    ar3_col = f"CP_{maturity}_AR1_3Y"
    hl3_col = f"CP_{maturity}_HalfLife_3Y"


    # --------------------------------------------------------
    # CURRENT METRICS
    # --------------------------------------------------------

    row = latest_cp[
        latest_cp["Maturity"] == maturity
    ].iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "1Y AR(1)",
        f"{row['AR1_1Y']:.3f}"
    )

    c2.metric(
        "1Y Half-Life",
        f"{row['HalfLife_1Y']:.2f} obs."
    )

    c3.metric(
        "3Y AR(1)",
        f"{row['AR1_3Y']:.3f}"
    )

    c4.metric(
        "3Y Half-Life",
        f"{row['HalfLife_3Y']:.2f} obs."
    )


    # --------------------------------------------------------
    # AR CHART
    # --------------------------------------------------------

    st.plotly_chart(
        line_chart(
            cp,
            [ar_col, ar3_col],
            f"{maturity} Rolling AR(1)",
            "AR(1)",
            zero_line=False
        ),
        use_container_width=True
    )


    # --------------------------------------------------------
    # HALF LIFE CHART
    # --------------------------------------------------------

    st.plotly_chart(
        line_chart(
            cp,
            [hl_col, hl3_col],
            f"{maturity} Rolling Mean-Reversion Half-Life",
            "Observations",
            zero_line=False
        ),
        use_container_width=True
    )

    st.caption(
        "Half-life is reported only where 0 < AR(1) < 1."
    )


# ============================================================
# DATA & METHODOLOGY
# ============================================================

elif page == "Data & Methodology":

    st.subheader("Data Coverage")

    quality_display = quality[
        [
            "Series",
            "Start",
            "End",
            "Observations"
        ]
    ].copy()

    st.dataframe(
        quality_display,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("Methodology")

    methodology = metadata.get(
        "methodology",
        {}
    )

    for key, value in methodology.items():

        st.markdown(
            f"**{key.replace('_', ' ').title()}**"
        )

        st.write(value)

    st.divider()

    st.subheader("Sources")

    sources = metadata.get(
        "sources",
        {}
    )

    for key, value in sources.items():

        st.write(
            f"**{key.replace('_', ' ')}:** {value}"
        )

    st.divider()

    st.caption(
        "This application is an analytical market-monitoring "
        "tool and does not constitute investment advice."
    )
