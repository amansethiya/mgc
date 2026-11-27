import io,joblib,numpy as np,soundfile as sf,sklearn
from sklearn.ensemble import RandomForestClassifier
from fastapi.testclient import TestClient
from app.main import create_app
from preprocessing.features import GENRES,CONFIG,FEATURE_COUNT
from training.pipeline import split

def wav_bytes():
    t=np.arange(22050*6)/22050;y=.25*np.sin(2*np.pi*440*t)+.1*np.sin(2*np.pi*660*t);out=io.BytesIO();sf.write(out,y,22050,format='WAV');return out.getvalue()

def test_untrained_service(tmp_path):
    with TestClient(create_app(tmp_path/'missing.joblib')) as c:
        assert c.get('/health').json()['data']['modelReady'] is False
        assert c.post('/api/v1/predict',files={'file':('x.wav',wav_bytes(),'audio/wav')}).status_code==503
        assert c.post('/api/v1/predict',files={'file':('x.txt',b'x','text/plain')}).status_code==415
        assert c.post('/api/v1/predict').status_code==422

def test_inference_contract(tmp_path):
    # Synthetic estimator tests transport only. Never distributed as a real genre model.
    rng=np.random.default_rng(42);X=rng.normal(size=(30,FEATURE_COUNT));m=RandomForestClassifier(n_estimators=5,random_state=42).fit(X,np.tile(GENRES,3));path=tmp_path/'fixture.joblib';joblib.dump({'model':m,'version':'TEST-ONLY','config':CONFIG,'feature_count':FEATURE_COUNT,'sklearn_version':sklearn.__version__},path)
    with TestClient(create_app(path)) as c:
        r=c.post('/api/v1/predict',files={'file':('x.wav',wav_bytes(),'audio/wav')});assert r.status_code==200,r.text
        d=r.json()['data'];assert set(d['probabilities'])==set(GENRES);assert abs(sum(d['probabilities'].values())-1)<1e-6;assert d['analyzedDuration']==6;assert d['confidenceScore']==max(d['probabilities'].values())
        assert c.post('/api/v1/predict',files={'file':('x.wav',b'not audio','audio/wav')}).status_code==400

def test_group_splits():
    y=np.repeat(GENRES,70);g=np.array([f'{label}-{i//2}' for label in GENRES for i in range(70)])
    a,b,c=split(y,g);assert len(a)+len(b)+len(c)==len(y);assert not set(g[a])&set(g[b]);assert not set(g[a])&set(g[c]);assert not set(g[b])&set(g[c])
