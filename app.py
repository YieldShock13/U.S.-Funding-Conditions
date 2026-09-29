
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
def load_data(data_version="v2.0-calendar-window"):

    # data_version intentionally participates in Streamlit's
    # cache key. Increment whenever production data schemas
    # or methodology change.


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

    # --------------------------------------------------------
    # PRODUCTION SCHEMA VALIDATION
    # --------------------------------------------------------

    required_cp = {
        "Maturity",
        "Date",
        "Spread_bp",
        "Z_1Y",
        "Z_3Y",
        "Pct_1Y",
        "Vol_63obs",
        "AR1_1Y",
        "HalfLife_1Y_obs",
        "AR1_3Y",
        "HalfLife_3Y_obs",
        "Regime"
    }

    required_spreads = {
        "Spread",
        "End",
        "Current_bp",
        "Full_Percentile",
        "Pct_1Y",
        "Z_Full",
        "Z_1Y",
        "AR1_1Y",
        "HalfLife_1Y_obs",
        "ADF_p",
        "Regime"
    }

    required_monitor = {
        "CP_Stress_Composite",
        "CP_30D_AR1_1Y",
        "CP_30D_HalfLife_1Y_obs",
        "CP_60D_AR1_1Y",
        "CP_60D_HalfLife_1Y_obs",
        "CP_90D_AR1_1Y",
        "CP_90D_HalfLife_1Y_obs"
    }

    missing_cp = required_cp - set(latest_cp.columns)
    missing_spreads = required_spreads - set(latest_spreads.columns)
    missing_monitor = required_monitor - set(cp.columns)

    if missing_cp:
        raise RuntimeError(
            f"latest_cp.csv schema mismatch: {sorted(missing_cp)}"
        )

    if missing_spreads:
        raise RuntimeError(
            "latest_spreads.csv schema mismatch: "
            f"{sorted(missing_spreads)}"
        )

    if missing_monitor:
        raise RuntimeError(
            "cp_monitor.csv schema mismatch: "
            f"{sorted(missing_monitor)}"
        )

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
) = load_data("v2.0-calendar-window-20260930")


# ============================================================
# HELPERS
# ============================================================


def robust_y_range(df, columns, nonnegative=False):
    """
    Calculate presentation-only robust y-axis limits.
    Does NOT alter the underlying observations.
    """

    available = [c for c in columns if c in df.columns]

    if not available:
        return None

    values = (
        df[available]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy()
        .ravel()
    )

    values = values[np.isfinite(values)]

    if len(values) < 5:
        return None

    upper = float(np.nanpercentile(values, 99))

    if nonnegative:
        lower = 0.0
    else:
        lower = float(np.nanpercentile(values, 1))

    if not np.isfinite(lower) or not np.isfinite(upper):
        return None

    if upper <= lower:
        return None

    span = upper - lower

    if nonnegative:
        upper += span * 0.05
    else:
        lower -= span * 0.05
        upper += span * 0.05

    return [lower, upper]


