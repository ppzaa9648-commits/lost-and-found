from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from database import get_supabase
from models import UserRegister, UserLogin, PostCreate, PostUpdate, MessageCreate
import uuid
import os
import httpx
import urllib.parse
import boto3
from botocore.config import Config
from fastapi.responses import RedirectResponse
from linebot import LineBotApi
from linebot.models import TextSendMessage, ImageSendMessage, FlexSendMessage

# -------------------------------------------------
# Helper: ensure user metadata exists (called after login/registration)
# -------------------------------------------------
def _ensure_user_metadata(user_id: str, defaults: dict):
    """Create or merge default fields into a user's metadata.
    Uses the Supabase service key (admin API)."""
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key.upper() in ("YOUR_SUPABASE_SERVICE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY"):
        raise HTTPException(status_code=503, detail="Service key not configured")
    from supabase import create_client
    supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)

    # fetch current metadata (may be None)
    cur = supabase_admin.auth.admin.get_user_by_id(user_id).execute()
    cur_meta = cur.user.user_metadata or {}
    new_meta = {**cur_meta, **defaults}
    supabase_admin.auth.admin.update_user_by_id(user_id, {"user_metadata": new_meta})

# -------------------------------------------------
# Helper: safe user token authentication
# -------------------------------------------------
def _get_user_from_token(token: str):
    supabase = get_supabase()
    try:
        user_resp = supabase.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(status_code=401, detail="Unauthorized: User not found")
        return user_resp.user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: Token invalid or expired")

# -------------------------------------------------
# Helper: require admin (admin OR super admin)
# -------------------------------------------------
def _require_admin(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth_header.split(" ")[1]
    user = _get_user_from_token(token)
    meta = user.user_metadata or {}
    if not (meta.get("is_admin") or meta.get("is_super_admin")):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user.id

# -------------------------------------------------
# Helper: require super admin (only the top owner)
# -------------------------------------------------
def _require_super_admin(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth_header.split(" ")[1]
    user = _get_user_from_token(token)
    meta = user.user_metadata or {}
    if not meta.get("is_super_admin"):
        raise HTTPException(status_code=403, detail="Super admin required")
    return user.id

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CLIENT_ID = os.getenv("LINE_CLIENT_ID", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CALLBACK_URL = os.getenv("LINE_CALLBACK_URL", "http://127.0.0.1:8000/auth/callback/line")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5500/frontend").rstrip("/")

line_bot_api = None
if LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_ACCESS_TOKEN != "YOUR_LINE_CHANNEL_ACCESS_TOKEN":
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)

# --- CLOUDFLARE R2 SETUP ---
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

r2_client = None
if all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]) and R2_ACCOUNT_ID != "YOUR_CLOUDFLARE_ACCOUNT_ID":
    r2_client = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto"
    )

app = FastAPI(title="Lost and Found API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Lost and Found API is running with Supabase"}

# --- AUTH ---
@app.get("/auth/login/line")
def login_line():
    if not LINE_CLIENT_ID or LINE_CLIENT_ID == "YOUR_LINE_CLIENT_ID":
        raise HTTPException(status_code=400, detail="LINE_CLIENT_ID is not configured in .env")
        
    line_auth_url = "https://access.line.me/oauth2/v2.1/authorize"
    params = {
        "response_type": "code",
        "client_id": LINE_CLIENT_ID,
        "redirect_uri": LINE_CALLBACK_URL,
        "state": "random_state_string",
        "scope": "profile openid email"
    }
    url = f"{line_auth_url}?{urllib.parse.urlencode(params)}"
    return {"url": url}

