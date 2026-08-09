import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { createUserWithEmailAndPassword, onAuthStateChanged, signInWithEmailAndPassword, signInWithPopup, signInWithPhoneNumber, RecaptchaVerifier, sendPasswordResetEmail, signOut as firebaseSignOut, updateProfile, type ConfirmationResult, type User as FirebaseUser } from 'firebase/auth';
import { firebaseAuth, firebaseConfigured, googleProvider } from '../services/firebase';
import { platformApi } from '../services/platformApi';

type SessionUser={uid:string;email?:string|null;displayName?:string|null;provider:string};
type AuthContextValue={user:SessionUser|null;profile:any;loading:boolean;firebaseConfigured:boolean;loginEmail:(email:string,password:string)=>Promise<void>;registerEmail:(name:string,email:string,password:string)=>Promise<void>;loginGoogle:()=>Promise<void>;sendPhoneOtp:(phone:string)=>Promise<void>;verifyPhoneOtp:(code:string)=>Promise<void>;resetPassword:(email:string)=>Promise<void>;demoLogin:()=>Promise<void>;logout:()=>Promise<void>;completeOnboarding:(data:any)=>Promise<void>;refreshProfile:()=>Promise<void>};
const AuthContext=createContext<AuthContextValue|null>(null);
const DEMO_KEY='mihimura_demo_session';
let phoneConfirmation:ConfirmationResult|null=null;
let recaptchaVerifier:RecaptchaVerifier|null=null;

function mapFirebase(u:FirebaseUser):SessionUser{return {uid:u.uid,email:u.email,displayName:u.displayName,provider:u.providerData[0]?.providerId||'firebase'}}

export function AuthProvider({children}:{children:ReactNode}){
 const [user,setUser]=useState<SessionUser|null>(null),[profile,setProfile]=useState<any>(null),[loading,setLoading]=useState(true);
 const refreshProfile=async()=>{try{setProfile(await platformApi.me())}catch{const uid=user?.uid||'demo_farmer_001';const local=localStorage.getItem(`mihimura_profile_${uid}`);setProfile(local?JSON.parse(local):null)}};
 useEffect(()=>{
   if(firebaseAuth&&firebaseConfigured){return onAuthStateChanged(firebaseAuth,async u=>{setUser(u?mapFirebase(u):null);if(u){try{setProfile(await platformApi.me())}catch{setProfile(null)}}else setProfile(null);setLoading(false)})}
   const demo=localStorage.getItem(DEMO_KEY);if(demo){const d=JSON.parse(demo);setUser(d);const p=localStorage.getItem(`mihimura_profile_${d.uid}`);setProfile(p?JSON.parse(p):{uid:d.uid,onboarding_complete:1,name:'Demo Farmer',role:'farmer',language:'English',district:'Ampara'})}setLoading(false);
 },[]);
 const loginEmail=async(email:string,password:string)=>{if(!firebaseAuth)throw new Error('Firebase is not configured. Use Demo Access or add Firebase keys.');await signInWithEmailAndPassword(firebaseAuth,email,password)};
 const registerEmail=async(name:string,email:string,password:string)=>{if(!firebaseAuth)throw new Error('Firebase is not configured. Use Demo Access or add Firebase keys.');const cred=await createUserWithEmailAndPassword(firebaseAuth,email,password);await updateProfile(cred.user,{displayName:name});setUser(mapFirebase(cred.user));setProfile(null)};
 const loginGoogle=async()=>{if(!firebaseAuth)throw new Error('Firebase is not configured. Add Firebase keys to enable Google login.');const cred=await signInWithPopup(firebaseAuth,googleProvider);setUser(mapFirebase(cred.user));try{setProfile(await platformApi.me())}catch{setProfile(null)}};
 const sendPhoneOtp=async(phone:string)=>{if(!firebaseAuth)throw new Error('Firebase is not configured.');try{if(!recaptchaVerifier)recaptchaVerifier=new RecaptchaVerifier(firebaseAuth,'mihimura-recaptcha',{size:'invisible'});phoneConfirmation=await signInWithPhoneNumber(firebaseAuth,phone,recaptchaVerifier)}catch(exc){recaptchaVerifier?.clear();recaptchaVerifier=null;throw exc}};
 const verifyPhoneOtp=async(code:string)=>{if(!phoneConfirmation)throw new Error('Request a verification code first.');await phoneConfirmation.confirm(code);phoneConfirmation=null;recaptchaVerifier?.clear();recaptchaVerifier=null};
 const resetPassword=async(email:string)=>{if(!firebaseAuth)throw new Error('Firebase is not configured.');if(!email)throw new Error('Enter your email address first.');await sendPasswordResetEmail(firebaseAuth,email)};
 const demoLogin=async()=>{const d={uid:'demo_farmer_001',email:'demo@mihimura.lk',displayName:'Demo Farmer',provider:'demo'};localStorage.setItem(DEMO_KEY,JSON.stringify(d));setUser(d);try{setProfile(await platformApi.me())}catch{setProfile({uid:d.uid,onboarding_complete:1,name:'Demo Farmer',role:'farmer',language:'English',district:'Ampara'})}};
 const logout=async()=>{if(firebaseAuth?.currentUser)await firebaseSignOut(firebaseAuth);localStorage.removeItem(DEMO_KEY);setUser(null);setProfile(null)};
 const completeOnboarding=async(data:any)=>{let saved:any;try{saved=await platformApi.saveProfile({...data,onboarding_complete:true})}catch{saved={...data,onboarding_complete:1,uid:user?.uid};localStorage.setItem(`mihimura_profile_${user?.uid}`,JSON.stringify(saved))}setProfile(saved)};
 useEffect(()=>{
   let accessibility:any={};
   try{accessibility=typeof profile?.accessibility_json==='string'?JSON.parse(profile.accessibility_json):(profile?.accessibility_json||{})}catch{accessibility={}}
   document.documentElement.classList.toggle('large-text',Boolean(accessibility.largeText));
   document.documentElement.classList.toggle('high-contrast',Boolean(accessibility.highContrast));
 },[profile]);
 const value=useMemo(()=>({user,profile,loading,firebaseConfigured,loginEmail,registerEmail,loginGoogle,sendPhoneOtp,verifyPhoneOtp,resetPassword,demoLogin,logout,completeOnboarding,refreshProfile}),[user,profile,loading]);
 return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth(){const ctx=useContext(AuthContext);if(!ctx)throw new Error('useAuth must be used inside AuthProvider');return ctx}
