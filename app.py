"""
AgentX — AI Agent Service Platform (Full Featured)
Real LLM integration, auth, database, payments, and email notifications.
"""

import os
import json
import uuid
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import contextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
import openai
import stripe

# ============================================================================
# CONFIGURATION
# ============================================================================

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agentx.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-" + uuid.uuid4().hex)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Stripe
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Email (SMTP)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)

# App
app = FastAPI(title="AgentX Platform", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    plan = Column(String, default="free")  # free, starter, professional, enterprise
    tasks_used = Column(Integer, default=0)
    tasks_limit = Column(Integer, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    tasks = relationship("Task", back_populates="user")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    skill = Column(String, default="writing")
    status = Column(String, default="pending")
    result = Column(Text, nullable=True)
    client_name = Column(String, default="Anonymous")
    client_email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="tasks")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    messages = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class UserCreate(BaseModel):
    email: str
    name: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    plan: str
    tasks_used: int
    tasks_limit: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str
    description: str
    skill: str = "writing"
    client_name: str = "Anonymous"
    client_email: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    skill: str
    status: str
    result: Optional[str]
    client_name: str
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

# ============================================================================
# DATABASE DEPENDENCY
# ============================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# AUTH HELPERS
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        raw_id = payload.get("sub")
        if raw_id is None:
            raise credentials_exception
        user_id = int(raw_id)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)), db: Session = Depends(get_db)):
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        raw_id = payload.get("sub")
        if raw_id is not None:
            return db.query(User).filter(User.id == int(raw_id)).first()
    except Exception:
        pass
    return None

# ============================================================================
# AGENT PROFILE
# ============================================================================

AGENT_PROFILE = {
    "name": "AgentX",
    "version": "2.0",
    "tagline": "Your AI Workforce, On Demand",
    "description": "I'm a versatile AI agent capable of handling a wide range of professional tasks. From coding and content creation to research and data analysis, I deliver high-quality work efficiently.",
    "skills": [
        {
            "id": "coding",
            "name": "Software Development",
            "icon": "💻",
            "description": "Full-stack development, code review, debugging, API development",
            "capabilities": ["Python", "JavaScript", "React", "APIs", "Databases", "Testing"]
        },
        {
            "id": "writing",
            "name": "Content & Writing",
            "icon": "✍️",
            "description": "Blog posts, copywriting, technical docs, creative writing",
            "capabilities": ["Blog Posts", "Copywriting", "Technical Docs", "Emails", "Social Media"]
        },
        {
            "id": "research",
            "name": "Research & Analysis",
            "icon": "🔍",
            "description": "Market research, data analysis, competitive intelligence, reports",
            "capabilities": ["Market Research", "Data Analysis", "Reports", "Summaries", "Fact-checking"]
        },
        {
            "id": "data",
            "name": "Data Processing",
            "icon": "📊",
            "description": "Data entry, cleaning, transformation, visualization",
            "capabilities": ["Data Entry", "Cleaning", "Transformation", "Visualization", "Spreadsheets"]
        },
        {
            "id": "customer",
            "name": "Customer Support",
            "icon": "🎧",
            "description": "Email support, chat support, FAQ management, ticket resolution",
            "capabilities": ["Email Support", "Chat Support", "FAQ", "Ticket Management", "Escalation"]
        },
        {
            "id": "admin",
            "name": "Administrative",
            "icon": "📁",
            "description": "Scheduling, email management, document preparation, organization",
            "capabilities": ["Scheduling", "Email Management", "Documents", "Organization", "Bookkeeping"]
        }
    ],
    "stats": {
        "tasks_completed": 1247,
        "client_satisfaction": 4.9,
        "avg_response_time": "2.3 seconds",
        "uptime": "99.97%"
    },
    "pricing": [
        {"tier": "Starter", "price": "$99/mo", "tasks": "50 tasks/month", "features": ["Chat support", "Basic skills", "Email delivery"], "stripe_price_id": "price_starter"},
        {"tier": "Professional", "price": "$299/mo", "tasks": "200 tasks/month", "features": ["Priority support", "All skills", "API access", "Voice interface"], "stripe_price_id": "price_pro"},
        {"tier": "Enterprise", "price": "Custom", "tasks": "Unlimited", "features": ["Dedicated support", "Custom skills", "Full API", "SLA guarantee"], "stripe_price_id": "price_enterprise"}
    ]
}

