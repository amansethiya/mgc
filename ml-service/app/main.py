from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import os,logging,joblib,sklearn
from fastapi import FastAPI,UploadFile,File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from preprocessing.features import GENRES,CONFIG,FEATURE_COUNT,InvalidAudio,load_audio,extract_features
ROOT=Path(__file__).resolve().parents[1];MAX=25*1024*1024;log=logging.getLogger(__name__)
class ServiceError(Exception):
    def __init__(self,status,code,message):self.status=status;self.code=code;self.message=message

def load_model(path):
    if not path.is_file():return None
    bundle=joblib.load(path) # Only load trusted artifacts from our own training script.
    if bundle['config']!=CONFIG or bundle['feature_count']!=FEATURE_COUNT or bundle['sklearn_version']!=sklearn.__version__ or set(bundle['model'].classes_)!=set(GENRES):raise ValueError('Model artifact incompatible with this feature pipeline or scikit-learn version.')
    return bundle

def create_app(model_path=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.bundle=None
        try:app.state.bundle=load_model(Path(model_path or os.environ.get('MODEL_PATH',ROOT/'models'/'genre_model.joblib')))
        except Exception:log.exception('Model loading failed. Retrain with this environment.')
        yield
    app=FastAPI(title='Music Genre ML Service',version='1.0.0',lifespan=lifespan)
    def error(status,code,message):return JSONResponse(status_code=status,content={'success':False,'error':{'code':code,'message':message}})
    @app.exception_handler(ServiceError)
    async def service_error(request,exc):return error(exc.status,exc.code,exc.message)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):return error(422,'INVALID_REQUEST','Send a multipart audio file using the field file.')
    @app.exception_handler(HTTPException)
    async def http_error(request,exc):return error(exc.status_code,'HTTP_ERROR',str(exc.detail))
    @app.exception_handler(Exception)
    async def unexpected(request,exc):
        log.error('Inference failure',exc_info=exc);return error(500,'INTERNAL_ERROR','Audio analysis failed.')
    @app.get('/health')
    def health():return {'success':True,'data':{'status':'ok','modelReady':app.state.bundle is not None}}
    @app.get('/api/v1/genres')
    def genres():return {'success':True,'data':GENRES}
    @app.get('/api/v1/model/info')
    def info():
        b=app.state.bundle;return {'success':True,'data':{'ready':b is not None,'modelVersion':b['version'] if b else None,'genres':GENRES,'preprocessing':CONFIG}}
    def infer(path,b):
        try:y,duration,analyzed=load_audio(path);features=extract_features(y)
        except InvalidAudio as e:raise ServiceError(400,'INVALID_AUDIO',str(e)) from e
        probs=b['model'].predict_proba(features.reshape(1,-1))[0];mapping={str(k):float(v) for k,v in zip(b['model'].classes_,probs)};genre=max(mapping,key=mapping.get)
        return {'predictedGenre':genre,'confidenceScore':mapping[genre],'probabilities':mapping,'audioDuration':duration,'analyzedDuration':analyzed,'modelVersion':b['version']}
    @app.post('/api/v1/predict')
    async def predict(file:UploadFile=File(...)):
        try:
            suffix=Path(file.filename or '').suffix.lower()
            if suffix not in ('.wav','.mp3'):raise ServiceError(415,'UNSUPPORTED_FORMAT','Upload a WAV or MP3 file.')
            if file.size is not None and file.size>MAX:raise ServiceError(413,'FILE_TOO_LARGE','Maximum upload size is 25 MB.')
            if app.state.bundle is None:raise ServiceError(503,'MODEL_NOT_READY','Train the GTZAN model and restart the ML service.')
            with TemporaryDirectory() as temp:
                path=Path(temp)/('audio'+suffix);size=0
                with path.open('wb') as out:
                    while chunk:=await file.read(1024*1024):
                        size+=len(chunk)
                        if size>MAX:raise ServiceError(413,'FILE_TOO_LARGE','Maximum upload size is 25 MB.')
                        out.write(chunk)
                result=await run_in_threadpool(infer,path,app.state.bundle)
            return {'success':True,'data':result}
        finally:await file.close()
    return app
app=create_app()
