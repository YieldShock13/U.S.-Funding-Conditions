from pathlib import Path
import requests
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

DATA=Path("data"); DATA.mkdir(exist_ok=True)
TODAY=pd.Timestamp.utcnow().date().isoformat()
COLS=["SOFR","EFFR","IORB","ON_RRP","AA_FIN_30D","AA_FIN_60D","AA_FIN_90D","AA_NF_30D","AA_NF_60D","AA_NF_90D","A2P2_NF_30D","A2P2_NF_60D","A2P2_NF_90D","TGCR","BGCR"]
FRED={"IORB":"IORB","ON_RRP":"RRPONTSYAWARD","AA_FIN_30D":"DCPF1M","AA_FIN_60D":"DCPF2M","AA_FIN_90D":"DCPF3M","AA_NF_30D":"DCPN30","AA_NF_60D":"DCPN2M","AA_NF_90D":"DCPN3M","A2P2_NF_30D":"RIFSPPNA2P2D30NB","A2P2_NF_60D":"RIFSPPNA2P2D60NB","A2P2_NF_90D":"RIFSPPNA2P2D90NB"}
NY={"SOFR":("secured","sofr"),"TGCR":("secured","tgcr"),"BGCR":("secured","bgcr"),"EFFR":("unsecured","effr")}

def fred(sid,name):
    d=pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}")
    d.columns=["Date",name]; d["Date"]=pd.to_datetime(d["Date"]); d[name]=pd.to_numeric(d[name],errors="coerce")
    return d.set_index("Date")[[name]]

def nyfed(cat,typ,name):
    u=f"https://markets.newyorkfed.org/api/rates/{cat}/{typ}/search.json?startDate=2000-01-01&endDate={TODAY}&type=rate"
    r=requests.get(u,timeout=60); r.raise_for_status(); p=r.json(); rec=p.get("refRates",p.get("rates",p))
    if isinstance(rec,dict): rec=rec.get("rates",rec.get("refRates",[]))
    rows=[]
    for x in rec:
        dt=x.get("effectiveDate") or x.get("date"); val=x.get("percentRate") if x.get("percentRate") is not None else x.get("rate")
        if dt is not None and val is not None: rows.append((dt,val))
    d=pd.DataFrame(rows,columns=["Date",name]); d["Date"]=pd.to_datetime(d["Date"]); d[name]=pd.to_numeric(d[name],errors="coerce")
    return d.dropna().drop_duplicates("Date",keep="last").set_index("Date")

def merge_series(old,new,col):
    s=pd.concat([old[[col]],new]).sort_index()
    return s[~s.index.duplicated(keep="last")][col]

def ar1(x):
    x=pd.Series(x).dropna().to_numpy(float)
    if len(x)<3:return np.nan
    X=np.column_stack([np.ones(len(x)-1),x[:-1]])
    return float(np.linalg.lstsq(X,x[1:],rcond=None)[0][1])

def half(phi):
    return float(-np.log(2)/np.log(phi)) if pd.notna(phi) and 0<phi<1 else np.nan

def calc(x):
    x=x.dropna(); cur=x.iloc[-1]; end=x.index[-1]
    x1=x[x.index>=end-pd.DateOffset(years=1)]; x3=x[x.index>=end-pd.DateOffset(years=3)]
    def z(a): return (cur-a.mean())/a.std() if len(a)>1 and a.std()>0 else np.nan
    def pct(a): return float((a<=cur).mean()*100) if len(a) else np.nan
    p1,p3,pf=ar1(x1),ar1(x3),ar1(x)
    try: adfp=float(adfuller(x.values,regression="c",autolag="AIC")[1]) if len(x)>20 else np.nan
    except Exception: adfp=np.nan
    return {"Start":x.index[0].date(),"End":end.date(),"Current_bp":cur,"Observations":len(x),"Full_Percentile":pct(x),"Z_Full":z(x),"AR1_Full":pf,"HalfLife_Full_obs":half(pf),"ADF_p":adfp,"Start_1Y":x1.index[0].date(),"Obs_1Y":len(x1),"Pct_1Y":pct(x1),"Z_1Y":z(x1),"AR1_1Y":p1,"HalfLife_1Y_obs":half(p1),"Start_3Y":x3.index[0].date(),"Obs_3Y":len(x3),"Pct_3Y":pct(x3),"Z_3Y":z(x3),"AR1_3Y":p3,"HalfLife_3Y_obs":half(p3)}