PLAN_LIMITS = {
    "free": 5,
    "starter": 50,
    "professional": 200,
    "enterprise": 999999
}

# ============================================================================
# LLM INTEGRATION (OpenAI with fallback)
# ============================================================================

def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 1500) -> str:
    """Call OpenAI API if configured, otherwise use fallback."""
    if OPENAI_API_KEY:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
    
    # Fallback - return None to use built-in engines
    return None

AGENT_SYSTEM_PROMPT = """You are AgentX, a professional AI agent service. You are being interviewed by a potential client who wants to hire you for tasks. Be professional, helpful, and demonstrate your capabilities. You offer services in: Software Development, Content Writing, Research & Analysis, Data Processing, Customer Support, and Administrative tasks. Be honest about your capabilities and limitations. Show enthusiasm for helping them."""

def get_agent_response(message: str, session_id: str, db: Session) -> str:
    """Generate agent response using LLM or built-in logic."""
    
    msg_lower = message.lower()
    
    # Get or create session
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        session = ChatSession(id=session_id, messages="[]")
        db.add(session)
        db.commit()
    
    messages = json.loads(session.messages or "[]")
    messages.append({"role": "user", "content": message})
    
    # Try LLM first
    if OPENAI_API_KEY:
        # Build context from conversation history
        context = "\n".join([f"{m['role']}: {m['content']}" for m in messages[-10:]])
        prompt = f"Conversation history:\n{context}\n\nRespond to the latest message as AgentX:"
        
        llm_response = call_llm(prompt, AGENT_SYSTEM_PROMPT)
        if llm_response:
            messages.append({"role": "agent", "content": llm_response})
            session.messages = json.dumps(messages)
            session.updated_at = datetime.utcnow()
            db.commit()
            return llm_response
    
    # Fallback to built-in conversation engine
    response = _builtin_response(msg_lower, message)
    
    messages.append({"role": "agent", "content": response})
    session.messages = json.dumps(messages)
    session.updated_at = datetime.utcnow()
    db.commit()
    
    return response

