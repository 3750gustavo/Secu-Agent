# Railway Deployment Guide for Secu-Agent

Complete guide to deploy Secu-Agent AI Lead Management System on Railway with PostgreSQL data persistence.

## 📋 Prerequisites

- Railway account (free tier available)
- GitHub account with repository access
- ArliAI API key
- Basic understanding of environment variables

## 🚀 Quick Start Deployment

### Step 1: Prepare Your Repository

1. **Ensure all files are committed to GitHub:**
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push
   ```

2. **Verify required files exist:**
   - `railway.json` - Railway configuration
   - `nixpacks.toml` - Build configuration  
   - `requirements.txt` - Python dependencies
   - `main.py` - Application entry point
   - `database.py` - Database configuration
   - `migrate_db.py` - Database migration script

### Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your Secu-Agent repository
5. Railway will automatically detect the configuration

### Step 3: Add PostgreSQL Database

**CRITICAL for data persistence!**

1. In your Railway project, click "New Service"
2. Select "PostgreSQL" from the database options
3. Railway will create a PostgreSQL database
4. **Important:** Railway automatically sets the `DATABASE_URL` environment variable

### Step 4: Configure Environment Variables

In your Railway project's Variables tab, add these variables:

#### Required Variables:

1. **AIRLI_API_KEY**
   - Your ArliAI API key
   - Get this from your local `airli_config.json` file
   - **Never commit this to GitHub!**

2. **AIRLI_BASE_URL**
   - `https://api.arliai.dev/v1`
   - Default ArliAI API endpoint

#### Automatic Variables (set by Railway):

- **DATABASE_URL** - Automatically set when you add PostgreSQL service
- **PORT** - Automatically set by Railway
- **RAILWAY_ENVIRONMENT** - Automatically set by Railway

### Step 5: Deploy

1. Click "Deploy" button in Railway
2. Railway will build and deploy your application
3. Monitor the build logs for any errors
4. Wait for the health check to pass

### Step 6: Verify Deployment

1. Check the deployment logs for "✓ Database migration completed successfully"
2. Visit your Railway URL (provided by Railway)
3. Test the health endpoint: `https://your-app.railway.app/health`
4. Expected response:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "timestamp": "2026-06-01T17:00:00.000Z"
   }
   ```

## 🔧 Configuration Details

### Database Configuration

The system automatically detects the environment:

- **Local Development:** Uses SQLite (`vigil_agent.db`)
- **Railway Production:** Uses PostgreSQL (via `DATABASE_URL`)

No manual configuration needed - the system handles both cases automatically.

### API Configuration

The system supports multiple configuration methods:

1. **Environment Variables (Recommended for Railway):**
   - `AIRLI_API_KEY` - Your API key
   - `AIRLI_BASE_URL` - API endpoint

2. **Config File (Local Development):**
   - `airli_config.json` - Local configuration file
   - **Never commit this file to GitHub!**

Priority: Environment variables > Config file > Defaults

## 📊 Monitoring Your Deployment

### Health Checks

Railway automatically monitors your application via the `/health` endpoint.

### Logs

View real-time logs in Railway dashboard:
- Application startup logs
- Database migration logs
- API request logs
- Error messages

### Metrics

Railway provides:
- CPU usage
- Memory usage
- Request counts
- Response times

## 🛠️ Troubleshooting

### Build Fails

**Issue:** `psycopg2-binary` installation fails

**Solution:** Ensure you're using `psycopg2-binary==2.9.10` or later in `requirements.txt`

### Health Check Fails

**Issue:** Application starts but health check fails

**Solutions:**
1. Check environment variables are set correctly
2. Verify PostgreSQL service is running
3. Check application logs for errors
4. Ensure `DATABASE_URL` is set by Railway

### Database Connection Issues

**Issue:** Cannot connect to PostgreSQL

**Solutions:**
1. Verify PostgreSQL service is added to Railway project
2. Check `DATABASE_URL` environment variable exists
3. Ensure PostgreSQL service is running
4. Check database logs in Railway

### API Key Issues

**Issue:** AI functionality not working

**Solutions:**
1. Verify `AIRLI_API_KEY` is set in Railway Variables
2. Check API key is valid and active
3. Verify `AIRLI_BASE_URL` is correct
4. Check application logs for API errors

## 🔄 Updating Your Deployment

### Automatic Deployments

Railway automatically deploys when you push to GitHub:

```bash
git add .
git commit -m "Update application"
git push
```

### Manual Redeploy

1. Go to Railway project
2. Click "Redeploy" button
3. Monitor deployment logs

## 💾 Data Persistence

### PostgreSQL Database

- **Automatic backups:** Railway provides automatic backups
- **Data persistence:** Data persists across deployments
- **Scaling:** Database scales automatically with your needs

### Local Development

- **SQLite database:** Data stored in `vigil_agent.db`
- **No persistence needed:** Local development doesn't require PostgreSQL

## 🔒 Security Best Practices

### Environment Variables

- ✅ **DO:** Set sensitive data in Railway Variables
- ❌ **DON'T:** Commit API keys to GitHub
- ❌ **DON'T:** Use hardcoded credentials in code

### Database Security

- Railway manages database credentials automatically
- Never expose `DATABASE_URL` in logs or error messages
- Use Railway's built-in security features

### API Security

- Keep API keys in Railway Variables only
- Rotate API keys periodically
- Monitor API usage for unusual activity

## 📈 Scaling

### Railway Free Tier Limits

- **512MB RAM** per service
- **1GB PostgreSQL storage**
- **500 hours** of runtime per month
- **Community support**

### When to Upgrade

Consider upgrading when:
- Consistently hitting memory limits
- Need more storage
- Require dedicated support
- Need higher performance

## 🧪 Testing

### Local Testing

Before deploying to Railway:

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (uses SQLite)
python main.py

# Test health endpoint
curl http://localhost:8000/health
```