def regime(z):
    if pd.isna(z):return "N/A"
    if z>=2:return "Very High"
    if z>=1:return "High"
    if z<=-1:return "Low"
    return "Normal"

old=pd.read_csv(DATA/"raw_rates.csv",index_col=0,parse_dates=True).sort_index()
rates=old.copy()
for name,(cat,typ) in NY.items(): rates[name]=merge_series(old,nyfed(cat,typ,name),name)
for name,sid in FRED.items(): rates[name]=merge_series(old,fred(sid,name),name)
rates=rates.reindex(columns=COLS).sort_index().dropna(how="all")
assert list(rates.columns)==COLS and rates.index.is_unique
for c in COLS: assert rates[c].count()>=old[c].count(),f"{c}: observation loss"
rates.to_csv(DATA/"raw_rates.csv",index_label="Date")

pairs={"SOFR-EFFR":("SOFR","EFFR"),"TGCR-SOFR":("TGCR","SOFR"),"BGCR-TGCR":("BGCR","TGCR"),"SOFR-IORB":("SOFR","IORB"),"EFFR-IORB":("EFFR","IORB"),"SOFR-ON_RRP":("SOFR","ON_RRP"),"A2P2-AA_NF_30D":("A2P2_NF_30D","AA_NF_30D"),"A2P2-AA_NF_60D":("A2P2_NF_60D","AA_NF_60D"),"A2P2-AA_NF_90D":("A2P2_NF_90D","AA_NF_90D"),"AA_FIN-AA_NF_30D":("AA_FIN_30D","AA_NF_30D"),"AA_FIN-AA_NF_60D":("AA_FIN_60D","AA_NF_60D"),"AA_FIN-AA_NF_90D":("AA_FIN_90D","AA_NF_90D"),"AA_FIN_90D-30D":("AA_FIN_90D","AA_FIN_30D"),"AA_NF_90D-30D":("AA_NF_90D","AA_NF_30D"),"A2P2_NF_90D-30D":("A2P2_NF_90D","A2P2_NF_30D")}
sp=pd.DataFrame(index=rates.index)
for n,(a,b) in pairs.items(): sp[n]=(rates[a]-rates[b])*100
sp=sp.dropna(how="all"); sp.to_csv(DATA/"spreads.csv",index_label="Date")

lr=[]
for c in COLS:
    x=rates[c].dropna(); lr.append({"Series":c,"Date":x.index[-1].date(),"Current":x.iloc[-1],"Start":x.index[0].date(),"Observations":len(x),"Min":x.min(),"Max":x.max()})
pd.DataFrame(lr).to_csv(DATA/"latest_rates.csv",index=False)

ls=[]
for n in pairs:
    q=calc(sp[n].dropna()); q["Spread"]=n; q["Regime"]=regime(q["Z_1Y"]); ls.append(q)
pd.DataFrame(ls)[["Spread","Start","End","Current_bp","Observations","Full_Percentile","Z_Full","AR1_Full","HalfLife_Full_obs","ADF_p","Start_1Y","Obs_1Y","Pct_1Y","Z_1Y","AR1_1Y","HalfLife_1Y_obs","Start_3Y","Obs_3Y","Pct_3Y","Z_3Y","AR1_3Y","HalfLife_3Y_obs","Regime"]].to_csv(DATA/"latest_spreads.csv",index=False)