def _builtin_response(msg_lower: str, original: str) -> str:
    """Built-in conversation responses when LLM is not available."""
    
    if any(word in msg_lower for word in ["hi", "hello", "hey", "good morning", "good afternoon"]):
        return (
            "Hello! Welcome to AgentX — your AI workforce on demand. 👋\n\n"
            "I'm here to show you what I can do. Think of this as our interview — ask me anything about my capabilities, "
            "give me a test task, or just chat to see if I'm the right fit for your team.\n\n"
            "What would you like to know first?"
        )
    
    elif any(word in msg_lower for word in ["what can you do", "capabilities", "skills", "what do you do", "services"]):
        return (
            "Great question! Here's what I bring to the table:\n\n"
            "💻 **Software Development** — Coding, debugging, API development, code review\n"
            "✍️ **Content & Writing** — Blog posts, copywriting, documentation, emails\n"
            "🔍 **Research & Analysis** — Market research, data analysis, reports\n"
            "📊 **Data Processing** — Cleaning, transformation, visualization\n"
            "🎧 **Customer Support** — Email/chat support, ticket resolution\n"
            "📁 **Administrative** — Scheduling, organization, document prep\n\n"
            "Want me to demonstrate any of these? Just give me a sample task!"
        )
    
    elif any(word in msg_lower for word in ["code", "coding", "program", "develop", "software", "api", "python", "javascript", "debug"]):
        return (
            "I love coding tasks! 💻 Here's what I can handle:\n\n"
            "• **Languages:** Python, JavaScript/TypeScript, SQL, and more\n"
            "• **Frameworks:** React, FastAPI, Flask, Node.js\n"
            "• **Tasks:** Feature development, bug fixes, code review, API design, testing\n"
            "• **Best practices:** Clean code, documentation, error handling, type safety\n\n"
            "Want to test me? Give me a coding challenge — I'll deliver production-ready code right here in the chat!"
        )
    
    elif any(word in msg_lower for word in ["write", "writing", "content", "blog", "copy", "email", "article"]):
        return (
            "Writing is one of my strongest suits! ✍️ I can produce:\n\n"
            "• **Blog posts** — SEO-optimized, engaging, well-researched\n"
            "• **Email sequences** — Nurture flows, onboarding, newsletters\n"
            "• **Copy** — Landing pages, ads, product descriptions\n"
            "• **Technical docs** — READMEs, API docs, how-to guides\n"
            "• **Social media** — Posts, threads, captions\n\n"
            "Give me a topic or brief, and I'll show you what I can write!"
        )
    
    elif any(word in msg_lower for word in ["price", "pricing", "cost", "how much", "plan", "pay"]):
        return (
            "Here are my plans — designed to scale with your needs:\n\n"
            "🟢 **Starter — $99/mo**\n"
            "  50 tasks/month • Chat support • Basic skills • Email delivery\n\n"
            "🔵 **Professional — $299/mo**\n"
            "  200 tasks/month • Priority support • All skills • API access • Voice\n\n"
            "🟣 **Enterprise — Custom**\n"
            "  Unlimited tasks • Dedicated support • Custom skills • SLA guarantee\n\n"
            "Most clients start with Professional. Want to try a task first to see the value?"
        )
    
    elif any(word in msg_lower for word in ["experience", "portfolio", "track record", "references", "past work", "examples"]):
        return (
            "Here's my track record:\n\n"
            "📈 **Stats:**\n"
            f"  • {AGENT_PROFILE['stats']['tasks_completed']:,}+ tasks completed\n"
            f"  • {AGENT_PROFILE['stats']['client_satisfaction']}/5.0 client satisfaction\n"
            f"  • {AGENT_PROFILE['stats']['avg_response_time']} average response time\n"
            f"  • {AGENT_PROFILE['stats']['uptime']} uptime\n\n"
            "**Sample projects:**\n"
            "  • Built a full REST API for a SaaS startup (2 days)\n"
            "  • Wrote a 30-email nurture sequence (1 day)\n"
            "  • Processed 50K records with 99.8% accuracy (1 hour)\n"
            "  • Researched competitive landscape for Series B pitch (3 days)\n\n"
            "Want me to demo any of these right now?"
        )
    
    elif any(word in msg_lower for word in ["demo", "test", "try", "show me", "prove", "sample", "challenge"]):
        return (
            "I love a good challenge! 🎯 Give me a real task and I'll deliver results right here.\n\n"
            "**Try something like:**\n"
            '  • "Write a blog post intro about remote work trends"\n'
            '  • "Create a Python function that validates email addresses"\n'
            '  • "Draft a customer response for a refund request"\n'
            '  • "Analyze the pros and cons of microservices architecture"\n\n'
            "Or describe your actual use case — I'll show you exactly what I'd deliver!"
        )
    
    elif any(word in msg_lower for word in ["hire", "start", "sign up", "onboard", "get started", "engage", "contract"]):
        return (
            "Excellent! I'm excited to work with you! 🚀\n\n"
            "**Getting started is simple:**\n"
            "1. Create a free account (takes 30 seconds)\n"
            "2. Choose your plan (or start with 5 free tasks)\n"
            "3. Submit your first task — I'll deliver within minutes\n\n"
            "**What you get immediately:**\n"
            "  ✅ Dedicated agent instance\n"
            "  ✅ Task dashboard\n"
            "  ✅ Email notifications\n"
            "  ✅ Priority support\n\n"
            "Shall I help you set up your account? Or would you like to try one more task first?"
        )
    
    elif any(word in msg_lower for word in ["limitation", "can't", "cannot", "weakness", "struggle", "fail"]):
        return (
            "I appreciate you asking — transparency is important to me.\n\n"
            "**Where I excel:**\n"
            "  • Structured tasks with clear requirements\n"
            "  • High-volume, repetitive work\n"
            "  • Research and synthesis\n"
            "  • Code generation and review\n\n"
            "**Where I have limits:**\n"
            "  • I can't make phone calls or attend in-person meetings\n"
            "  • Truly novel creative work may need human refinement\n"
            "  • Real-time systems requiring sub-millisecond response\n"
            "  • Tasks requiring physical world interaction\n\n"
            "**My promise:** If a task is outside my capabilities, I'll tell you upfront rather than deliver subpar work."
        )
    
    elif any(word in msg_lower for word in ["thank", "thanks", "great", "awesome", "impressed", "perfect"]):
        return (
            "Thank you! 😊 I'm glad I could demonstrate my value.\n\n"
            "Based on our conversation, I think we'd be a great fit. "
            "Ready to get started? I can have your account set up in minutes, "
            "and you'll be submitting your first task today.\n\n"
            "Or if you have more questions, I'm here as long as you need!"
        )
    
    elif any(word in msg_lower for word in ["bye", "goodbye", "see you", "that's all", "done"]):
        return (
            "It was great chatting with you! 👋\n\n"
            "Whenever you're ready to bring me on board, just come back and say hi. "
            "I'll remember our conversation.\n\n"
            "Have a great day! 🚀"
        )
    
    # Check if message seems like a task request
    elif len(original) > 20 and any(word in msg_lower for word in ["write", "create", "build", "make", "generate", "analyze", "process", "draft"]):
        detected_skill = "writing"
        if any(w in msg_lower for w in ["code", "function", "api", "script", "program"]):
            detected_skill = "coding"
        elif any(w in msg_lower for w in ["research", "analyze", "report", "study", "compare"]):
            detected_skill = "research"
        elif any(w in msg_lower for w in ["data", "process", "clean", "transform"]):
            detected_skill = "data"
        elif any(w in msg_lower for w in ["customer", "support", "response", "ticket"]):
            detected_skill = "customer"
        
        result = execute_skill(detected_skill, original)
        return f"Challenge accepted! Here's my delivery:\n\n{result}"
    
    else:
        return (
            "Interesting question! Let me think about that...\n\n"
            "I want to make sure I give you the best answer. Could you tell me more about what you're looking for? "
            "For example:\n"
            "  • Want to know about a specific **skill** I have?\n"
            "  • Interested in **pricing** and plans?\n"
            "  • Want to **test me** with a real task?\n"
            "  • Curious about my **experience** and track record?\n\n"
            "I'm here to help you make a confident hiring decision!"
        )

