# Cloudflare Manager - Pages + D1 Edition

This directory contains the **serverless version** of Cloudflare Manager running on **Cloudflare Pages + D1**. This version provides all the functionality of the original Flask app while offering global performance, zero maintenance, and automatic scaling.

## ⚡ Key Advantages

- **🌍 Global Performance**: Deployed to Cloudflare's global edge network
- **🔒 Built-in Security**: DDoS protection and Web Application Firewall included  
- **📈 Auto Scaling**: Handles traffic spikes automatically
- **💰 Cost Effective**: Pay only for what you use
- **🛠️ Zero Maintenance**: No servers to manage or update

## ✨ Enhanced Features (v2.1)

### 🏠 Modern Dashboard
- **Compact Analytics Overview**: 4 key metric cards at the top (zones, requests, bandwidth, threats)
- **Enhanced Search**: Prominent, left-aligned search with modern styling and animations
- **Improved Layout**: Better spacing, responsive design, optimized for 399+ domains
- **Real-time Updates**: Dashboard refreshes automatically after sync operations

### 🗄️ Database Administration Panel
- **Dual-View Interface**: Toggle between Tables view and Schema view
- **Schema Explorer**: Detailed column specs, data types, constraints, primary keys
- **Table Management**: Row counts, metadata, last updated timestamps
- **Collapsible Stats**: Expandable statistics section for detailed analytics

### 🔐 Authentication & UX
- **Clean Authentication**: Cookie-based sessions with proper logout handling
- **Consistent Navigation**: Aligned logout buttons and responsive navbar
- **Theme Support**: Dark/light mode with persistent user preferences

## 🚀 Quick Deployment

### Step 1: Create D1 Database
```bash
# Install Wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Create D1 database
wrangler d1 create cloudflare-manager-db

# Note the database ID and update wrangler.toml
```

### Step 2: Set up Database Schema
```bash
# Apply the schema
wrangler d1 execute cloudflare-manager-db --file=./schema.sql

# Verify tables were created
wrangler d1 execute cloudflare-manager-db --command="SELECT name FROM sqlite_master WHERE type='table';"
```

### Step 3: Deploy to Pages
```bash
# Option 1: Connect GitHub repo
# 1. Push this directory to GitHub
# 2. Go to Cloudflare Dashboard → Pages
# 3. Connect your repository
# 4. Set build output directory to 'public'

# Option 2: Direct upload
wrangler pages deploy public/ --project-name=cloudflare-manager
```

### Step 4: Configure Environment Variables
In Cloudflare Dashboard → Pages → Your Project → Settings → Environment Variables:
```
CLOUDFLARE_EMAIL=your-email@domain.com
CLOUDFLARE_API_KEY=your-global-api-key
CLOUDFLARE_ACCOUNT_ID=your-account-id
```

### Step 5: Add Cloudflare Access (Optional)
1. Go to Cloudflare Dashboard → Zero Trust → Access → Applications
2. Add Application → Self-hosted
3. Enter your Pages domain (e.g., `cloudflare-manager.pages.dev`)
4. Configure authentication (Google, GitHub, email, etc.)
5. Set access policies

## 📁 Project Structure

```
pages-migration/
├── functions/           # Pages Functions (API routes)
│   └── api/
│       ├── zones.js     # GET /api/zones
│       ├── sync.js      # POST /api/sync, GET /api/sync
│       ├── database.js  # GET /api/database
│       └── zones/
│           └── [id].js  # GET /api/zones/[id]
├── public/              # Static files
│   ├── index.html       # Main dashboard
│   ├── database.html    # Database overview
│   ├── css/
│   │   └── main.css     # Styles (copied from Flask app)
│   └── js/
│       ├── app.js       # Main application logic
│       ├── database.js  # Database overview logic
│       └── theme.js     # Theme management
├── schema.sql           # D1 database schema
├── wrangler.toml        # Wrangler configuration
└── README.md            # This file
```

## 🔄 Data Migration from Flask App

