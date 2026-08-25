# 🤖 AgentX - AI Agent Service Platform

A complete platform where clients can interview, hire, and manage AI agents for various tasks. Features authentication, task management, payment integration, and email notifications.

## ✨ Features

### 🎯 Core Functionality
- **Landing Page** - Professional marketing page showcasing agent capabilities
- **Interactive Chat Interview** - Clients can interview the AI agent in real-time
- **Voice Input** - Browser-based speech recognition for hands-free interaction
- **Task Submission** - Submit tasks across 6 skill categories
- **Dashboard** - Track tasks, view results, and manage account
- **Authentication** - Secure user registration and login with JWT tokens

### 🛠️ Skill Categories
1. **💻 Coding** - Software development, debugging, code review
2. **✍️ Writing** - Blog posts, articles, marketing copy
3. **🔍 Research** - Market research, analysis, reports
4. **📊 Data Processing** - Data cleaning, analysis, visualization
5. **🎧 Customer Support** - Email/chat support, ticket resolution
6. **📁 Admin** - Scheduling, email management, document preparation

### 🔐 Authentication & Authorization
- User registration with email/password
- JWT-based authentication (7-day token expiry)
- Protected routes and API endpoints
- Session management for chat history
- Task limits based on subscription plan

### 💳 Payment Integration (Stripe Ready)
- Three subscription tiers:
  - **Free** - 5 tasks/month
  - **Starter** - 50 tasks/month ($99/mo)
  - **Professional** - 200 tasks/month ($299/mo)
  - **Enterprise** - Unlimited tasks (custom pricing)
- Stripe checkout integration ready
- Webhook support for payment confirmation

### 📧 Email Notifications
- Task completion notifications
- SMTP configuration support
- Customizable email templates

### 🗄️ Database
- SQLite for development (default)
- PostgreSQL ready for production
- Persistent storage for users, tasks, and chat sessions

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd ai-agent-platform
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or install manually:
   ```bash
   pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 sqlalchemy==2.0.23 \
     python-jose[cryptography]==3.3.0 passlib==1.7.4 bcrypt==4.0.1 \
     pydantic[email]==2.5.0 python-multipart==0.0.6 stripe==7.0.0 \
     openai==1.3.0 aiosmtplib==3.0.1
   ```