credit=pd.DataFrame({t:sp[f"A2P2-AA_NF_{t}"] for t in ["30D","60D","90D"]}).ffill(limit=5)
cp=pd.DataFrame(index=credit.index)
for t in ["30D","60D","90D"]:
    x=credit[t]; cp[f"CP_Credit_{t}"]=x
    z1=[];z3=[];ze=[];pct=[];a1=[];h1=[];a3=[];h3=[]
    for dt,val in x.items():
        hist=x.loc[:dt].dropna(); w1=hist[hist.index>=dt-pd.DateOffset(years=1)]; w3=hist[hist.index>=dt-pd.DateOffset(years=3)]
        def zz(w): return (val-w.mean())/w.std() if pd.notna(val) and len(w)>1 and w.std()>0 else np.nan
        p1,p3=ar1(w1),ar1(w3)
        z1.append(zz(w1));z3.append(zz(w3));ze.append(zz(hist));pct.append(float((w1<=val).mean()*100) if pd.notna(val) and len(w1) else np.nan);a1.append(p1);h1.append(half(p1));a3.append(p3);h3.append(half(p3))
    cp[f"CP_{t}_Z_1Y"]=z1;cp[f"CP_{t}_Z_3Y"]=z3;cp[f"CP_{t}_Z_Expanding"]=ze;cp[f"CP_{t}_Pct_1Y"]=pct;cp[f"CP_{t}_Vol_63obs"]=x.rolling(63,min_periods=2).std();cp[f"CP_{t}_AR1_1Y"]=a1;cp[f"CP_{t}_HalfLife_1Y_obs"]=h1;cp[f"CP_{t}_AR1_3Y"]=a3;cp[f"CP_{t}_HalfLife_3Y_obs"]=h3
zcols=[f"CP_{t}_Z_1Y" for t in ["30D","60D","90D"]]
cp["CP_Stress_Composite"]=cp[zcols].mean(axis=1,skipna=True).where(cp[zcols].notna().sum(axis=1)>=2)
cp["CP_Regime"]=cp["CP_Stress_Composite"].map(lambda z:"Extreme Stress" if pd.notna(z) and z>=2 else "Elevated Stress" if pd.notna(z) and z>=1 else "Compressed" if pd.notna(z) and z<=-1 else "Normal" if pd.notna(z) else np.nan)
cp["CP_Credit_90D_minus_30D"]=credit["90D"]-credit["30D"]; cp["CP_Credit_60D_minus_30D"]=credit["60D"]-credit["30D"]
cp.to_csv(DATA/"cp_monitor.csv",index_label="Date")

lcp=[]
for t in ["30D","60D","90D"]:
    x=sp[f"A2P2-AA_NF_{t}"].dropna(); q=calc(x)
    lcp.append({"Maturity":t,"Date":q["End"],"Spread_bp":q["Current_bp"],"Start_1Y":q["Start_1Y"],"Obs_1Y":q["Obs_1Y"],"Z_1Y":q["Z_1Y"],"Pct_1Y":q["Pct_1Y"],"AR1_1Y":q["AR1_1Y"],"HalfLife_1Y_obs":q["HalfLife_1Y_obs"],"Start_3Y":q["Start_3Y"],"Obs_3Y":q["Obs_3Y"],"Z_3Y":q["Z_3Y"],"Pct_3Y":q["Pct_3Y"],"AR1_3Y":q["AR1_3Y"],"HalfLife_3Y_obs":q["HalfLife_3Y_obs"],"Z_Expanding":q["Z_Full"],"Vol_63obs":x.tail(63).std(),"Regime":"Compressed" if q["Z_1Y"]<=-1 else "Elevated" if q["Z_1Y"]>=1 else "Normal"})
pd.DataFrame(lcp).to_csv(DATA/"latest_cp.csv",index=False)

quality=[]
for c in COLS:
    x=rates[c].dropna(); quality.append({"Series":"RATE_"+c,"Start":x.index[0].date(),"End":x.index[-1].date(),"Observations":len(x),"Missing_Total":len(rates)-len(x),"Latest":x.iloc[-1]})
for n in pairs:
    x=sp[n].dropna(); quality.append({"Series":"SPREAD_"+n,"Start":x.index[0].date(),"End":x.index[-1].date(),"Observations":len(x),"Missing_Total":len(rates)-len(x),"Latest":x.iloc[-1]})
pd.DataFrame(quality).to_csv(DATA/"data_quality.csv",index=False)

print("PASS: raw/spreads/latest/CP regenerated")
for c in COLS:
    x=rates[c].dropna(); print(f"{c:16s} {x.index[-1].date()} {x.iloc[-1]:.4f} n={len(x)}")