### Option 1: Export from Flask App
Add this temporary route to your Flask app:
```python
@app.route('/export-json')
def export_json():
    conn = db_util.get_database_connection()
    
    # Export zones
    zones_cursor = conn.execute("SELECT * FROM zones")
    zones = [dict(row) for row in zones_cursor.fetchall()]
    
    # Export DNS records
    dns_cursor = conn.execute("SELECT * FROM dns_records")
    dns_records = [dict(row) for row in dns_cursor.fetchall()]
    
    conn.close()
    
    return {
        'zones': zones,
        'dns_records': dns_records
    }
```

### Option 2: Manual Sync
1. Deploy the Pages app
2. Run the sync function to fetch fresh data from Cloudflare API
3. This will populate your D1 database with current data

## 🔧 API Endpoints

The Pages Functions provide the same API as your Flask app:

| Flask Route | Pages Function | Description |
|-------------|----------------|-------------|
| `GET /` | `GET /api/zones` | Get all zones |
| `POST /sync` | `POST /api/sync` | Start sync operation |
| `GET /api/sync/progress` | `GET /api/sync` | Get sync progress |
| `GET /view_db` | `GET /api/database` | Database overview |
| `GET /zone/<id>` | `GET /api/zones/[id]` | Zone details |

## 🎨 Features Included

✅ **All Original Features**:
- Domain listing with analytics
- Real-time sync with progress tracking
- Database overview with statistics
- Dark/light theme support
- Responsive design

✅ **Enhanced for Pages**:
- Serverless deployment (no server management)
- Global CDN (ultra-fast loading)
- Built-in DDoS protection
- Easy authentication with Cloudflare Access
- Automatic scaling

## 🔒 Authentication Options

### Option A: Cloudflare Access (Recommended)
- Professional SSO authentication
- Team access management
- Audit logs
- Multiple auth providers

### Option B: Custom Auth with Pages Functions
Create `functions/_middleware.js`:
```javascript
export async function onRequest(context) {
  const { request, next } = context;
  
  // Add your custom auth logic here
  const authHeader = request.headers.get('Authorization');
  if (!authHeader && !request.url.includes('/login')) {
    return new Response('Unauthorized', { status: 401 });
  }
  
  return next();
}
```

## 🚀 Performance Benefits

| Metric | Flask App | Pages + D1 |
|--------|-----------|-------------|
| **Cold Start** | N/A | ~10ms |
| **Global Latency** | Single region | <50ms worldwide |
| **Scalability** | Manual | Automatic |
| **Maintenance** | Server updates | Zero maintenance |
| **DDoS Protection** | Additional setup | Built-in |

## 🔍 Monitoring

View logs and analytics:
```bash
# View function logs
wrangler pages deployment tail

# View D1 metrics
wrangler d1 info cloudflare-manager-db
```

## 🆘 Troubleshooting

### Common Issues:

1. **Database ID not found**
   - Update `database_id` in `wrangler.toml` after creating D1 database

2. **Environment variables not set**
   - Set them in Cloudflare Dashboard → Pages → Settings → Environment Variables

3. **CORS issues**
   - Pages Functions automatically handle CORS for same-origin requests

4. **Sync not working**
   - Verify Cloudflare API credentials are correct
   - Check function logs for detailed error messages

### Debug Commands:
```bash
# Test local development
wrangler pages dev public/

# View D1 database content
wrangler d1 execute cloudflare-manager-db --command="SELECT COUNT(*) FROM zones;"

# Check function logs
wrangler pages deployment tail --project-name=cloudflare-manager
```

## 🎯 Next Steps

After successful deployment:

1. **Test all functionality** in the Pages app
2. **Configure Cloudflare Access** for authentication
3. **Set up custom domain** (optional)
4. **Run initial sync** to populate D1 database
5. **Decommission Flask app** once verified working

Your Cloudflare Manager is now running on a modern, serverless architecture with global performance and zero maintenance! 🎉