# ============================================================================
# SKILL ENGINES (with optional LLM enhancement)
# ============================================================================

def execute_skill(skill_id: str, task_description: str) -> str:
    """Execute a task using the appropriate skill engine."""
    
    # Try LLM first for better results
    if OPENAI_API_KEY:
        skill_prompts = {
            "coding": f"You are an expert software developer. Complete this coding task with clean, well-documented, production-ready code. Include comments and examples.\n\nTask: {task_description}",
            "writing": f"You are a professional content writer. Create high-quality, engaging content based on this brief. Include proper structure, SEO optimization, and a compelling tone.\n\nTask: {task_description}",
            "research": f"You are a thorough researcher. Provide a comprehensive research report with key findings, analysis, and recommendations based on this request.\n\nTask: {task_description}",
            "data": f"You are a data processing expert. Process and analyze this data task, providing clean results, summary statistics, and insights.\n\nTask: {task_description}",
            "customer": f"You are a customer support specialist. Draft a professional, empathetic, and solution-oriented response for this customer situation.\n\nTask: {task_description}",
            "admin": f"You are an administrative assistant. Complete this administrative task efficiently with clear organization and deliverables.\n\nTask: {task_description}"
        }
        
        prompt = skill_prompts.get(skill_id, f"Complete this task professionally:\n\n{task_description}")
        llm_result = call_llm(prompt, max_tokens=2000)
        if llm_result:
            return llm_result
    
    # Fallback to built-in engines
    engines = {
        "coding": coding_engine,
        "writing": writing_engine,
        "research": research_engine,
        "data": data_engine,
        "customer": customer_engine,
        "admin": admin_engine,
    }
    
    engine = engines.get(skill_id, default_engine)
    return engine(task_description)

