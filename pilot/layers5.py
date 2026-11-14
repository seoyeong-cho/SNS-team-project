import json, re, numpy as np, pandas as pd
d=pd.read_csv("SSB-Tax-Database-Aug23.csv",encoding="utf-8-sig").dropna(subset=["jurisdiction"])
d=d[d.level.str.strip()=="National"].replace({"country_code":{"PERU":"PER"}})
C={x["cca3"]:x for x in json.load(open("countries.json"))}
f=d.sort_values("year_imp").groupby("country_code").first(); f=f[f.year_imp>=1990].copy()
f["budget"]=[bool(re.search(r'financ|budget|loi de finances|tax code|code g[ée]n[ée]ral|amend|modif',str(l),re.I)) and str(int(y)) in str(l) for l,y in zip(f.legislation,f.year_imp)]
top={'English','French','Arabic','Spanish','Portuguese'}
ORG={'EU':"AUT BEL BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT NLD POL PRT ROU SVK SVN ESP SWE",
 'ECOWAS':"BEN BFA CPV CIV GMB GHA GIN GNB LBR MLI NER NGA SEN SLE TGO",'SADC':"AGO BWA COM COD SWZ LSO MDG MWI MUS MOZ NAM SYC ZAF TZA ZMB ZWE",
 'EAC':"BDI KEN RWA SSD TZA UGA COD SOM",'COMESA':"BDI COM COD DJI EGY ERI SWZ ETH KEN LBY MDG MWI MUS RWA SYC SOM SDN TUN UGA ZMB ZWE",
 'ECCAS':"CMR CAF TCD COG GNQ GAB AGO BDI COD RWA STP",'GCC':"BHR KWT OMN QAT SAU ARE",'ASEAN':"BRN KHM IDN LAO MYS MMR PHL SGP THA VNM",
 'CARICOM':"ATG BHS BRB BLZ DMA GRD GUY HTI JAM KNA LCA VCT SUR TTO",'SICA':"BLZ CRI SLV GTM HND NIC PAN DOM",'MERCOSUR':"ARG BRA PRY URY BOL",
 'ANDEAN':"BOL COL ECU PER",'PIF':"AUS FJI KIR MHL FSM NRU NZL PLW PNG WSM SLB TON TUV VUT COK NIU PYF NCL",'SAARC':"AFG BGD BTN IND MDV NPL PAK LKA",
 'ARAB':"DZA BHR COM DJI EGY IRQ JOR KWT LBN LBY MRT MAR OMN PSE QAT SAU SOM SDN SYR TUN ARE YEM"}
mem={c:{o for o,s in ORG.items() if c in s.split()} for c in f.index}
layers={'대륙':lambda c:{C[c]['region']}, '소지역':lambda c:{C[c]['subregion'] or C[c]['region']},
 '언어':lambda c:set((C[c].get('languages') or {}).values())&top, '소득':lambda c:{f.loc[c,'income_group']},
 '통화':lambda c:set((C[c].get('currencies') or {}).keys()), '지역기구(임시)':lambda c:mem[c]}
rng=np.random.default_rng(0); R=2000
def run(sub):
    idx=list(sub.index); y=sub.year_imp.values.astype(float); k=len(idx); iu=np.triu(np.ones((k,k),bool),1); out=[]
    for name,fn in layers.items():
        G=[fn(c) for c in idx]; S=np.array([[bool(G[i]&G[j]) for j in range(k)] for i in range(k)])&iu
        Ssym=S|S.T
        gap=lambda yy: np.abs(yy[:,None]-yy[None,:])[S].mean()
        def recent(yy):  # 같은 그룹 나라가 직전 1~3년 안에 도입한 뒤 도입한 비율
            d_=yy[:,None]-yy[None,:]; return ((Ssym&(d_>=1)&(d_<=3)).any(1)).mean()
        g0=gap(y); r0=recent(y); ng=[];nr=[]
        for _ in range(R):
            p=rng.permutation(y); ng.append(gap(p)); nr.append(recent(p))
        ng=np.array(ng); nr=np.array(nr)
        out.append(dict(분야=name, 쌍=int(S.sum()), 연도차=round(g0,1), 가짜=round(ng.mean(),1), p_묶임=round((np.sum(ng<=g0)+1)/(R+1),3),
                        최근3년따라함=round(r0,2), 가짜_따라함=round(nr.mean(),2), p_따라함=round((np.sum(nr>=r0)+1)/(R+1),3)))
    return pd.DataFrame(out)
pd.set_option('display.width',200)
print('[A] 전체 112개국'); print(run(f).to_string(index=False))
print('\n[B] 예산법 연도 46개국 제외 (66개국)'); print(run(f[~f.budget]).to_string(index=False))
