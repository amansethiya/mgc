"""Run from the MGC repository root. Applies narrowly scoped Render deployment edits."""
from pathlib import Path

root = Path.cwd()

def edit(text, old, new):
    if new in text:
        return text
    if text.count(old) != 1:
        raise SystemExit(f'Expected exactly one matching source fragment: {old[:100]!r}. No files written.')
    return text.replace(old, new, 1)

files = {name: root / name for name in ['backend/src/server.js', 'backend/src/app.js', 'ml-service/app/main.py']}
if not all(p.is_file() for p in files.values()):
    raise SystemExit('Run this script from the project root containing backend, frontend and ml-service.')
texts = {n: p.read_text(encoding='utf-8') for n,p in files.items()}
n = 'backend/src/server.js'
s = texts[n]
s = edit(s, "APP_ORIGIN='http://localhost:5173'", "APP_ORIGIN=process.env.RENDER_EXTERNAL_URL||'http://localhost:5173'")
s = edit(s, ".listen(Number(PORT),'127.0.0.1'", ".listen(Number(PORT),'0.0.0.0'")
texts[n] = s
n = 'backend/src/app.js'
s = texts[n]
s = edit(s, "const uploads=fileURLToPath(new URL('../uploads/',import.meta.url));", "const uploads=process.env.UPLOAD_DIR||fileURLToPath(new URL('../uploads/',import.meta.url));\nconst frontendDist=fileURLToPath(new URL('../../frontend/dist/',import.meta.url));")
s = edit(s, "app.use(helmet());", "if(process.env.RENDER==='true')app.set('trust proxy',1);app.use(helmet({contentSecurityPolicy:{directives:{'media-src':[\"'self'\",'blob:'],'img-src':[\"'self'\",'data:','blob:']}}}));")
s = edit(s, "maxContentLength:1024*1024,...options", "maxContentLength:1024*1024,...options,headers:{...options.headers,...(process.env.ML_API_KEY?{'X-ML-API-Key':process.env.ML_API_KEY}:{})}")
old = "app.use((req,res,next)=>next(new ApiError(404,'NOT_FOUND','Endpoint not found.')));"
new = """if(production){
  const index=path.join(frontendDist,'index.html');
  if(!fs.existsSync(index))throw new Error('Frontend build missing. Run npm run build.');
  app.use(express.static(frontendDist,{index:false}));
  app.get(/^(?!\\/api(?:\\/|$)).*$/, (req,res)=>res.sendFile(index));
 }
 """ + old
s = edit(s, old, new)
texts[n] = s
n = 'ml-service/app/main.py'
s = texts[n]
s = edit(s, 'import os,logging,joblib,sklearn', 'import os,logging,joblib,sklearn,hmac')
s = edit(s, "    @app.exception_handler(ServiceError)", """    @app.middleware('http')
    async def protect_inference(request, call_next):
        key = os.environ.get('ML_API_KEY', '')
        if request.url.path.rstrip('/') == '/api/v1/predict':
            if os.environ.get('RENDER') == 'true' and not key:
                return error(503, 'SERVICE_NOT_CONFIGURED', 'Inference key is missing.')
            if key and not hmac.compare_digest(request.headers.get('X-ML-API-Key', '').encode(), key.encode()):
                return error(401, 'UNAUTHORIZED', 'Invalid inference credentials.')
        return await call_next(request)
    @app.exception_handler(ServiceError)""")
texts[n] = s
# Do not modify any file until every expected source fragment has been checked.
for name,p in files.items():
    p.write_text(texts[name], encoding='utf-8')
print('Deployment edits applied. Review git diff, build, test and commit the three source files.')
