/** Fixed-origin HTTPS entry point for versionbridge.pages.dev. */
const ORIGIN='https://versionbridge.64.177.53.254.sslip.io';
export default {
  async fetch(request) {
    const incoming=new URL(request.url);
    const upstream=new URL(ORIGIN);
    upstream.pathname=incoming.pathname;
    upstream.search=incoming.search;
    const forward=new Request(upstream,request);
    forward.headers.set('Host',upstream.host);
    forward.headers.set('X-Forwarded-Host',incoming.host);
    forward.headers.set('X-Forwarded-Proto','https');
    try {
      const result=await fetch(forward,{redirect:'manual'});
      const response=new Response(result.body,result);
      const location=response.headers.get('Location');
      if(location?.startsWith(ORIGIN)) response.headers.set('Location',location.replace(ORIGIN,incoming.origin));
      if(incoming.pathname.startsWith('/api/') || incoming.pathname.endsWith('.html') || incoming.pathname==='/') response.headers.set('Cache-Control','no-store');
      response.headers.set('X-Content-Type-Options','nosniff');
      return response;
    } catch(error) {
      console.error('VersionBridge origin unavailable:',error.message);
      return new Response('VersionBridge is temporarily unavailable. Please retry shortly.',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8','Cache-Control':'no-store'}});
    }
  }
};