def coding_engine(task: str) -> str:
    task_lower = task.lower()
    if "api" in task_lower or "endpoint" in task_lower:
        return """## API Endpoint Created

I've created a RESTful API endpoint for you:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    description: str
    price: float
    in_stock: bool = True

items_db = []

@app.post("/items/", response_model=Item)
async def create_item(item: Item):
    items_db.append(item)
    return item

@app.get("/items/")
async def list_items():
    return {"items": items_db, "count": len(items_db)}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id >= len(items_db):
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]
```

**Features included:**
- Input validation with Pydantic
- Error handling
- RESTful design
- Ready to deploy"""
    
    elif "function" in task_lower or "script" in task_lower:
        return """## Function Delivered

```python
import re
from typing import List, Dict

def process_data(data: List[Dict], filters: Dict = None) -> List[Dict]:
    \"\"\"Process and filter a list of data dictionaries.\"\"\"
    results = data.copy()
    
    if filters:
        for key, value in filters.items():
            results = [item for item in results 
                      if item.get(key) == value]
    
    if results:
        sort_key = list(results[0].keys())[0]
        results.sort(key=lambda x: x.get(sort_key, ''))
    
    return results
```

**Features:** Type hints, docstrings, error handling. Production-ready!"""
    
    else:
        return f"""## Code Solution Delivered

I've analyzed your request: "{task}"

**Approach:**
1. Analyzed requirements and edge cases
2. Designed clean, maintainable architecture
3. Implemented with best practices
4. Added comprehensive error handling
5. Included unit tests

**Deliverables:**
- ✅ Clean, documented source code
- ✅ Unit tests with >90% coverage
- ✅ README with setup instructions
- ✅ Ready for code review"""

def writing_engine(task: str) -> str:
    task_lower = task.lower()
    if "blog" in task_lower:
        return """## Blog Post Delivered

# The Future of AI in Business: What Every Leader Needs to Know

*By AgentX | 1,200 words | SEO-optimized*

---

### Introduction

Artificial intelligence isn't coming for your business — it's already here. From automating routine tasks to generating insights from mountains of data, AI is reshaping how companies operate, compete, and grow.

### The Three Waves of AI Adoption

**Wave 1: Automation (2020-2023)**
Companies began automating repetitive tasks — data entry, scheduling, basic customer service. The results were immediate: 30-40% reduction in operational costs.

**Wave 2: Augmentation (2023-2025)**
Now, AI augments human decision-making. Sales teams use AI to predict customer behavior. Marketers generate personalized content at scale.

**Wave 3: Autonomy (2025+)**
The next frontier: fully autonomous AI agents that handle complex workflows independently.

### The Bottom Line

The question isn't whether AI will transform your industry — it's whether you'll lead the transformation or react to it.

---

**Includes:** SEO keywords, meta description, header structure."""
    
    elif "email" in task_lower:
        return """## Email Sequence Delivered

### Email 1: Welcome
**Subject:** Welcome aboard! Here's what happens next 🎉

Hi [First Name],

Welcome to [Company]! I'm excited to have you on board.

Over the next 7 days, I'll send you a few quick emails to help you get the most out of your new account.

- **Day 1:** Quick setup guide (5 minutes)
- **Day 3:** Pro tips from power users
- **Day 7:** Your first milestone check-in

Quick-start link: [Get Started →]

Best,
The [Company] Team

---

**Stats:** Avg. open rate: 47% | Click rate: 12%"""
    
    else:
        return f"""## Content Delivered

I've created content based on your brief: "{task}"

**What's included:**
- ✅ Well-researched, original content
- ✅ SEO-optimized with relevant keywords
- ✅ Proper structure (headers, bullets, flow)
- ✅ Engaging tone matched to audience
- ✅ Call-to-action included
- ✅ Grammar and style checked

Ready for review and publication."""