### Railway Testing

After deployment:

```bash
# Test health endpoint
curl https://your-app.railway.app/health

# Test API endpoints
curl https://your-app.railway.app/api/info
curl https://your-app.railway.app/leads
```

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app)
- [PostgreSQL on Railway](https://docs.railway.app/guides/postgresql)
- [Environment Variables](https://docs.railway.app/reference/variables)
- [Troubleshooting](https://docs.railway.app/guides/troubleshooting)

## 🆘 Support

### Common Issues

1. **Build failures:** Check requirements.txt versions
2. **Runtime errors:** Review application logs
3. **Database issues:** Verify PostgreSQL service
4. **API issues:** Check environment variables

### Getting Help

- Railway Community: [discord.gg/railway](https://discord.gg/railway)
- Railway Docs: [docs.railway.app](https://docs.railway.app)
- GitHub Issues: Report issues in repository

## ✅ Deployment Checklist

Before deploying, ensure:

- [ ] All code committed to GitHub
- [ ] `railway.json` configuration present
- [ ] `nixpacks.toml` build configuration present
- [ ] `requirements.txt` includes `psycopg2-binary==2.9.10`
- [ ] Environment variables documented
- [ ] PostgreSQL service added to Railway
- [ ] `AIRLI_API_KEY` set in Railway Variables
- [ ] `AIRLI_BASE_URL` set in Railway Variables
- [ ] Health check endpoint configured
- [ ] Database migration script present
- [ ] Local testing completed successfully

## 🎉 Success!

Your Secu-Agent application is now deployed on Railway with:

- ✅ Automatic PostgreSQL database
- ✅ Persistent data storage
- ✅ Secure environment variables
- ✅ Health monitoring
- ✅ Automatic deployments
- ✅ Scalable infrastructure

**Next Steps:**
1. Monitor your deployment logs
2. Set up alerts for issues
3. Configure custom domain (optional)
4. Set up analytics (optional)
5. Enjoy your cloud-hosted AI lead management system!