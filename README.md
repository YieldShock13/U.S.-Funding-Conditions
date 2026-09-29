# U.S. Funding Conditions

A quantitative monitor of U.S. short-term funding and money-market conditions.

## V1 Coverage

### Secured and overnight funding
- SOFR
- TGCR
- BGCR
- Effective Federal Funds Rate
- IORB
- ON RRP award rate

### Commercial paper
- AA Financial: 30D, 60D, 90D
- AA Nonfinancial: 30D, 60D, 90D
- A2/P2 Nonfinancial: 30D, 60D, 90D

### Analytics
- Funding basis spreads
- Commercial-paper credit spreads
- Commercial-paper term spreads
- Historical percentile
- Rolling and full-history z-scores
- AR(1) persistence
- Ornstein-Uhlenbeck implied half-life
- Augmented Dickey-Fuller stationarity tests
- Commercial-paper funding-stress composite

## Data Sources

Federal Reserve Bank of New York and Federal Reserve/FRED.

## Methodology

Each spread retains its own maximum pairwise history.

Raw statistical series are not forward-filled.

The synchronized commercial-paper monitoring layer permits a maximum
five-business-day carry to accommodate differing publication dates.

The CP Stress Composite is the mean trailing one-year standardized
A2/P2 minus AA Nonfinancial commercial-paper spread across the
30D, 60D and 90D maturities, requiring at least two available maturities.

## Status

V1 — Funding and Commercial Paper module.
