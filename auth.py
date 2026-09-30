import hashlib
import hmac
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
import settings
import store

router=APIRouter(prefix='/api/auth')
COOKIE='harvest_session'

def password_hash(password):
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()

def verify(password,encoded):
    salt,expected=encoded.split(':')
    actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    return hmac.compare_digest(actual,expected)

DUMMY=password_hash('not-a-real-account-password')

def token_hash(value):return hashlib.sha256(value.encode()).hexdigest()

def current_user(request: Request):
    token=request.cookies.get(COOKIE,'')
    with store.connection() as db:
        row=db.execute('SELECT u.id,u.email,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.disabled=0',(token_hash(token),time.time())).fetchone()
    if not row:raise HTTPException(401,'Please sign in.')
    user=dict(row)
    if request.method not in ('GET','HEAD','OPTIONS'):
        if not hmac.compare_digest(request.headers.get('x-csrf-token',''),user['csrf']):raise HTTPException(403,'Invalid session request token. Reload the page.')
    return user

class Login(BaseModel):
    email: str=Field(min_length=3,max_length=254)
    password: str=Field(min_length=1,max_length=256)

@router.post('/login')
def login(body: Login,request: Request,response: Response):
    # Uses transport peer, not untrusted X-Forwarded-For. Gateway provides a trusted peer in hosted mode.
    peer=request.client.host if request.client else 'unknown'
    key='login:'+token_hash(peer)
    if not store.rate(key,20,900):raise HTTPException(429,'Too many sign-in attempts. Try again in 15 minutes.')
    with store.connection() as db:row=db.execute('SELECT * FROM users WHERE email=?',(body.email.lower().strip(),)).fetchone()
    ok=verify(body.password,row['password'] if row else DUMMY)
    if not row or not ok or row['disabled']:raise HTTPException(401,'Invalid email or password.')
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
    with store.connection(True) as db:
        db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
        db.execute('INSERT INTO sessions VALUES (?,?,?,?)',(token_hash(token),row['id'],csrf,time.time()+settings.SESSION_SECONDS))
        store.audit(db,row['id'],'login')
    response.set_cookie(COOKIE,token,httponly=True,secure=settings.COOKIE_SECURE,samesite='strict',max_age=settings.SESSION_SECONDS,path='/')
    return {'email':row['email'],'csrf':csrf}

@router.get('/me')
def me(user=Depends(current_user)):return {'email':user['email'],'csrf':user['csrf']}

@router.post('/logout')
def logout(request: Request,response: Response,user=Depends(current_user)):
    with store.connection(True) as db:
        db.execute('DELETE FROM sessions WHERE token=?',(token_hash(request.cookies.get(COOKIE,'')),))
        store.audit(db,user['id'],'logout')
    response.delete_cookie(COOKIE,path='/')
    return {'ok':True}