def line_chart(
    df,
    columns,
    title,
    ytitle,
    zero_line=False,
    robust_y=False,
    nonnegative_y=False
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


    # Presentation-only Y-axis scaling.
    # Underlying observations remain completely unchanged.
    if robust_y:
        yrange = robust_y_range(
            df,
            columns,
            nonnegative=nonnegative_y
        )

        if yrange is not None:
            fig.update_yaxes(range=yrange)

    return fig



def chart_y_control(key, default="Robust"):

    options = [
        "Robust",
        "Full range"
    ]

    return st.radio(
        "Y-axis",
        options,
        index=options.index(default),
        horizontal=True,
        key=f"{key}_yaxis"
    )


def chart_date_control(df, key, default="3Y"):
    """
    Presentation-layer chart filter only.

    This function does NOT recalculate analytics. It only
    returns a date-filtered view for plotting.
    """

    if df is None or len(df) == 0:
        return df

    data = df.copy()

    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)

    valid_index = data.index[
        ~data.index.isna()
    ]

    if len(valid_index) == 0:
        return data

    data_start = valid_index.min()
    data_end = valid_index.max()

    options = [
        "1M",
        "3M",
        "6M",
        "1Y",
        "3Y",
        "5Y",
        "10Y",
        "All",
        "Custom"
    ]

    if default not in options:
        default = "3Y"

    period = st.radio(
        "Chart range",
        options,
        index=options.index(default),
        horizontal=True,
        key=f"{key}_range"
    )

    if period == "All":
        start = data_start
        end = data_end

    elif period == "Custom":

        c1, c2 = st.columns(2)

        with c1:
            start_date = st.date_input(
                "Start date",
                value=data_start.date(),
                min_value=data_start.date(),
                max_value=data_end.date(),
                key=f"{key}_start"
            )

        with c2:
            end_date = st.date_input(
                "End date",
                value=data_end.date(),
                min_value=data_start.date(),
                max_value=data_end.date(),
                key=f"{key}_end"
            )

        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)

        if start > end:
            st.warning(
                "Start date is after end date."
            )
            return data.iloc[0:0]

    else:

        offsets = {
            "1M": pd.DateOffset(months=1),
            "3M": pd.DateOffset(months=3),
            "6M": pd.DateOffset(months=6),
            "1Y": pd.DateOffset(years=1),
            "3Y": pd.DateOffset(years=3),
            "5Y": pd.DateOffset(years=5),
            "10Y": pd.DateOffset(years=10)
        }

        end = data_end
        start = end - offsets[period]

    return data.loc[
        (data.index >= start)
        & (data.index <= end)
    ]