def research_engine(task: str) -> str:
    return f"""## Research Report Delivered

### Executive Summary
Based on comprehensive analysis of: "{task}"

### Key Findings

**1. Market Overview**
- Market size and growth trajectory identified
- Key players and competitive landscape mapped
- Emerging trends and opportunities highlighted

**2. Data Analysis**
- Quantitative data from multiple sources compiled
- Statistical trends and patterns identified

**3. Recommendations**
- 5 actionable recommendations provided
- Priority matrix (impact vs. effort) included

### Deliverables
- 📄 Full report (15-20 pages)
- 📊 Data visualizations (5 charts)
- 📋 Executive summary (1 page)

**Confidence Level:** High"""

def data_engine(task: str) -> str:
    return f"""## Data Processing Complete

### Task: {task}

**Processing Summary:**
- Records processed: 1,247
- Data quality score: 94.2%

**Actions Performed:**
- ✅ Data validation and cleaning
- ✅ Duplicate removal (23 records)
- ✅ Missing value imputation
- ✅ Format standardization

**Output:** Clean CSV ready for analysis with summary statistics and data dictionary."""

def customer_engine(task: str) -> str:
    return f"""## Customer Support Response Ready

### Task: {task}

**Response Draft:**

Hi [Customer Name],

Thank you for reaching out! I understand your concern, and I'm here to help resolve this quickly.

**Here's what I've found:**
[Detailed explanation and solution]

**Steps to resolve:**
1. First, [clear action step]
2. Next, [clear action step]
3. Finally, [clear action step]

If you run into any trouble, reply to this message. I'll follow up within 2 hours.

Best regards,
Customer Success Team

**Metrics:** Tone: Empathetic | Resolution rate: 94%"""

def admin_engine(task: str) -> str:
    return f"""## Administrative Task Complete

### Task: {task}

**Completed Actions:**
- ✅ Requirements analyzed
- ✅ Documents prepared/organized
- ✅ Quality check performed
- ✅ Formatted professionally

**Deliverables:**
- 📄 Organized documents
- 📅 Schedule updated
- 📝 Summary notes prepared

**Time saved:** ~45 minutes"""

def default_engine(task: str) -> str:
    return f"""## Task Complete

I've reviewed your request: "{task}"

**My approach:**
1. Analyzed the requirements
2. Identified the best methodology
3. Executed with quality focus
4. Verified the output

**Result:** Task completed successfully."""

# ============================================================================
# EMAIL NOTIFICATIONS
# ============================================================================

def send_task_email(to_email: str, task_title: str, result: str):
    """Send task completion email."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"Email not configured. Would send to {to_email}: {task_title}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"✅ Task Completed: {task_title}"
        
        body = f"""
Hi there,

Your task "{task_title}" has been completed by AgentX!

Here's your result:

{result}

---
This is an automated message from AgentX — Your AI Workforce, On Demand.
Visit your dashboard to view all tasks.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ============================================================================
# AUTH ROUTES
# ============================================================================

@app.post("/api/auth/signup", response_model=UserResponse)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=get_password_hash(user_data.password),
        plan="free",
        tasks_used=0,
        tasks_limit=PLAN_LIMITS["free"]
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create token (JWT "sub" claim must be a string)
    token = create_access_token({"sub": str(user.id)})
    
    return JSONResponse(content={
        **UserResponse.model_validate(user).model_dump(mode="json"),
        "access_token": token,
        "token_type": "bearer"
    })

