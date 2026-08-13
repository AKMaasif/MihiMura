const CACHE='mihimura-v3-shell-v2';
const SHELL=['/','/index.html','/manifest.webmanifest','/favicon.svg'];

self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));
});

self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});

self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET') return;
  const url=new URL(event.request.url);
  // Never cache API responses, identity-provider requests, or other cross-origin/private data.
  if(url.origin!==self.location.origin) return;
  if(event.request.mode==='navigate'){
    event.respondWith(fetch(event.request).then(response=>{
      const copy=response.clone();caches.open(CACHE).then(cache=>cache.put('/index.html',copy));return response;
    }).catch(()=>caches.match('/index.html')));
    return;
  }
  if(['script','style','image','font','manifest'].includes(event.request.destination)){
    event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request).then(response=>{
      if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));}
      return response;
    })));
  }
});

self.addEventListener('push',event=>{
  let payload={};
  try{payload=event.data?.json?.()||{}}catch{payload={body:event.data?.text?.()||''}}
  const notification=payload.notification||payload;
  const title=notification.title||'MihiMura field alert';
  const options={body:notification.body||'New field guidance is available.',icon:'/favicon.svg',badge:'/favicon.svg',data:payload.data||{url:'/#/app/dashboard'}};
  event.waitUntil(self.registration.showNotification(title,options));
});

self.addEventListener('notificationclick',event=>{
  event.notification.close();
  const target=event.notification.data?.url||'/#/app/dashboard';
  event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(list=>{
    for(const client of list){if('focus'in client){client.navigate(target);return client.focus();}}
    return clients.openWindow(target);
  }));
});
