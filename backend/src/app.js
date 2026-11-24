import express from 'express';
import helmet from 'helmet';
import cookieParser from 'cookie-parser';
import rateLimit from 'express-rate-limit';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import mongoose from 'mongoose';
import multer from 'multer';
import axios from 'axios';
import FormData from 'form-data';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {randomUUID} from 'node:crypto';
import {User,Prediction} from './models.js';
import {ApiError,credentials,validatePrediction} from './validation.js';
const uploads=fileURLToPath(new URL('../uploads/',import.meta.url));
const MAX=25*1024*1024;
const publicUser=u=>({id:u.id,username:u.username,email:u.email,role:u.role});
const ok=(res,data,status=200)=>res.status(status).json({success:true,data});
const cleanFile=async name=>{if(name)await fsp.unlink(path.join(uploads,name)).catch(e=>{if(e.code!=='ENOENT')console.error('Upload cleanup failed:',e.code);});};
export function createApp({jwtSecret,mlUrl,origin,production=false}){
 const app=express();fs.mkdirSync(uploads,{recursive:true});app.disable('x-powered-by');app.use(helmet());app.use(express.json({limit:'32kb'}));app.use(cookieParser());
 app.use((req,res,next)=>{if(!['GET','HEAD','OPTIONS'].includes(req.method)&&req.get('origin')&&req.get('origin')!==origin)return next(new ApiError(403,'ORIGIN_DENIED','Request origin not allowed.'));next();});
 const cookie={httpOnly:true,secure:production,sameSite:'lax',path:'/'};
 const session=(res,u)=>res.cookie('genre_session',jwt.sign({sub:u.id},jwtSecret,{algorithm:'HS256',expiresIn:'1d'}),{...cookie,maxAge:86400000});
 async function auth(req,res,next){let id;try{id=jwt.verify(req.cookies.genre_session||'',jwtSecret,{algorithms:['HS256']}).sub;}catch{throw new ApiError(401,'UNAUTHORIZED','Please sign in.');}if(!mongoose.isValidObjectId(id))throw new ApiError(401,'UNAUTHORIZED','Please sign in.');req.user=await User.findById(id);if(!req.user)throw new ApiError(401,'UNAUTHORIZED','Please sign in.');next();}
 const authLimit=rateLimit({windowMs:15*60*1000,limit:35,standardHeaders:'draft-8',legacyHeaders:false,handler:(req,res,next)=>next(new ApiError(429,'RATE_LIMIT','Too many attempts. Try again later.'))});
 const uploadLimit=rateLimit({windowMs:60*1000,limit:8,standardHeaders:'draft-8',legacyHeaders:false,keyGenerator:req=>req.user.id,handler:(req,res,next)=>next(new ApiError(429,'RATE_LIMIT','Too many uploads. Try again later.'))});
 const upload=multer({storage:multer.diskStorage({destination:uploads,filename:(req,file,cb)=>cb(null,randomUUID()+path.extname(file.originalname).toLowerCase())}),limits:{fileSize:MAX,files:1,fields:0},fileFilter:(req,file,cb)=>['.mp3','.wav'].includes(path.extname(file.originalname).toLowerCase())?cb(null,true):cb(new ApiError(415,'UNSUPPORTED_FORMAT','Upload an MP3 or WAV file.'))}).single('file');
 async function mlRequest(method,endpoint,options={}){try{const r=await axios({method,url:`${mlUrl}${endpoint}`,timeout:120000,maxBodyLength:MAX+65536,maxContentLength:1024*1024,...options});return r.data;}catch(e){const s=e.response?.status;const err=e.response?.data?.error;if([400,413,415,422,503].includes(s))throw new ApiError(s,err?.code||'ML_ERROR',err?.message||'Audio processing unavailable.');throw new ApiError(502,'ML_UNAVAILABLE','ML service could not complete the request. Check that FastAPI is running.');}}
 async function owned(req,withFile=false){if(!mongoose.isValidObjectId(req.params.id))throw new ApiError(404,'NOT_FOUND','Prediction not found.');const query=Prediction.findOne({_id:req.params.id,userId:req.user.id});if(withFile)query.select('+storedFileName');const p=await query;if(!p)throw new ApiError(404,'NOT_FOUND','Prediction not found.');return p;}
 app.get('/api/v1/health',(req,res)=>ok(res,{database:mongoose.connection.readyState===1?'connected':'disconnected'}));
 app.get('/api/v1/model/info',async(req,res)=>{const result=await mlRequest('get','/api/v1/model/info');ok(res,result.data);});
 app.post('/api/v1/auth/register',authLimit,async(req,res)=>{const {username,email,password}=credentials(req.body,true);const u=await User.create({username,email,passwordHash:await bcrypt.hash(password,12)});session(res,u);ok(res,publicUser(u),201);});
 app.post('/api/v1/auth/login',authLimit,async(req,res)=>{const {email,password}=credentials(req.body);const u=await User.findOne({email}).select('+passwordHash');if(!u||!await bcrypt.compare(password,u.passwordHash))throw new ApiError(401,'INVALID_CREDENTIALS','Invalid email or password.');session(res,u);ok(res,publicUser(u));});
 app.post('/api/v1/auth/logout',(req,res)=>{res.clearCookie('genre_session',cookie);ok(res,{loggedOut:true});});
 app.get('/api/v1/auth/me',auth,(req,res)=>ok(res,publicUser(req.user)));
 app.post('/api/v1/predictions',auth,uploadLimit,upload,async(req,res)=>{if(!req.file)throw new ApiError(400,'FILE_REQUIRED','Select an audio file.');let saved=false;try{const form=new FormData();form.append('file',fs.createReadStream(req.file.path),{filename:req.file.filename,knownLength:req.file.size});const result=await mlRequest('post','/api/v1/predict',{data:form,headers:form.getHeaders()});const fields=validatePrediction(result.data);const p=await Prediction.create({userId:req.user.id,originalFileName:path.basename(req.file.originalname).slice(0,255),storedFileName:req.file.filename,audioFormat:path.extname(req.file.filename).slice(1),...fields});saved=true;const obj=p.toObject({flattenMaps:true});delete obj.storedFileName;ok(res,obj,201);}finally{if(!saved)await cleanFile(req.file.filename);}});
 app.get('/api/v1/predictions',auth,async(req,res)=>{const page=Math.max(1,Math.min(10000,parseInt(req.query.page,10)||1));const limit=20;const filter={userId:req.user.id};const [items,total]=await Promise.all([Prediction.find(filter).sort({createdAt:-1,_id:-1}).skip((page-1)*limit).limit(limit).lean(),Prediction.countDocuments(filter)]);ok(res,{items,total,page,limit});});
 app.get('/api/v1/predictions/:id',auth,async(req,res)=>ok(res,await owned(req)));
 app.get('/api/v1/predictions/:id/audio',auth,async(req,res,next)=>{const p=await owned(req,true);res.set('Cache-Control','private, no-store');res.type(p.audioFormat==='mp3'?'audio/mpeg':'audio/wav');res.sendFile(p.storedFileName,{root:uploads},err=>{if(err)next(new ApiError(404,'AUDIO_MISSING','Audio is no longer available.'));});});
 app.delete('/api/v1/predictions/:id',auth,async(req,res)=>{const p=await owned(req,true);await Prediction.deleteOne({_id:p.id,userId:req.user.id});await cleanFile(p.storedFileName);ok(res,{deleted:true});});
 app.get('/api/v1/dashboard/stats',auth,async(req,res)=>{const userId=req.user._id;const [distribution,summary,recent]=await Promise.all([Prediction.aggregate([{$match:{userId}},{$group:{_id:'$predictedGenre',count:{$sum:1}}},{$sort:{count:-1,_id:1}}]),Prediction.aggregate([{$match:{userId}},{$group:{_id:null,total:{$sum:1},averageConfidence:{$avg:'$confidenceScore'}}}]),Prediction.find({userId}).sort({createdAt:-1}).limit(5).lean()]);ok(res,{total:summary[0]?.total||0,averageConfidence:summary[0]?.averageConfidence??null,mostFrequentGenre:distribution[0]?._id||null,distribution:distribution.map(x=>({genre:x._id,count:x.count})),recent});});
 app.use((req,res,next)=>next(new ApiError(404,'NOT_FOUND','Endpoint not found.')));
 app.use((err,req,res,next)=>{if(res.headersSent)return next(err);if(err instanceof multer.MulterError)err=new ApiError(err.code==='LIMIT_FILE_SIZE'?413:400,err.code,err.code==='LIMIT_FILE_SIZE'?'Maximum upload size is 25 MB.':'Invalid upload request.');if(err.code===11000)err=new ApiError(409,'EMAIL_EXISTS','Email is already registered.');if(err.type==='entity.parse.failed')err=new ApiError(400,'INVALID_JSON','Malformed JSON.');if(err.type==='entity.too.large')err=new ApiError(413,'BODY_TOO_LARGE','Request too large.');if(!(err instanceof ApiError))console.error(err.message);res.status(err instanceof ApiError?err.status:500).json({success:false,error:{code:err instanceof ApiError?err.code:'INTERNAL_ERROR',message:err instanceof ApiError?err.message:'Unexpected server error.'}});});return app;
}
