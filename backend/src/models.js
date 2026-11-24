import mongoose from 'mongoose';
import {GENRES} from './validation.js';
const userSchema=new mongoose.Schema({username:{type:String,required:true,minlength:3,maxlength:30},email:{type:String,required:true,unique:true,lowercase:true,trim:true},passwordHash:{type:String,required:true,select:false},role:{type:String,enum:['user'],default:'user'}},{timestamps:true});
const predictionSchema=new mongoose.Schema({userId:{type:mongoose.Schema.Types.ObjectId,ref:'User',required:true},originalFileName:{type:String,required:true},storedFileName:{type:String,required:true,select:false},audioDuration:{type:Number,required:true,min:0},analyzedDuration:{type:Number,required:true,min:0},audioFormat:{type:String,enum:['mp3','wav'],required:true},predictedGenre:{type:String,enum:GENRES,required:true},confidenceScore:{type:Number,min:0,max:1,required:true},probabilities:{type:Map,of:Number,required:true},modelVersion:{type:String,required:true}},{timestamps:true});
predictionSchema.index({userId:1,createdAt:-1});
export const User=mongoose.model('User',userSchema);
export const Prediction=mongoose.model('Prediction',predictionSchema);
