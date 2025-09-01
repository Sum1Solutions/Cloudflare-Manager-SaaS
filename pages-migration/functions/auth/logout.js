// Logout endpoint
export async function onRequestPost(context) {
  const url = new URL(context.request.url);
  
  return new Response(null, {
    status: 302,
    headers: {
      'Location': url.origin,
      'Set-Cookie': 'auth=; HttpOnly; Path=/; Max-Age=0'
    }
  });
}