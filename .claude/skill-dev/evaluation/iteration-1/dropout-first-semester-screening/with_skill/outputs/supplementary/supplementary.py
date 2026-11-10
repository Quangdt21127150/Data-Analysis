"""Kiểm tra bổ sung (chỉ dùng train OOF, không chọn mô hình theo test):
1) Công bằng theo tuổi/giới của baseline B1 (số học phần đạt HK1) so với LR -> chênh lệch đến từ dữ liệu hay mô hình
2) Tỷ lệ bỏ học theo nhóm, theo số học phần đạt HK1
3) Recall theo nhóm khi dùng ngưỡng riêng theo nhóm (kịch bản tham khảo)
"""
import pandas as pd, numpy as np, json
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
cfg=json.load(open('../config.json',encoding='utf-8'))
p=pd.read_csv('../output/prepared.csv')
raw=pd.read_csv(cfg['data_path'],sep=';'); raw.columns=[c.strip() for c in raw.columns]
p['Gender']=raw['Gender'].values; p['Age']=raw['Age at enrollment'].values; p['Target']=raw['Target'].values
tr=p[p._split=='train'].reset_index(drop=True)
num=cfg['features']['numeric']; cat=cfg['features']['categorical']
for c in cat: tr[c]=tr[c].astype(str)
pre=ColumnTransformer([('n',Pipeline([('i',SimpleImputer(strategy='median')),('s',StandardScaler())]),num),
                       ('c',Pipeline([('i',SimpleImputer(strategy='most_frequent')),('o',OneHotEncoder(handle_unknown='ignore',min_frequency=10))]),cat)])
m=Pipeline([('p',pre),('m',LogisticRegression(max_iter=2000,class_weight='balanced'))])
y=tr._y.astype(int).values
s_lr=cross_val_predict(m,tr[num+cat],y,cv=StratifiedKFold(5,shuffle=True,random_state=2026),method='predict_proba')[:,1]
s_b1=-tr['Curricular units 1st sem (approved)'].values+1e-6*np.random.default_rng(0).random(len(tr))
def flag(s,rate=0.3): return s>=np.quantile(s,1-rate)
out=[]
tr['age_grp']=np.where(tr.Age<=20,'<=20','>20')
for name,s in [('LR',s_lr),('B1_approved',s_b1)]:
    f=flag(s)
    for g in ['age_grp','Gender']:
        for v,d in tr.assign(f=f).groupby(g):
            out.append(dict(score=name,group=g,level=v,n=len(d),dropout_rate=round(d._y.mean(),3),flag_rate=round(d.f.mean(),3),recall=round(d.f[d._y==1].mean(),3),precision=round(d._y[d.f].mean(),3)))
res=pd.DataFrame(out); print(res.to_string(index=False)); res.to_csv('fairness_baseline_vs_lr_trainoof.csv',index=False)
# Drop-out rate by approved units
tr['approved_bin']=pd.cut(tr['Curricular units 1st sem (approved)'],[-1,0,2,4,6,100],labels=['0','1-2','3-4','5-6','>=7'])
t=tr.groupby('approved_bin',observed=True).agg(n=('_y','size'),dropout_rate=('_y','mean')).round(3); print(t); t.to_csv('dropout_by_approved_units_train.csv')
# enrolled==0 subgroup
z=tr[tr['Curricular units 1st sem (enrolled)']==0]; print('enrolled0',len(z),z._y.mean().round(3))
# Group-specific thresholds (each age group flagged at its own top 30%)
f2=np.zeros(len(tr),bool)
for v,idx in tr.groupby('age_grp').groups.items():
    ss=s_lr[idx]; f2[idx]=ss>=np.quantile(ss,0.7)
r=[]
for v,d in tr.assign(f=f2).groupby('age_grp'):
    r.append(dict(level=v,flag_rate=round(d.f.mean(),3),recall=round(d.f[d._y==1].mean(),3),precision=round(d._y[d.f].mean(),3)))
print('per-group 30% quota',r,'overall recall',round(f2[y==1].mean(),3),'overall flag',round(f2.mean(),3))
pd.DataFrame(r).to_csv('age_quota_scenario_trainoof.csv',index=False)
# Enrolled class among flagged (LR, 30%)
f=flag(s_lr); print(tr[f].Target.value_counts(normalize=True).round(3)); tr[f].Target.value_counts().to_csv('flagged_by_true_status_trainoof.csv')