@app.get("/auth/callback/line")
async def callback_line(code: str, state: str = None):
    token_url = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINE_CALLBACK_URL,
        "client_id": LINE_CLIENT_ID,
        "client_secret": LINE_CHANNEL_SECRET
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, headers=headers, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to get LINE token: {resp.text}")
        token_data = resp.json()
        access_token = token_data.get("access_token")
        
        profile_url = "https://api.line.me/v2/profile"
        profile_headers = {"Authorization": f"Bearer {access_token}"}
        profile_resp = await client.get(profile_url, headers=profile_headers)
        if profile_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get LINE profile")
        profile = profile_resp.json()
        
        user_id = profile.get("userId")
        display_name = profile.get("displayName")
        picture_url = profile.get("pictureUrl", "")
        
        supabase = get_supabase()
        email = f"{user_id}@line.lostandfound.com"
        password = f"secret_{user_id}_password!"
        
        try:
            # Try to sign in first
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        except Exception:
            # If sign in fails, use admin API if service key exists to bypass rate limits, otherwise normal signup
            service_key = os.getenv("SUPABASE_SERVICE_KEY")
            if service_key and service_key.upper() not in ("YOUR_SUPABASE_SERVICE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY"):
                from supabase import create_client
                supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
                try:
                    supabase_admin.auth.admin.create_user({
                        "email": email,
                        "password": password,
                        "email_confirm": True,
                        "user_metadata": {
                            "full_name": display_name,
                            "avatar_url": picture_url,
                            "line_user_id": user_id
                        }
                    })
                    # Now sign in normally
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Admin create user failed: {str(e)}")
            else:
                try:
                    res = supabase.auth.sign_up({
                        "email": email, 
                        "password": password, 
                        "options": {"data": {"full_name": display_name, "avatar_url": picture_url}}
                    })
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to create user (Rate Limit?): {str(e)}")
                
        if not res.session:
            raise HTTPException(status_code=400, detail="Failed to create session")
            
        supabase_token = res.session.access_token
        
        # --- NEW: Ensure metadata exists for the user ---
        try:
            # We set defaults if they don't exist. This won't overwrite is_admin/is_super_admin if already set.
            _ensure_user_metadata(res.user.id, {
                "is_admin": False,
                "is_super_admin": False,
                "is_banned": False,
                "full_name": display_name,
                "avatar_url": picture_url
            })
        except Exception as e:
            print(f"Metadata sync error: {e}")

        frontend_url = f"{FRONTEND_BASE_URL}/index.html#access_token={supabase_token}"
        return RedirectResponse(url=frontend_url)

