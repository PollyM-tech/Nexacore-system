"""Disposable NAS simulator and RADIUS wire client. No real router or provider calls."""
import hashlib, hmac, json, os, secrets, socket, struct, sys


def attr(t,v):
    return bytes([t,len(v)+2])+v


def attrs(data):
    offset=20; result=[]
    while offset<len(data):
        t,n=data[offset:offset+2]
        assert n>=2 and offset+n<=len(data)
        result.append((t,data[offset+2:offset+n])); offset+=n
    return result


def daemon():
    secret=os.environ['OWN_SECRET'].encode(); attempts={}
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind(('0.0.0.0',3799))
        while True:
            data,remote=sock.recvfrom(4096)
            if len(data)<20 or data[0]!=40: continue
            assert data[4:20]==hashlib.md5(data[:4]+bytes(16)+data[20:]+secret).digest()
            values=attrs(data); sid=next(v.decode() for t,v in values if t==44)
            # Independently check the request Message-Authenticator.
            ma=next(v for t,v in values if t==80)
            rebuilt=b''.join(attr(t,bytes(16) if t==80 else v) for t,v in values)
            assert ma==hmac.new(secret,data[:4]+bytes(16)+rebuilt,hashlib.md5).digest()
            attempts[sid]=attempts.get(sid,0)+1
            if sid=='retry-once' and attempts[sid]==1: continue
            response_attrs=attr(101,struct.pack('!I',503)) if sid=='already-gone' else b''
            code=42 if sid=='already-gone' else 41
            response_attrs+=attr(80,bytes(16))
            header=struct.pack('!BBH',code,data[1],20+len(response_attrs))
            ma=hmac.new(secret,header+data[4:20]+response_attrs,hashlib.md5).digest()
            response_attrs=response_attrs[:-16]+ma
            response=header+hashlib.md5(header+data[4:20]+response_attrs+secret).digest()+response_attrs
            if sid=='invalid-response': response=response[:4]+bytes(16)+response[20:]
            sock.sendto(response,remote)


def probe():
    kind,identity=sys.argv[1:3]
    username=os.environ.get('CODE_'+identity,identity)
    password=username if identity!='PPP' else os.environ['PPP_PASSWORD']
    if '--wrong-password' in sys.argv: password='wrong-password'
    secret=os.environ['OWN_SECRET'].encode()
    if '--wrong-secret' in sys.argv: secret=b'wrong-secret-for-negative-test'
    identifier=secrets.randbelow(256); authenticator=secrets.token_bytes(16)
    sid=os.environ.get('SESSION_ID','wire-session')
    mac='AA-BB-CC-DD-EE-02' if '--second-device' in sys.argv else 'AA-BB-CC-DD-EE-01'
    own_ip=os.environ['OWN_IP'] if '--spoof-source' not in sys.argv else os.environ['OTHER_IP']
    values=attr(1,username.encode())+attr(4,socket.inet_aton(own_ip))+attr(31,mac.encode())+attr(44,sid.encode())
    if kind=='auth':
        if '--chap' in sys.argv:
            values+=attr(3,bytes([identifier])+hashlib.md5(bytes([identifier])+password.encode()+authenticator).digest())
        else:
            padded=password.encode()+bytes((16-len(password.encode())%16)%16)
            encrypted=b'';previous=authenticator
            for pos in range(0,len(padded),16):
                block=bytes(a^b for a,b in zip(padded[pos:pos+16],hashlib.md5(secret+previous).digest()));encrypted+=block;previous=block
            values+=attr(2,encrypted)
        code,port=1,1812
    else:
        code,port=4,1813
        status={'start':1,'interim':3,'stop':2}[kind]
        values+=attr(40,struct.pack('!I',status))+attr(42,struct.pack('!I',int(os.environ.get('UPLOAD','0'))))+attr(43,struct.pack('!I',int(os.environ.get('DOWNLOAD','0'))))
        values+=attr(46,struct.pack('!I',int(os.environ.get('DURATION','0'))))
        authenticator=bytes(16)
    values+=attr(80,bytes(16))
    header=struct.pack('!BBH',code,identifier,20+len(values))
    values=values[:-16]+hmac.new(secret,header+authenticator+values,hashlib.md5).digest()
    if code==4: authenticator=hashlib.md5(header+bytes(16)+values+secret).digest()
    request=header+authenticator+values
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.settimeout(5);sock.connect(('radius',port));sock.send(request)
        try: response=sock.recv(4096)
        except socket.timeout: print(json.dumps({'code':'timeout'}));return
    assert response[1]==identifier
    assert response[4:20]==hashlib.md5(response[:4]+authenticator+response[20:]+secret).digest()
    result={'code':response[0]}
    for t,v in attrs(response):
        if t==27: result['session_timeout']=struct.unpack('!I',v)[0]
        if t==26 and struct.unpack('!I',v[:4])[0]==14988:
            vt,vl=v[4:6];value=v[6:4+vl]
            if vt==8: result['rate']=value.decode()
            if vt==17: result['quota']=struct.unpack('!I',value)[0]
    print(json.dumps(result))

if __name__=='__main__':
    if sys.argv[1]=='daemon': daemon()
    else: probe()