def filter_chart_data(df, period):
    """
    Internal presentation-only filter for cases where the
    page has already collected the user's range selection.
    """

    if period is None:
        return df

    return df



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

    composite_chart = chart_date_control(
        composite.to_frame(
            name="CP_Stress_Composite"
        ),
        key="overview_cp_composite"
    )["CP_Stress_Composite"].dropna()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=composite_chart.index,
            y=composite_chart.values,
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

    basis_chart = chart_date_control(
        spreads,
        key="funding_basis"
    )

    basis_y = chart_y_control(
        key="funding_basis"
    )

    st.plotly_chart(
        line_chart(
            basis_chart,
            selected,
            group,
            "Basis points",
            zero_line=True,
            robust_y=(basis_y == "Robust")
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
        "Full_Percentile",
        "Pct_1Y",
        "Z_Full",
        "Z_1Y",
        "AR1_1Y",
        "HalfLife_1Y_obs",
        "ADF_p",
        "Regime"
    ]

    table = table[cols]

    table.columns = [
        "Spread",
        "Date",
        "Current (bp)",
        "Full-History Percentile",
        "1Y Percentile",
        "Full Z",
        "1Y Z",
        "1Y AR(1)",
        "1Y Half-Life (obs.)",
        "ADF p",
        "Regime"
    ]

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True
    )


    st.caption(
        "1Y statistics use observations occurring within the "
        "trailing one calendar year. They do not assume 252 "
        "observations per year."
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

    cp_chart_data = chart_date_control(
        spreads,
        key="commercial_paper"
    )

    cp_y = chart_y_control(
        key="commercial_paper"
    )

    st.plotly_chart(
        line_chart(
            cp_chart_data,
            cp_credit_cols,
            "A2/P2 − AA Nonfinancial Commercial Paper",
            "Basis points",
            zero_line=True,
            robust_y=(cp_y == "Robust")
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
            "Vol_63obs",
            "AR1_1Y",
            "HalfLife_1Y_obs",
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
        "63-Observation Vol",
        "1Y AR(1)",
        "1Y Half-Life (obs.)",
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
            cp_chart_data,
            cols,
            option,
            "Basis points",
            zero_line=True,
            robust_y=(cp_y == "Robust")
        ),
        use_container_width=True
    )


# ============================================================
# CROSS-MARKET FUNDING
# ============================================================

elif page == "Cross-Market Funding":

    st.subheader("CP–Overnight Funding Differentials")

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

        # Genuine trailing calendar year.
        end_1y = x.index[-1]
        start_1y = end_1y - pd.DateOffset(years=1)

        x1 = x.loc[
            x.index >= start_1y
        ]

        sd1 = x1.std()

        z_1y = (
            (current - x1.mean()) / sd1
            if len(x1) > 1 and sd1 > 0
            else np.nan
        )

        full_percentile = (
            (x <= current).mean() * 100
        )

        pct_1y = (
            (x1 <= current).mean() * 100
            if len(x1)
            else np.nan
        )

        rows.append({

            "Spread": col,

            "Date":
                x.index[-1].date(),

            "Current (bp)":
                current,

            "Historical Mean (bp)":
                mean,

            "Full-History Percentile":
                full_percentile,

            "1Y Percentile":
                pct_1y,

            "1Y Observations":
                len(x1),

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
                    f"1Y pct: {row['1Y Percentile']:.0f}%"
                )


    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    cross_chart = chart_date_control(
        cross,
        key="cross_market"
    )

    cross_y = chart_y_control(
        key="cross_market"
    )

    st.plotly_chart(
        line_chart(
            cross_chart,
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
            "Full-History Percentile": 1,
            "1Y Percentile": 1,
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


    # Match the level chart to the already selected
    # cross-market display interval.
    if len(cross_chart):
        chart_start = cross_chart.index.min()
        chart_end = cross_chart.index.max()

        level_chart = level_panel.loc[
            (level_panel.index >= chart_start)
            & (level_panel.index <= chart_end)
        ]
    else:
        level_chart = level_panel.iloc[0:0]

    st.plotly_chart(
        line_chart(
            level_chart,
            list(level_panel.columns),
            f"{cp_type} vs {benchmark}",
            "Rate (%)",
            zero_line=False,
            robust_y=(cross_y == "Robust")
        ),
        use_container_width=True
    )


    st.info(
        "Interpretation: CP minus overnight funding is a broad "
        "cross-market funding differential. Because CP is term unsecured "
        "funding while SOFR is overnight secured funding and EFFR "
        "is overnight unsecured interbank funding, the spread is "
        "not a maturity-matched pure credit premium."
    )


# ============================================================
# PERSISTENCE
# ============================================================

elif page == "Persistence":

    st.subheader("Commercial-Paper Persistence & Mean Reversion")

    maturity = st.selectbox(
        "Maturity",
        ["30D", "60D", "90D"]
    )

    ar_col = f"CP_{maturity}_AR1_1Y"
    hl_col = f"CP_{maturity}_HalfLife_1Y_obs"

    ar3_col = f"CP_{maturity}_AR1_3Y"
    hl3_col = f"CP_{maturity}_HalfLife_3Y_obs"


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
        f"{row['HalfLife_1Y_obs']:.2f} obs."
    )

    c3.metric(
        "3Y AR(1)",
        f"{row['AR1_3Y']:.3f}"
    )

    c4.metric(
        "3Y Half-Life",
        f"{row['HalfLife_3Y_obs']:.2f} obs."
    )


    # --------------------------------------------------------
    # AR CHART
    # --------------------------------------------------------

    persistence_chart = chart_date_control(
        cp,
        key="persistence"
    )

    persistence_y = chart_y_control(
        key="persistence"
    )

    st.plotly_chart(
        line_chart(
            persistence_chart,
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
            persistence_chart,
            [hl_col, hl3_col],
            f"{maturity} Rolling AR(1)-Implied Mean-Reversion Half-Life",
            "Observations",
            zero_line=False
        ),
        use_container_width=True
    )

    st.caption(
        "AR(1)-implied half-life is reported in observations "
        "and only where 0 < AR(1) < 1. Windows labelled 1Y "
        "and 3Y use actual calendar periods, not fixed "
        "observation counts."
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