3. **Configure environment variables (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the server:**
   ```bash
   python app.py
   ```

5. **Open your browser:**
   - Main site: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Dashboard: http://localhost:8000/dashboard

## 📖 Usage Guide

### For Clients

1. **Visit the Landing Page**
   - Browse agent capabilities
   - View pricing plans
   - Read about skill categories

2. **Interview the Agent**
   - Use the chat interface to ask questions
   - Test the agent with sample tasks
   - Try voice input for hands-free interaction

3. **Create an Account**
   - Click "Sign Up" in the navigation
   - Enter your name, email, and password
   - Get 5 free tasks to start

4. **Submit Tasks**
   - Choose a skill category
   - Provide task title and description
   - Add client name and email (optional)
   - Receive results instantly

5. **Track Your Tasks**
   - Login to your dashboard
   - View task history and results
   - Monitor task usage and limits

### For Developers

#### API Endpoints

**Authentication:**
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user profile

**Tasks:**
- `POST /api/submit-task` - Submit a new task (requires auth)
- `GET /api/tasks` - Get user's task history (requires auth)

**Chat:**
- `POST /api/chat` - Send message to agent
- `GET /api/chat/history/{session_id}` - Get chat history

**Other:**
- `GET /api/skills` - Get available skill categories
- `GET /api/profile` - Get agent profile information
- `POST /api/create-checkout-session` - Create Stripe checkout (requires auth)
- `POST /api/stripe-webhook` - Stripe webhook handler

#### Example API Usage

**Sign up:**
```bash
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","password":"securepass123"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"john@example.com","password":"securepass123"}'
```

**Submit task (with auth token):**
```bash
curl -X POST http://localhost:8000/api/submit-task \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "Write blog post",
    "description": "Write a 500-word blog post about AI trends",
    "skill": "writing",
    "client_name": "John Doe",
    "client_email": "john@example.com"
  }'
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# JWT Secret (generate a secure random string)
SECRET_KEY=your-secret-key-here

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./agentx.db
# DATABASE_URL=postgresql://user:pass@localhost/agentx

# Stripe (for payments)
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_PUBLISHABLE_KEY=pk_test_your_key

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# OpenAI (optional, for enhanced AI responses)
OPENAI_API_KEY=sk-your-openai-key
```

### Database Configuration

**SQLite (Development):**
```python
DATABASE_URL = "sqlite:///./agentx.db"
```

**PostgreSQL (Production):**
```python
DATABASE_URL = "postgresql://user:password@localhost/agentx"
```

## 🔧 Customization

### Modify Agent Profile

Edit `app.py` and update the `AGENT_PROFILE` dictionary:

```python
AGENT_PROFILE = {
    "name": "Your Agent Name",
    "tagline": "Your Custom Tagline",
    "description": "Your agent description",
    "skills": [...],  # Customize skills
    "pricing": [...],  # Customize pricing
}
```

### Add New Skills

1. Add skill definition to `AGENT_PROFILE["skills"]`
2. Create engine function in `app.py`:
   ```python
   def your_skill_engine(task: str) -> str:
       # Your logic here
       return "Result"
   ```
3. Register in `execute_skill()` function

### Customize Chat Responses

Edit the `get_agent_response()` function in `app.py` to modify how the agent responds to different types of messages.

## 🚀 Deployment

### Docker Deployment

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t agentx .
docker run -p 8000:8000 --env-file .env agentx
```

### Production Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Configure PostgreSQL database
- [ ] Set up Stripe production keys
- [ ] Configure SMTP for email notifications
- [ ] Enable HTTPS (use reverse proxy like nginx)
- [ ] Set up proper CORS origins
- [ ] Configure rate limiting
- [ ] Set up monitoring and logging
- [ ] Back up database regularly
- [ ] Use environment variables for secrets

### CORS Configuration

Update `app.py` to allow your production domain:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📊 Project Structure

```
ai-agent-platform/
├── app.py                  # Main FastAPI application
├── agentx.db              # SQLite database (auto-created)
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .env.example          # Environment variables template
└── static/
    ├── index.html        # Landing page with chat
    └── dashboard.html    # User dashboard
```

## 🔒 Security Features

- **Password Hashing** - PBKDF2-SHA256 for secure password storage
- **JWT Authentication** - Token-based auth with expiration
- **Input Validation** - Pydantic models validate all inputs
- **SQL Injection Protection** - SQLAlchemy ORM prevents injection
- **CORS Protection** - Configurable CORS policy
- **Rate Limiting** - Ready to implement (add middleware)

## 🧪 Testing

Test the API endpoints:

```bash
# Run the server
python app.py

# In another terminal, test endpoints
curl http://localhost:8000/api/profile
curl http://localhost:8000/api/skills
```

Or use the interactive API docs at http://localhost:8000/docs

## 🤝 Contributing

This is a demo project. Feel free to fork and customize for your needs!

## 📝 License

MIT License - feel free to use this project for any purpose.

## 🆘 Support

For issues or questions:
1. Check the API docs at `/docs`
2. Review the code comments in `app.py`
3. Customize as needed for your use case

## 🎯 Next Steps

Potential enhancements:
- [ ] Add OpenAI integration for smarter responses
- [ ] Implement real-time WebSocket chat
- [ ] Add file upload support
- [ ] Create admin panel for platform management
- [ ] Add analytics and reporting
- [ ] Implement task queuing with Celery
- [ ] Add multi-language support
- [ ] Create mobile app
- [ ] Add team/organization support
- [ ] Implement task templates

---

**Built with FastAPI, SQLAlchemy, and modern web technologies**

🚀 Ready to deploy your AI agent service platform!
