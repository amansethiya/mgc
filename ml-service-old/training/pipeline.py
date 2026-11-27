import argparse,csv,hashlib,json,time
from collections import Counter
from pathlib import Path
import joblib,numpy as np,sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import classification_report,confusion_matrix,accuracy_score,f1_score
from preprocessing.features import CONFIG,GENRES,FEATURE_COUNT,load_audio,extract_features
ROOT=Path(__file__).resolve().parents[1]

def collect(dataset,manifest=None):
    meta={}
    if manifest:
        with open(manifest,newline='',encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                key=row['path'].replace('\\','/')
                if key in meta:raise ValueError(f'Duplicate manifest path: {key}')
                meta[key]=row
    X=[];labels=[];groups=[];tracks=[];skipped=[];seen={};duplicates=[]
    paths=sorted(p for g in GENRES for p in (dataset/g).glob('*') if p.suffix.lower() in ('.wav','.mp3'))
    if not paths:raise ValueError('No audio found. Point --dataset to GTZAN genres_original (contains blues/, classical/, etc.).')
    if manifest and any(p.relative_to(dataset).as_posix() not in meta for p in paths):raise ValueError('Group manifest must cover all discovered audio files.')
    for i,p in enumerate(paths):
        rel=p.relative_to(dataset).as_posix();row=meta.get(rel,{})
        if row.get('exclude','').lower() in ('1','true','yes'):
            skipped.append({'path':rel,'reason':row.get('reason') or 'manifest exclusion'});continue
        group=row.get('group','').strip() if manifest else rel
        if not group:raise ValueError(f'Manifest group cannot be empty: {rel}')
        try:
            y,_,_=load_audio(p);digest=hashlib.sha256(y.tobytes()).hexdigest()
            if digest in seen:duplicates.append({'path':rel,'matches':seen[digest]});continue
            feat=extract_features(y);seen[digest]=rel;X.append(feat);labels.append(p.parent.name);groups.append(group);tracks.append(rel)
        except Exception as e:skipped.append({'path':rel,'reason':str(e)})
        if (i+1)%25==0:print(f'Inspected {i+1}/{len(paths)}',flush=True)
    return np.asarray(X),np.asarray(labels),np.asarray(groups),tracks,{'discovered':len(paths),'class_distribution':dict(Counter(labels)),'skipped':skipped,'exact_duplicates':duplicates,'group_manifest':str(manifest) if manifest else None,'limitations':'Exact decoded excerpt duplicates removed. Near duplicates, artist identity and incorrect labels require a reviewed group/exclusion manifest; without one results are track-disjoint only.'}

def split(y,groups):
    folds=list(StratifiedGroupKFold(n_splits=7,shuffle=True,random_state=42).split(np.zeros(len(y)),y,groups))
    for i,(_,test) in enumerate(folds):
        for j,(_,val) in enumerate(folds):
            if i==j:continue
            train=np.setdiff1d(np.arange(len(y)),np.concatenate([test,val]))
            if all(set(y[z])==set(GENRES) for z in (train,val,test)):
                assert not(set(groups[train])&set(groups[val]) or set(groups[train])&set(groups[test]) or set(groups[val])&set(groups[test]))
                return train,val,test
    raise ValueError('Unable to create group-disjoint splits containing all 10 genres. Inspect manifest and dataset.')

def metrics(model,X,y):
    t=time.perf_counter();pred=model.classes_[np.argmax(model.predict_proba(X),axis=1)];seconds=time.perf_counter()-t;report=classification_report(y,pred,labels=GENRES,output_dict=True,zero_division=0)
    return {'accuracy':float(accuracy_score(y,pred)),'macro_f1':float(f1_score(y,pred,average='macro')),'macro_precision':report['macro avg']['precision'],'macro_recall':report['macro avg']['recall'],'classification_report':report,'confusion_matrix':confusion_matrix(y,pred,labels=GENRES).tolist(),'prediction_ms_per_track':seconds*1000/len(y)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path,default=ROOT/'models'/'genre_model.joblib');p.add_argument('--evaluation',type=Path,default=ROOT/'evaluation');args=p.parse_args();args.evaluation.mkdir(parents=True,exist_ok=True)
    X,y,groups,tracks,audit=collect(args.dataset,args.manifest);(args.evaluation/'dataset_audit.json').write_text(json.dumps(audit,indent=2))
    if any(Counter(y)[g]<7 for g in GENRES):raise ValueError('Need at least seven usable tracks per genre; use the full GTZAN dataset.')
    tr,va,te=split(y,groups)
    with (args.evaluation/'splits.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['path','genre','group','split'])
        for name,ids in [('train',tr),('validation',va),('test',te)]:w.writerows((tracks[i],y[i],groups[i],name) for i in ids)
    candidates={'random_forest':RandomForestClassifier(n_estimators=300,class_weight='balanced',random_state=42,n_jobs=-1),'svm':make_pipeline(StandardScaler(),SVC(C=10,kernel='rbf',probability=True,class_weight='balanced',random_state=42))};results={}
    for name,model in candidates.items():
        start=time.perf_counter();model.fit(X[tr],y[tr]);elapsed=time.perf_counter()-start;results[name]={'training_seconds':elapsed,'validation':metrics(model,X[va],y[va])};print(name,'validation macro F1:',results[name]['validation']['macro_f1'],flush=True)
    winner=max(candidates,key=lambda n:results[n]['validation']['macro_f1'])
    for name,model in candidates.items():results[name]['test']=metrics(model,X[te],y[te])
    version=f'{winner}-v1-{time.strftime("%Y%m%d-%H%M%S",time.gmtime())}';report={'selected_model':winner,'model_version':version,'feature_config':CONFIG,'genres':GENRES,'split_counts':{'train':len(tr),'validation':len(va),'test':len(te)},'group_manifest_used':bool(args.manifest),'results':results}
    args.output.parent.mkdir(parents=True,exist_ok=True);joblib.dump({'model':candidates[winner],'version':version,'config':CONFIG,'feature_count':FEATURE_COUNT,'sklearn_version':sklearn.__version__},args.output);(args.evaluation/'metrics.json').write_text(json.dumps(report,indent=2))
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    for name,result in results.items():
        fig,ax=plt.subplots(figsize=(9,7));sns.heatmap(result['test']['confusion_matrix'],annot=True,fmt='d',cmap='Blues',xticklabels=GENRES,yticklabels=GENRES,ax=ax);ax.set(xlabel='Predicted',ylabel='Actual',title=f'{name}: held-out test');fig.tight_layout();fig.savefig(args.evaluation/f'{name}_confusion.png',dpi=150);plt.close(fig)
    print(f'Selected {winner}; artifact: {args.output}; report: {args.evaluation}',flush=True)
