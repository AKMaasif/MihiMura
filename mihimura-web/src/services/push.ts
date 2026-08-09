import { getMessaging, getToken, isSupported } from 'firebase/messaging';
import { firebaseApp } from './firebase';
import { platformApi } from './platformApi';

export async function enablePushNotifications(){
  if(!firebaseApp) return {enabled:false,reason:'Firebase is not configured'};
  if(!(await isSupported())) return {enabled:false,reason:'Firebase Messaging is not supported in this browser'};
  const vapidKey=import.meta.env.VITE_FIREBASE_VAPID_KEY;
  if(!vapidKey) return {enabled:false,reason:'VITE_FIREBASE_VAPID_KEY is missing'};
  if(!('serviceWorker' in navigator)) return {enabled:false,reason:'Service workers are not supported in this browser'};
  const permission=await Notification.requestPermission();
  if(permission!=='granted') return {enabled:false,reason:`Notification permission: ${permission}`};
  const registration=await navigator.serviceWorker.register('/sw.js');
  const token=await getToken(getMessaging(firebaseApp),{vapidKey,serviceWorkerRegistration:registration});
  if(!token) return {enabled:false,reason:'No FCM registration token was returned'};
  await platformApi.deviceToken(token);
  return {enabled:true,token};
}