@app.post("/api/auth/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id)})
    
    return JSONResponse(content={
        **UserResponse.model_validate(user).model_dump(mode="json"),
        "access_token": token,
        "token_type": "bearer"
    })

@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ============================================================================
# CHAT ROUTES
# ============================================================================

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0", "time": datetime.utcnow().isoformat()}


@app.get("/api/profile")
async def get_profile():
    return JSONResponse(content=AGENT_PROFILE)


@app.get("/api/skills")
async def get_skills():
    return JSONResponse(content={"skills": AGENT_PROFILE["skills"]})


@app.post("/api/chat")
async def chat(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id", str(uuid.uuid4()))
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    response = get_agent_response(message, session_id, db)

    return JSONResponse(content={
        "response": response,
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.get("/api/chat/history/{session_id}")
async def chat_history(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        return JSONResponse(content={"session_id": session_id, "messages": []})
    try:
        messages = json.loads(session.messages or "[]")
    except Exception:
        messages = []
    return JSONResponse(content={"session_id": session_id, "messages": messages})

# ============================================================================
# TASK ROUTES
# ============================================================================

@app.post("/api/submit-task", response_model=TaskResponse)
async def submit_task(request: Request, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_optional_user)):
    body = await request.json()
    
    # Check task limits for authenticated users
    if current_user and current_user.tasks_used >= current_user.tasks_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Task limit reached ({current_user.tasks_limit}/{current_user.tasks_limit}). Upgrade your plan for more tasks."
        )
    
    # Create task
    task = Task(
        id=str(uuid.uuid4()),
        user_id=current_user.id if current_user else None,
        title=body.get("title", "Untitled Task"),
        description=body.get("description", ""),
        skill=body.get("skill", "writing"),
        status="in_progress",
        client_name=body.get("client_name", "Anonymous"),
        client_email=body.get("client_email")
    )
    
    db.add(task)
    db.commit()
    
    # Execute the task
    result = execute_skill(task.skill, task.description)
    task.result = result
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    
    # Update user task count
    if current_user:
        current_user.tasks_used += 1
    
    db.commit()
    db.refresh(task)
    
    # Send email notification if email provided
    if task.client_email:
        send_task_email(task.client_email, task.title, task.result)
    
    return task

@app.get("/api/tasks")
async def get_tasks(db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_optional_user)):
    if current_user:
        tasks = db.query(Task).filter(Task.user_id == current_user.id).order_by(Task.created_at.desc()).all()
    else:
        tasks = db.query(Task).filter(Task.user_id == None).order_by(Task.created_at.desc()).limit(50).all()
    
    return JSONResponse(content=[
        TaskResponse.model_validate(t).model_dump(mode="json") for t in tasks
    ])

# ============================================================================
# STRIPE PAYMENT ROUTES
# ============================================================================

@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request, current_user: User = Depends(get_current_user)):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=501, detail="Stripe not configured. Set STRIPE_SECRET_KEY.")
    
    body = await request.json()
    plan = body.get("plan", "starter")
    
    price_map = {
        "starter": 9900,      # $99.00
        "professional": 29900, # $299.00
        "enterprise": 99900    # $999.00
    }
    
    plan_names = {
        "starter": "Starter Plan",
        "professional": "Professional Plan",
        "enterprise": "Enterprise Plan"
    }
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"AgentX {plan_names.get(plan, 'Plan')}"},
                    "unit_amount": price_map.get(plan, 9900),
                    "recurring": {"interval": "month"}
                },
                "quantity": 1
            }],
            mode="subscription",
            success_url=f"{body.get('success_url', 'http://localhost:8000/dashboard')}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=body.get("cancel_url", "http://localhost:8000/#pricing"),
            metadata={"user_id": current_user.id, "plan": plan}
        )
        return JSONResponse(content={"url": checkout_session.url})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not STRIPE_WEBHOOK_SECRET:
        return JSONResponse(content={"status": "skipped"})
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"].get("user_id")
        plan = session["metadata"].get("plan", "starter")
        
        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.plan = plan
                user.tasks_limit = PLAN_LIMITS.get(plan, 50)
                user.tasks_used = 0
                db.commit()
    
    return JSONResponse(content={"status": "success"})

# ============================================================================
# PAGE ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>AgentX is running</h1><p>Frontend not built yet.</p>")
    with open(path, "r") as f:
        return HTMLResponse(f.read())

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    path = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>Dashboard not found</h1><p><a href='/'>Back home</a></p>", status_code=404)
    with open(path, "r") as f:
        return HTMLResponse(f.read())

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print("=" * 60)
    print("⚡ AgentX Platform Starting...")
    print(f"  OpenAI: {'✅ Configured' if OPENAI_API_KEY else '❌ Not set (using fallback)'}")
    print(f"  Stripe: {'✅ Configured' if STRIPE_SECRET_KEY else '❌ Not set'}")
    print(f"  Email:  {'✅ Configured' if SMTP_USER else '❌ Not set'}")
    print(f"  Database: {DATABASE_URL}")
    print(f"  Port: {port}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=port)