@app.post("/auth/register")
def register(user: UserRegister):
    supabase = get_supabase()
    try:
        res = supabase.auth.sign_up({
            "email": user.email, 
            "password": user.password,
            "options": {
                "data": {
                    "full_name": user.full_name,
                    "phone": user.phone
                }
            }
        })
        
        if res.user:
            try:
                _ensure_user_metadata(res.user.id, {
                    "is_admin": False,
                    "is_super_admin": False,
                    "is_banned": False,
                    "full_name": user.full_name
                })
            except Exception as e:
                print(f"Metadata sync error: {e}")

        token = res.session.access_token if res.session else None
        return {"message": "Registration successful", "token": token, "data": {"id": res.user.id if res.user else None}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
def login(user: UserLogin):
    supabase = get_supabase()
    try:
        res = supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
        if not res.session:
            raise HTTPException(status_code=400, detail="Invalid credentials")
        return {"token": res.session.access_token, "message": "Login successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- USERS ---
@app.get("/users/me")
def get_me(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = auth_header.split(" ")[1]
    supabase = get_supabase()
    
    try:
        user_resp = supabase.auth.get_user(token)
        user = user_resp.user
        if not user:
             raise HTTPException(status_code=401, detail="Unauthorized")
        
        metadata = user.user_metadata or {}
        return {
            "id": user.id, 
            "email": user.email, 
            "full_name": metadata.get("full_name") or metadata.get("name") or "ผู้ใช้งาน",
            "avatar_url": metadata.get("avatar_url") or "",
            "line_social_id": metadata.get("line_social_id") or "",
            "is_admin": metadata.get("is_admin", False),
            "is_super_admin": metadata.get("is_super_admin", False)
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/users/me/line-id")
def set_line_social_id(request: Request, body: dict):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth_header.split(" ")[1]
    
    line_social_id = body.get("line_social_id", "").strip().replace("@", "")
    if not line_social_id:
        raise HTTPException(status_code=400, detail="LINE ID is required")
    
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key.upper() in ("YOUR_SUPABASE_SERVICE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY"):
        raise HTTPException(status_code=503, detail="Service key not configured")
    
    try:
        supabase = get_supabase()
        user_resp = supabase.auth.get_user(token)
        if not user_resp.user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        from supabase import create_client
        supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
        supabase_admin.auth.admin.update_user_by_id(
            user_resp.user.id,
            {"user_metadata": {"line_social_id": line_social_id}}
        )
        return {"message": "LINE ID saved", "line_social_id": line_social_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/{user_id}")
def get_user_by_id(user_id: str):
    """Public endpoint to get user profile by ID (for post detail page)"""
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key.upper() in ("YOUR_SUPABASE_SERVICE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY"):
        raise HTTPException(status_code=503, detail="Service key not configured")
    
    try:
        from supabase import create_client
        supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
        user_resp = supabase_admin.auth.admin.get_user_by_id(user_id)
        user = user_resp.user
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        metadata = user.user_metadata or {}
        return {
            "id": user.id,
            "full_name": metadata.get("full_name") or metadata.get("name") or "ผู้ใช้งาน",
            "avatar_url": metadata.get("avatar_url") or "",
            "line_user_id": metadata.get("line_user_id") or "",
            "line_social_id": metadata.get("line_social_id") or ""
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")

# --- POSTS ---
@app.get("/posts")
def get_posts(type: str = None, category: str = None, search: str = None, user_id: str = None):
    supabase = get_supabase()
    query = supabase.table("posts").select("*").order("created_at", desc=True)
    
    if type:
        query = query.eq("type", type)
    if category:
        query = query.eq("category", category)
    if user_id:
        query = query.eq("user_id", user_id)
    if search:
        # Simple search in title or description
        query = query.or_(f"title.ilike.%{search}%,description.ilike.%{search}%")
    try:
        response = query.execute()
        posts = response.data
        
        service_key = os.getenv("SUPABASE_SERVICE_KEY")
        if service_key and service_key.upper() not in ("YOUR_SUPABASE_SERVICE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY"):
            from supabase import create_client
            supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
            try:
                users = supabase_admin.auth.admin.list_users()
                user_map = {}
                for u in users:
                    meta = u.user_metadata or {}
                    user_map[u.id] = meta.get("full_name") or meta.get("name") or "ผู้ใช้งาน"
                
                for p in posts:
                    p["author_name"] = user_map.get(p.get("user_id"), "ผู้ใช้งาน")
            except Exception as e:
                print(f"Failed to fetch users: {e}")

        return {"data": posts, "message": "List of posts"}
    except Exception as e:
        return {"data": [], "message": f"Error fetching posts: {str(e)}"}

@app.post("/posts")
def create_post(post: PostCreate, request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth_header.split(" ")[1]
    
    supabase = get_supabase()
    user = _get_user_from_token(token)
    
    new_post = {k: v for k, v in post.dict().items() if v is not None}
    new_post["user_id"] = user.id
    
    # Supabase จะสร้าง UUID ให้เองตามที่ตั้งไว้ใน Default ของคอลัมน์ id
    # print("DEBUG INSERT DATA:", new_post)
    try:
        response = supabase.table("posts").insert(new_post).execute()
        created_data = response.data[0]
        
        # ส่งแจ้งเตือน Broadcast ผ่าน LINE OA
        if line_bot_api:
            try:
                title = created_data.get('title') or 'ไม่ระบุ'
                location = created_data.get('location') or 'ไม่ระบุ'
                img_urls = created_data.get('image_url', '').split(',')
                img_urls = [u for u in img_urls if u]
                if not img_urls:
                    img_urls = ["https://via.placeholder.com/400x300?text=No+Image"]
                
                user_metadata = user.user_metadata or {}
                line_id = user_metadata.get('line_social_id')
                
                is_lost = created_data.get('type') == 'lost'
                header_text = "🚨 ประกาศตามหาของหาย!" if is_lost else "✨ มีคนพบของตกหล่น!"
                header_color = "#ef4444" if is_lost else "#22c55e"
                post_url = f"{FRONTEND_BASE_URL}/post-detail.html?id={created_data.get('id')}"
                
                bubbles = []
                for img in img_urls[:1]: # Max 1 image
                    bubble = {
                        "type": "bubble",
                        "header": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": header_text,
                                    "weight": "bold",
                                    "color": "#ffffff",
                                    "size": "md"
                                }
                            ],
                            "backgroundColor": header_color
                        },
                        "hero": {
                            "type": "image",
                            "url": img,
                            "size": "full",
                            "aspectRatio": "20:13",
                            "aspectMode": "cover"
                        },
                        "body": {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": title,
                                    "weight": "bold",
                                    "size": "xl",
                                    "wrap": True
                                },
                                {
                                    "type": "box",
                                    "layout": "vertical",
                                    "margin": "lg",
                                    "spacing": "sm",
                                    "contents": [
                                        {
                                            "type": "box",
                                            "layout": "baseline",
                                            "spacing": "sm",
                                            "contents": [
                                                {
                                                    "type": "text",
                                                    "text": "สถานที่",
                                                    "color": "#aaaaaa",
                                                    "size": "sm",
                                                    "flex": 2
                                                },
                                                {
                                                    "type": "text",
                                                    "text": location,
                                                    "wrap": True,
                                                    "color": "#666666",
                                                    "size": "sm",
                                                    "flex": 5
                                                }
                                            ]
                                        },
                                        {
                                            "type": "box",
                                            "layout": "baseline",
                                            "spacing": "sm",
                                            "contents": [
                                                {
                                                    "type": "text",
                                                    "text": "LINE ID",
                                                    "color": "#aaaaaa",
                                                    "size": "sm",
                                                    "flex": 2
                                                },
                                                {
                                                    "type": "text",
                                                    "text": line_id if line_id else "ไม่ระบุ",
                                                    "wrap": True,
                                                    "color": "#666666",
                                                    "size": "sm",
                                                    "flex": 5
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        },
                        "footer": {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "height": "sm",
                                    "action": {
                                        "type": "uri",
                                        "label": "ดูรายละเอียด",
                                        "uri": post_url
                                    },
                                    "color": "#ea580c"
                                }
                            ]
                        }
                    }
                    bubbles.append(bubble)

                flex_content = bubbles[0] if len(bubbles) == 1 else {"type": "carousel", "contents": bubbles}
                alt_text = f"ประกาศใหม่: {title}"
                messages = [FlexSendMessage(alt_text=alt_text, contents=flex_content)]
                
                line_bot_api.broadcast(messages)
            except Exception as e:
                print(f"LINE Broadcast error: {e}")
                
        return {"message": "Post created successfully", "data": created_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating post: {str(e)}")

@app.get("/posts/{post_id}")
def get_post(post_id: str):
    supabase = get_supabase()
    response = supabase.table("posts").select("*").eq("id", post_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"data": response.data[0]}

def _tokenize_text(text: str) -> list:
    import re
    if not text:
        return []
    text = text.lower().strip()
    
    # แยกตามวรรคและสัญลักษณ์ก่อน
    raw_tokens = text.split()
    tokens = []
    
    for token in raw_tokens:
        # ตัดอักขระพิเศษที่ไม่ใช่ภาษาไทย/อังกฤษ/ตัวเลข
        token = re.sub(r'[^\w\u0e00-\u0e7f]', '', token)
        if not token:
            continue
        
        # ตรวจสอบว่ามีภาษาไทยหรือไม่
        has_thai = bool(re.search(r'[\u0e00-\u0e7f]', token))
        if has_thai:
            # ใช้ Bigram (2 อักษรติดกัน) สำหรับข้อความภาษาไทยเพื่อความแม่นยำในการคำนวณความคล้าย
            if len(token) <= 2:
                tokens.append(token)
            else:
                for i in range(len(token) - 1):
                    tokens.append(token[i:i+2])
        else:
            # ภาษาอังกฤษหรือตัวเลขให้ใช้เป็นคำเดี่ยวๆ
            tokens.append(token)
            
    return tokens

def calculate_match_score(new_post: dict, candidate: dict) -> dict:
    from datetime import datetime
    score = 0
    breakdown = {}
    
    # 1. Category Matching (Max 35 points)
    category_score = 35 if new_post.get("category") == candidate.get("category") else 0
    score += category_score
    breakdown["category"] = {
        "score": category_score,
        "max": 35,
        "message": "หมวดหมู่ตรงกัน" if category_score > 0 else "หมวดหมู่ไม่ตรงกัน"
    }
    
    # 2. Text Similarity (Max 35 points)
    title1 = new_post.get("title", "") or ""
    title2 = candidate.get("title", "") or ""
    desc1 = new_post.get("description", "") or ""
    desc2 = candidate.get("description", "") or ""
    
    tokens1_title = _tokenize_text(title1)
    tokens2_title = _tokenize_text(title2)
    
    title_overlap_score = 0
    if tokens1_title and tokens2_title:
        intersection = set(tokens1_title).intersection(set(tokens2_title))
        union = set(tokens1_title).union(set(tokens2_title))
        jaccard = len(intersection) / len(union) if union else 0
        
        # Substring bonus: if one title contains the other completely (and length > 2)
        if len(title1) > 2 and len(title2) > 2 and (title1.lower() in title2.lower() or title2.lower() in title1.lower()):
            title_overlap_score = max(14, int(jaccard * 20))
        else:
            title_overlap_score = int(jaccard * 20)
    score += title_overlap_score
    breakdown["title"] = {
        "score": title_overlap_score,
        "max": 20,
        "message": f"ความคล้ายคลึงของหัวข้อ ({title_overlap_score}/20)"
    }
    
    desc_overlap_score = 0
    tokens1_desc = _tokenize_text(desc1)
    tokens2_desc = _tokenize_text(desc2)
    if tokens1_desc and tokens2_desc:
        intersection = set(tokens1_desc).intersection(set(tokens2_desc))
        union = set(tokens1_desc).union(set(tokens2_desc))
        jaccard = len(intersection) / len(union) if union else 0
        
        if len(desc1) > 5 and len(desc2) > 5 and (desc1.lower() in desc2.lower() or desc2.lower() in desc1.lower()):
            desc_overlap_score = max(10, int(jaccard * 15))
        else:
            desc_overlap_score = int(jaccard * 15)
    score += desc_overlap_score
    breakdown["description"] = {
        "score": desc_overlap_score,
        "max": 15,
        "message": f"ความคล้ายคลึงของรายละเอียด ({desc_overlap_score}/15)"
    }
    
    # 3. Location Matching (Max 18 points)
    loc1 = new_post.get("location", "") or ""
    loc2 = candidate.get("location", "") or ""
    loc_score = 0
    if loc1 and loc2:
        loc1_clean = loc1.lower().strip()
        loc2_clean = loc2.lower().strip()
        if loc1_clean == loc2_clean:
            loc_score = 18
        elif len(loc1_clean) > 2 and len(loc2_clean) > 2 and (loc1_clean in loc2_clean or loc2_clean in loc1_clean):
            loc_score = 12
        else:
            tok1 = _tokenize_text(loc1)
            tok2 = _tokenize_text(loc2)
            if tok1 and tok2:
                intersection = set(tok1).intersection(set(tok2))
                union = set(tok1).union(set(tok2))
                jaccard = len(intersection) / len(union) if union else 0
                loc_score = int(jaccard * 10)
    score += loc_score
    breakdown["location"] = {
        "score": loc_score,
        "max": 18,
        "message": "สถานที่ตรงกัน" if loc_score == 18 else ("สถานที่ใกล้เคียงกัน" if loc_score >= 10 else ("สถานที่ต่างกันแต่มีส่วนคล้าย" if loc_score > 0 else "สถานที่ต่างกัน"))
    }
    
    # 4. Date Proximity (Max 12 points)
    date_score = 0
    d1_str = new_post.get("lost_found_date")
    d2_str = candidate.get("lost_found_date")
    diff_days = None
    if d1_str and d2_str:
        try:
            d1 = datetime.strptime(d1_str.split("T")[0], "%Y-%m-%d")
            d2 = datetime.strptime(d2_str.split("T")[0], "%Y-%m-%d")
            diff_days = abs((d1 - d2).days)
            if diff_days == 0:
                date_score = 12
            elif diff_days <= 2:
                date_score = 10
            elif diff_days <= 4:
                date_score = 8
            elif diff_days <= 7:
                date_score = 6
            elif diff_days <= 14:
                date_score = 4
            else:
                date_score = 2
        except Exception:
            date_score = 0
    score += date_score
    
    date_msg = "ช่วงเวลาเดียวกัน" if date_score == 12 else (f"ช่วงเวลาใกล้เคียงกัน ห่างกัน {diff_days} วัน" if diff_days is not None and date_score >= 4 else "ช่วงเวลาห่างกันค่อนข้างมาก")
    breakdown["date"] = {
        "score": date_score,
        "max": 12,
        "message": date_msg
    }
    
    return {"score": min(score, 100), "breakdown": breakdown}

@app.get("/posts/{post_id}/recommendations")
def get_recommendations(post_id: str):
    supabase = get_supabase()
    post_res = supabase.table("posts").select("*").eq("id", post_id).execute()
    if not post_res.data:
        raise HTTPException(status_code=404, detail="Post not found")
    new_post = post_res.data[0]
    
    opposite_type = "found" if new_post["type"] == "lost" else "lost"
    # Select published/active items
    candidates_res = supabase.table("posts").select("*").eq("type", opposite_type).neq("status", "claimed").execute()
    candidates = candidates_res.data or []
    
    scored_candidates = []
    for cand in candidates:
        match_info = calculate_match_score(new_post, cand)
        cand_copy = dict(cand)
        cand_copy["match_score"] = match_info["score"]
        cand_copy["match_breakdown"] = match_info["breakdown"]
        scored_candidates.append(cand_copy)
        
    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    
    top_6 = scored_candidates[:6]
    
    # Map author names
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if service_key and service_key.upper() not in ("YOUR_SUPABASE_SERVICE_KEY", "YOUR_SUPABASE_SERVICE_ROLE_KEY"):
        from supabase import create_client
        supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
        try:
            users = supabase_admin.auth.admin.list_users()
            user_map = {}
            for u in users:
                meta = u.user_metadata or {}
                user_map[u.id] = meta.get("full_name") or meta.get("name") or "ผู้ใช้งาน"
            
            for p in top_6:
                p["author_name"] = user_map.get(p.get("user_id"), "ผู้ใช้งาน")
        except Exception as e:
            print(f"Failed to fetch users: {e}")
            
    return {"data": top_6, "message": "Recommendations generated successfully"}

@app.put("/posts/{post_id}")
def update_post(post_id: str, post: PostUpdate, request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth_header.split(" ")[1]

    supabase = get_supabase()
    user = _get_user_from_token(token)

    # Determine if user is admin via metadata flag
    is_admin = False
    try:
        metadata = user.user_metadata or {}
        is_admin = metadata.get("is_admin", False)
    except Exception:
        is_admin = False

    if not is_admin:
        # Check ownership for regular users
        existing_post = supabase.table("posts").select("user_id").eq("id", post_id).execute()
        if not existing_post.data:
            raise HTTPException(status_code=404, detail="Post not found")
        if existing_post.data[0]["user_id"] != user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to update this post")
            
        if post.status is not None and post.status != "claimed":
            raise HTTPException(status_code=400, detail="คุณสามารถเปลี่ยนสถานะเป็น 'เสร็จสิ้น (เจ้าของมารับแล้ว)' ได้เท่านั้น")

    update_data = {k: v for k, v in post.dict().items() if v is not None}
    response = supabase.table("posts").update(update_data).eq("id", post_id).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Post not found or could not update")
    return {"message": "Post updated successfully", "data": response.data[0]}

@app.delete("/posts/{post_id}")
def delete_post(post_id: str):
    supabase = get_supabase()
    response = supabase.table("posts").delete().eq("id", post_id).execute()
    return {"message": "Post deleted successfully"}

# --- UPLOAD ---
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not r2_client:
        # Fallback to Supabase if R2 is not configured
        supabase = get_supabase()
        file_bytes = await file.read()
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = f"post_images/{unique_filename}"
        try:
            supabase.storage.from_("images").upload(file_path, file_bytes)
            img_url = supabase.storage.from_("images").get_public_url(file_path)
            return {"url": img_url, "message": "File uploaded to Supabase"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Supabase upload error: {str(e)}")

    # Use Cloudflare R2
    file_bytes = await file.read()
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    
    try:
        r2_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=unique_filename,
            Body=file_bytes,
            ContentType=file.content_type
        )
        
        img_url = f"{R2_PUBLIC_URL}/{unique_filename}"
        return {"url": img_url, "message": "File uploaded to Cloudflare R2"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cloudflare R2 upload error: {str(e)}")

# --- SEARCH ---
@app.get("/search")
def search_items(q: str):
    return {"data": [], "message": f"Search results for {q}"}

# --- MESSAGES ---
@app.get("/messages/{user_id}")
def get_messages(user_id: str):
    return {"data": [], "message": "List of messages"}

@app.post("/messages")
def send_message(msg: MessageCreate):
    return {"message": "Message sent successfully", "data": msg.dict()}

# --- SUPER ADMIN ENDPOINTS ---
# Require admin role via user_metadata.is_admin == true

# Duplicate _require_admin helper deleted, using definition from lines 49-58.

@app.get("/admin/users")
def admin_list_users(request: Request):
    _require_admin(request)
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key == "YOUR_SUPABASE_SERVICE_KEY":
        raise HTTPException(status_code=503, detail="Service key not configured")
    from supabase import create_client
    supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
    users = supabase_admin.auth.admin.list_users()
    return {"data": users, "message": "User list"}

@app.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: str, request: Request):
    _require_admin(request)
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key == "YOUR_SUPABASE_SERVICE_KEY":
        raise HTTPException(status_code=503, detail="Service key not configured")
    from supabase import create_client
    supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
    try:
        supabase_admin.auth.admin.delete_user(user_id)
        return {"message": f"User {user_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/super-admin/users/{user_id}/role")
def super_admin_update_role(user_id: str, request: Request, is_admin: bool = Body(..., embed=True), is_super_admin: bool = Body(False, embed=True)):
    """Only Super Admin can change roles of other users."""
    _require_super_admin(request)
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key == "YOUR_SUPABASE_SERVICE_KEY":
        raise HTTPException(status_code=503, detail="Service key not configured")
    from supabase import create_client
    supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
    try:
        supabase_admin.auth.admin.update_user_by_id(user_id, {"user_metadata": {"is_admin": is_admin, "is_super_admin": is_super_admin}})
        return {"message": f"User {user_id} role updated", "is_admin": is_admin, "is_super_admin": is_super_admin}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/super-admin/users/{user_id}/name")
def super_admin_update_name(user_id: str, request: Request, full_name: str = Body(..., embed=True)):
    """Only Super Admin can change names of other users."""
    _require_super_admin(request)
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key == "YOUR_SUPABASE_SERVICE_KEY":
        raise HTTPException(status_code=503, detail="Service key not configured")
    from supabase import create_client
    supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
    try:
        supabase_admin.auth.admin.update_user_by_id(user_id, {"user_metadata": {"full_name": full_name}})
        return {"message": f"User {user_id} name updated", "full_name": full_name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/admin/users/{user_id}/role")
def admin_update_user_role(user_id: str, request: Request, is_admin: bool = Body(..., embed=True)):
    """Allow Admin to give Admin role? Actually, let's restrict this to Super Admin too for safety, 
    or keep it as requested: 'Super Admin is above admin and can give admin role'."""
    _require_super_admin(request)
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key == "YOUR_SUPABASE_SERVICE_KEY":
        raise HTTPException(status_code=503, detail="Service key not configured")
    from supabase import create_client
    supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
    try:
        supabase_admin.auth.admin.update_user_by_id(user_id, {"user_metadata": {"is_admin": is_admin}})
        return {"message": f"User {user_id} role updated", "is_admin": is_admin}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/admin/users/{user_id}/ban")
def admin_ban_user(user_id: str, request: Request, is_banned: bool = Body(..., embed=True)):
    _require_admin(request)
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key == "YOUR_SUPABASE_SERVICE_KEY":
        raise HTTPException(status_code=503, detail="Service key not configured")
    from supabase import create_client
    supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)
    try:
        supabase_admin.auth.admin.update_user_by_id(user_id, {"user_metadata": {"is_banned": is_banned}})
        return {"message": f"User {user_id} ban status updated", "is_banned": is_banned}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/admin/posts")
def admin_list_posts(request: Request):
    _require_admin(request)
    supabase = get_supabase()
    resp = supabase.table("posts").select("*").execute()
    return {"data": resp.data, "message": "Posts list"}

@app.delete("/admin/posts/{post_id}")
def admin_delete_post(post_id: str, request: Request):
    _require_admin(request)
    supabase = get_supabase()
    resp = supabase.table("posts").delete().eq("id", post_id).execute()
    return {"message": f"Post {post_id} deleted"}


from fastapi import Body

# --- ADMIN ENDPOINTS ---
@app.put("/admin/posts/{post_id}/status")
def admin_update_status(post_id: str, request: Request, status: str = Body(..., embed=True)):
    """Allow admin users to update only the status of any post.
    Expected status values: 'pending', 'published', 'claimed'."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth_header.split(" ")[1]

    supabase = get_supabase()
    user = _get_user_from_token(token)

    metadata = user.user_metadata or {}
    is_admin = metadata.get("is_admin", False)
    is_super = metadata.get("is_super_admin", False)
    if not is_admin and not is_super:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    allowed_statuses = {"pending", "published", "claimed"}
    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid status value")

    # We need to use the service key to bypass RLS
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not service_key or service_key == "YOUR_SUPABASE_SERVICE_KEY":
        raise HTTPException(status_code=503, detail="Service key not configured")
    
    from supabase import create_client
    supabase_admin = create_client(os.getenv("SUPABASE_URL"), service_key)

    admin_name = metadata.get("full_name") or metadata.get("name") or "Admin"

    # Update only the status field (and status_by_name if column exists)
    try:
        response = supabase_admin.table("posts").update({
            "status": status, 
            "status_by_name": admin_name
        }).eq("id", post_id).execute()
    except Exception as e:
        # Fallback if status_by_name column is not created yet
        response = supabase_admin.table("posts").update({"status": status}).eq("id", post_id).execute()
        print(f"Fallback without status_by_name: {e}")

    if not response.data:
        raise HTTPException(status_code=404, detail="Post not found or could not update")
    return {"message": "Post status updated successfully", "data": response.data[0]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
