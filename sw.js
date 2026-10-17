const V="mcf-v15";const FILES=["./","index.html","manifest.webmanifest","icon-180.png","icon-512.png","pdf.min.mjs","pdf.worker.min.mjs"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting()));});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==V).map(x=>caches.delete(x)))).then(()=>self.clients.claim()));});
self.addEventListener("fetch",e=>{const q=e.request;if(q.method!=="GET")return;const u=new URL(q.url);if(u.origin!==self.location.origin)return;
  e.respondWith(caches.open(V).then(c=>c.match(q,{ignoreSearch:true}).then(hit=>{const net=fetch(q).then(r=>{if(r&&r.ok)c.put(q,r.clone());return r;}).catch(()=>hit||(q.mode==="navigate"?c.match("index.html"):Response.error()));return hit||net;})));});
