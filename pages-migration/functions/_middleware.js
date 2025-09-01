// Basic Authentication Middleware for Pages Functions
// This provides a simple username/password auth for local testing
// For production, use Cloudflare Access instead

export async function onRequest(context) {
  const { request, next, env } = context;
  
  // Skip auth for static assets
  const url = new URL(request.url);
  if (url.pathname.includes('.') && !url.pathname.includes('/api/')) {
    return next();
  }
  
  // Check if this is a login attempt
  if (request.method === 'POST' && url.pathname === '/auth/login') {
    const formData = await request.formData();
    const username = formData.get('username');
    const password = formData.get('password');
    
    // Secure credential check using environment variables
    const validUsername = env.AUTH_USERNAME || 'admin';
    const validPassword = env.AUTH_PASSWORD || 'CHANGE_THIS_PASSWORD_IMMEDIATELY';
    
    if (username === validUsername && password === validPassword) {
      // Set a session cookie
      return new Response(null, {
        status: 302,
        headers: {
          'Location': url.origin,
          'Set-Cookie': 'auth=authenticated; HttpOnly; Path=/; Max-Age=86400'
        }
      });
    } else {
      return new Response('Invalid credentials', { status: 401 });
    }
  }
  
  // Check for authentication
  const cookies = request.headers.get('Cookie') || '';
  const isAuthenticated = cookies.includes('auth=authenticated');
  
  // Allow API calls from authenticated pages (they include the cookie)
  // If not authenticated and not on login page, show login
  if (!isAuthenticated && url.pathname !== '/login.html') {
    return new Response(`
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloudflare Manager - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .login-container { min-height: 100vh; display: flex; align-items: center; }
        .login-card { backdrop-filter: blur(10px); background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); }
    </style>
</head>
<body>
    <div class="container login-container">
        <div class="row justify-content-center w-100">
            <div class="col-md-4">
                <div class="card login-card">
                    <div class="card-body p-5">
                        <div class="text-center mb-4">
                            <h2 class="text-white"><i class="fas fa-cloud"></i> Cloudflare Manager</h2>
                            <p class="text-white-50">Sign in to continue</p>
                        </div>
                        <form method="POST" action="/auth/login">
                            <div class="mb-3">
                                <input type="text" class="form-control" name="username" placeholder="Username" required>
                            </div>
                            <div class="mb-4">
                                <input type="password" class="form-control" name="password" placeholder="Password" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Sign In</button>
                        </form>
                        <div class="text-center mt-4">
                            <small class="text-white-50">Default: admin / cloudflare123</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/js/all.min.js"></script>
</body>
</html>
    `, {
      status: 401,
      headers: { 'Content-Type': 'text/html' }
    });
  }
  
  return next();
}