# 🚀 Deploy to Railway (Step-by-Step Guide)

Get your AI Agent Platform live on the internet in **10 minutes**!

## 📋 What You'll Need

- ✅ Railway account (free): https://railway.app
- ✅ GitHub account (free): https://github.com
- ✅ Your code (already ready in this folder)

---

## Step 1: Push Code to GitHub (2 minutes)

### Option A: Use GitHub Web Interface (Easiest)

1. Go to https://github.com/new
2. Create a new repository named `agentx-platform`
3. **Don't** initialize with README (we already have one)
4. On the next page, click **"uploading an existing file"**
5. Drag and drop these files from your project:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
   - `.gitignore`
   - `README.md`
   - `SUMMARY.md`
   - `.env.example`
   - `static/` folder (with `index.html` and `dashboard.html`)
6. Click **"Commit changes"**

### Option B: Use Git Command Line

```bash
cd /home/user/ai-agent-platform

# Create a new repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/agentx-platform.git
git branch -M main
git push -u origin main
```

---

## Step 2: Deploy to Railway (3 minutes)

1. Go to https://railway.app and sign in with GitHub
2. Click **"New Project"**
3. Click **"Deploy from GitHub repo"**
4. Select your `agentx-platform` repository
5. Railway will automatically detect it's a Python app
6. Click **"Deploy Now"**

**That's it!** Railway will:
- Install Python 3.11
- Install your dependencies from `requirements.txt`
- Run your app using the `Procfile`
- Give you a public URL

---

## Step 3: Configure Environment Variables (2 minutes)

Your app is deployed, but you need to set up environment variables:

1. In Railway dashboard, click on your project
2. Click the **"Variables"** tab
3. Add these variables:

### Required:
```
SECRET_KEY=your-random-secret-key-here
```
Generate a random key: https://generate-secret.vercel.app/32

### Optional (add later when ready):
```
# For smarter AI responses
OPENAI_API_KEY=sk-your-openai-key

# For payments
STRIPE_SECRET_KEY=sk_test_your-stripe-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# For email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

4. Click **"Deploy"** to apply changes

---

## Step 4: Get Your Public URL (1 minute)

1. In Railway dashboard, click **"Settings"** tab
2. Scroll to **"Networking"** section
3. Click **"Generate Domain"**
4. You'll get a URL like: `agentx-platform-production.up.railway.app`

**🎉 Your platform is now LIVE!**

---

## Step 5: Test Your Live Site

1. Visit your Railway URL
2. Sign up for an account
3. Try the chat interview
4. Submit a task
5. Check your dashboard

**Everything should work exactly like the local version!**

---

## 🎯 Post-Deployment Checklist

### Immediate (Day 1)
- [ ] Test signup/login flow
- [ ] Submit test tasks
- [ ] Check dashboard works
- [ ] Verify database persistence

### This Week
- [ ] Set up OpenAI API key (for smarter responses)
- [ ] Configure custom domain (optional)
- [ ] Set up Stripe for payments
- [ ] Configure email notifications
- [ ] Add Google Analytics

### This Month
- [ ] Set up monitoring (Railway has built-in logs)
- [ ] Configure backups
- [ ] Set up error tracking (Sentry)
- [ ] Create marketing materials
- [ ] Start acquiring customers

---

## 🔧 Troubleshooting

### "Application failed to respond"
- Check Railway logs (click on deployment → "View Logs")
- Make sure `Procfile` is correct
- Verify all dependencies are in `requirements.txt`

### Database not persisting
- Railway's free tier uses ephemeral storage
- Add PostgreSQL: Click "New" → "Database" → "PostgreSQL"
- Update `DATABASE_URL` in Railway variables

### Can't access site
- Make sure you generated a domain in Settings
- Check if deployment succeeded (green checkmark)
- Wait 2-3 minutes after deployment

---

## 💰 Railway Pricing

**Free Tier (Hobby Plan):**
- ✅ $5/month credit (usually enough for small apps)
- ✅ 512 MB RAM
- ✅ 1 GB storage
- ✅ Shared CPU

**When you grow:**
- Pro plan: $20/month
- More RAM, CPU, storage
- Custom domains
- Team collaboration

---

## 🌐 Custom Domain (Optional)

Want `agentx.yourdomain.com` instead of Railway's URL?

1. Buy a domain (Namecheap, GoDaddy, Cloudflare)
2. In Railway: Settings → Domains → Add Custom Domain
3. Add DNS records:
   - Type: CNAME
   - Name: agentx (or @)
   - Value: your-railway-url.up.railway.app
4. Wait 5-10 minutes for DNS propagation
5. Railway auto-provisions SSL certificate

---

## 📊 Monitoring Your App

Railway provides:
- **Logs**: Real-time application logs
- **Metrics**: CPU, memory, network usage
- **Deployments**: History of all deployments
- **Alerts**: Get notified of issues

---

## 🔄 Updating Your App

When you make changes:

```bash
cd /home/user/ai-agent-platform
git add .
git commit -m "Description of changes"
git push origin main
```

Railway will **automatically redeploy** within 1-2 minutes!

---

## 🎓 Railway Resources

- Docs: https://docs.railway.app
- Examples: https://railway.app/examples
- Support: https://railway.app/discord
- Status: https://railway.app/status

---

## ✅ Success Checklist

- [ ] Code pushed to GitHub
- [ ] Deployed on Railway
- [ ] Environment variables set
- [ ] Public domain generated
- [ ] Signup/login working
- [ ] Tasks submitting successfully
- [ ] Dashboard displaying data

**🎉 Congratulations! Your AI Agent Platform is live!**

---

## 🚀 Next Steps

1. **Customize** - Update branding, pricing, skills
2. **Market** - Share on social media, Product Hunt
3. **Iterate** - Add features based on user feedback
4. **Scale** - Upgrade Railway plan as you grow
5. **Monetize** - Enable Stripe payments

---

**Need help?** Check Railway's Discord community or the README.md file!
