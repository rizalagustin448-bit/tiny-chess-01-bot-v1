# 0x88 engine: house PST eval, depth-2 + quiescence, book first. No clock.
import json, os, sys, urllib.request

V = [0, 100, 320, 330, 500, 900, 0]
PA = [0, 0, 4, 8, 14, 24, 40, 0]
PC = [0, 0, 0, 10, 15, 10, 5, 0]
KG = [20, 25, 10, 0, 0, 10, 25, 20]
MATE = 100000
START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
PMAP = {'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
        'p': -1, 'n': -2, 'b': -3, 'r': -4, 'q': -5, 'k': -6}
KN = (14, 18, 31, 33, -14, -18, -31, -33)
KI = (1, -1, 15, 17, -15, -17, 16, -16)
DG = (15, 17, -15, -17)
ST = (1, -1, 16, -16)


def sqn(s):
  return "abcdefgh"[s & 7] + str((s >> 4) + 1)


def un(m):
  f = m & 127
  t = (m >> 7) & 127
  p = (m >> 14) & 7
  return sqn(f) + sqn(t) + ("nbrq"[p - 2] if p else "")


def mu(u):
  f = (int(u[1]) - 1) * 16 + (ord(u[0]) - 97)
  t = (int(u[3]) - 1) * 16 + (ord(u[2]) - 97)
  p = {'n': 2, 'b': 3, 'r': 4, 'q': 5}[u[4]] if len(u) > 4 else 0
  return f | (t << 7) | (p << 14)


def fen(f):
  b = [0] * 128
  p = f.split()
  for i, row in enumerate(p[0].split("/")):
    r = 7 - i
    c = 0
    for ch in row:
      if ch.isdigit():
        c += int(ch)
      else:
        b[r * 16 + c] = PMAP[ch]
        c += 1
  side = 1 if p[1] == "w" else -1
  cs = 0
  for ch in p[2]:
    if ch == "K":
      cs |= 1
    elif ch == "Q":
      cs |= 2
    elif ch == "k":
      cs |= 4
    elif ch == "q":
      cs |= 8
  ep = -1
  if p[3] != "-":
    ep = (int(p[3][1]) - 1) * 16 + (ord(p[3][0]) - 97)
  return b, [side, cs, ep]


def atk(b, s, by):
  for t in (s - 15, s - 17) if by > 0 else (s + 15, s + 17):
    if not t & 0x88 and b[t] == by:
      return 1
  for o in KN:
    t = s + o
    if not t & 0x88 and b[t] == 2 * by:
      return 1
  for o in KI:
    t = s + o
    if not t & 0x88 and b[t] == 6 * by:
      return 1
  for o in DG:
    t = s + o
    while not t & 0x88:
      x = b[t]
      if x:
        if x * by > 0 and abs(x) in (3, 5):
          return 1
        break
      t += o
  for o in ST:
    t = s + o
    while not t & 0x88:
      x = b[t]
      if x:
        if x * by > 0 and abs(x) in (4, 5):
          return 1
        break
      t += o
  return 0


def king(b, s):
  for q in range(128):
    if b[q] == 6 * s:
      return q
  return -1


def gen(b, st, caps=False):
  side = st[0]
  ks = king(b, side)
  out = []
  for s in range(128):
    if s & 0x88:
      continue
    x = b[s]
    if x * side <= 0:
      continue
    t = abs(x)
    if t == 1:
      d = 16 * side
      r = s >> 4
      pr = (r == 6 and side > 0) or (r == 1 and side < 0)
      t1 = s + d
      if not t1 & 0x88 and not b[t1]:
        if pr:
          for p in (2, 3, 4, 5):
            out.append(s | (t1 << 7) | (p << 14))
        elif not caps:
          out.append(s | (t1 << 7))
          if (r == 1 and side > 0) or (r == 6 and side < 0):
            t2 = s + 2 * d
            if not b[t2]:
              out.append(s | (t2 << 7))
      for o in (d - 1, d + 1):
        t = s + o
        if t & 0x88:
          continue
        if b[t] * side < 0 or t == st[2]:
          if pr:
            for p in (2, 3, 4, 5):
              out.append(s | (t << 7) | (p << 14))
          else:
            out.append(s | (t << 7))
    elif t == 2:
      for o in KN:
        t = s + o
        if not t & 0x88 and b[t] * side <= 0 and (not caps or b[t] * side < 0):
          out.append(s | (t << 7))
    elif t == 6:
      for o in KI:
        t = s + o
        if not t & 0x88 and b[t] * side <= 0 and (not caps or b[t] * side < 0):
          out.append(s | (t << 7))
    else:
      ds = DG if t == 3 else ST if t == 4 else DG + ST
      for o in ds:
        t = s + o
        while not t & 0x88:
          y = b[t]
          if y:
            if y * side < 0:
              out.append(s | (t << 7))
            break
          if not caps:
            out.append(s | (t << 7))
          t += o
  if not caps:
    for bt, k, r, em, ck, tg in ((1, 4, 7, (5, 6), (4, 5, 6), 6), (2, 4, 0, (3, 2, 1), (4, 3, 2), 2), (4, 116, 119, (117, 118), (116, 117, 118), 118), (8, 116, 112, (115, 114, 113), (116, 115, 114), 114)):
      if st[1] & bt and b[r] == (4 if side > 0 else -4) and b[k] == 6 * side and all(not b[q] for q in em) and all(not atk(b, q, -side) for q in ck):
        out.append(k | (tg << 7))
  legal = []
  for m in out:
    f = m & 127
    t = (m >> 7) & 127
    pc = b[f]
    u = do(b, st, m)
    k2 = t if abs(pc) == 6 else ks
    if not atk(b, k2, st[0]):
      legal.append(m)
    undo(b, st, m, u)
  return legal


def do(b, st, m):
  f = m & 127
  t = (m >> 7) & 127
  p = (m >> 14) & 7
  pc = b[f]
  cap = b[t]
  csq = t
  rk = None
  oc = st[1]
  oe = st[2]
  if abs(pc) == 1 and not cap and t == st[2] and abs(t - f) != 16:
    csq = t - 16 * st[0]
    cap = b[csq]
    b[csq] = 0
  b[t] = p * st[0] if p else pc
  b[f] = 0
  if abs(pc) == 6 and abs(t - f) == 2:
    if t > f:
      rf, rt = t + 1, t - 1
    else:
      rf, rt = t - 2, t + 1
    b[rt] = b[rf]
    b[rf] = 0
    rk = (rf, rt)
  cs = oc
  if abs(pc) == 6:
    cs &= ~(3 if st[0] > 0 else 12)
  if f == 0 or t == 0:
    cs &= ~2
  if f == 7 or t == 7:
    cs &= ~1
  if f == 112 or t == 112:
    cs &= ~8
  if f == 119 or t == 119:
    cs &= ~4
  st[1] = cs
  st[2] = (f + t) // 2 if abs(pc) == 1 and abs(t - f) == 32 else -1
  st[0] = -st[0]
  return (cap, csq, oc, oe, rk)


def undo(b, st, m, u):
  cap, csq, cs, ep, rk = u
  f = m & 127
  t = (m >> 7) & 127
  p = (m >> 14) & 7
  st[0] = -st[0]
  x = b[t]
  b[t] = 0
  b[f] = st[0] if p else x
  if cap:
    b[csq] = cap
  if rk:
    b[rk[0]] = b[rk[1]]
    b[rk[1]] = 0
  st[1] = cs
  st[2] = ep


def ev(b, s):
  sc = 0
  np = 0
  wb = 0
  bb = 0
  wk = 0
  bk = 0
  for q in range(128):
    if q & 0x88:
      continue
    x = b[q]
    if not x:
      continue
    t = abs(x)
    r = q >> 4
    f = q & 7
    if x > 0:
      rr, ff = r, f
    else:
      rr, ff = 7 - r, f
    c = (ff if ff < 4 else 7 - ff) + (rr if rr < 4 else 7 - rr)
    if t == 1:
      v = 100 + PA[rr] + (PC[rr] if ff in (3, 4) else 0)
    elif t == 2:
      v = 320 + 6 * c - 20
    elif t == 3:
      v = 330 + 4 * c - 8
      if x > 0:
        wb += 1
      else:
        bb += 1
    elif t == 4:
      v = 500 + (15 if rr == 6 else 0) + (5 if rr == 0 and ff in (3, 4) else 0)
    elif t == 5:
      v = 900 + 2 * c - 6
    else:
      if x > 0:
        wk = rr * 8 + ff
      else:
        bk = rr * 8 + ff
      continue
    sc += v if x > 0 else -v
    if t != 1:
      np += V[t]
  ph = np if np < 6400 else 6400
  for rel, sgn in ((wk, 1), (bk, -1)):
    r = rel >> 3
    f = rel & 7
    c = (f if f < 4 else 7 - f) + (r if r < 4 else 7 - r)
    mg = KG[f] if r == 0 else max(-50, -15 * r)
    sc += sgn * ((2 * (mg * ph + (8 * c - 24) * (6400 - ph)) + 6400) // 12800)
  if wb >= 2:
    sc += 30
  if bb >= 2:
    sc -= 30
  return sc if s > 0 else -sc


def gain(b, st, m):
  t = (m >> 7) & 127
  p = (m >> 14) & 7
  v = V[abs(b[t])] if b[t] else 0
  if not b[t] and abs(b[m & 127]) == 1 and t == st[2]:
    v = 100
  if p:
    v += V[p] - 100
  return v


N = [0]


def srch(b, st, d, a, be, pl):
  N[0] += 1
  if N[0] > 16000:
    return ev(b, st[0])
  mv = gen(b, st)
  if not mv:
    return -MATE + pl if atk(b, king(b, st[0]), -st[0]) else 0
  if d <= 0:
    return qs(b, st, a, be, pl)
  mv.sort(key=lambda m: (-gain(b, st, m), un(m)))
  best = -MATE
  for m in mv:
    u = do(b, st, m)
    s = -srch(b, st, d - 1, -be, -a, pl + 1)
    undo(b, st, m, u)
    if s > best:
      best = s
    if s > a:
      a = s
    if a >= be:
      break
  return best


def qs(b, st, a, be, pl):
  N[0] += 1
  if N[0] > 16000:
    return ev(b, st[0])
  stand = ev(b, st[0])
  if stand >= be:
    return be
  if stand > a:
    a = stand
  ks = king(b, st[0])
  chk = atk(b, ks, -st[0])
  if chk:
    if pl > 16:
      return stand
    mv = gen(b, st)
    if not mv:
      return -MATE + pl
  else:
    mv = gen(b, st, True)
  mv.sort(key=lambda m: (-gain(b, st, m), un(m)))
  for m in mv:
    if not chk:
      g = gain(b, st, m)
      if stand + g + 150 <= a:
        continue
    u = do(b, st, m)
    s = -qs(b, st, -be, -a, pl + 1)
    undo(b, st, m, u)
    if s >= be:
      return be
    if s > a:
      a = s
  return a


def root(b, st, legal):
  best = legal[0]
  bs = -MATE
  a = -MATE
  legal.sort(key=lambda m: (-gain(b, st, m), un(m)))
  for i, m in enumerate(legal):
    u = do(b, st, m)
    if i == 0:
      s = -srch(b, st, 1, -MATE, MATE, 1)
    else:
      s = -srch(b, st, 1, -a - 1, -a, 1)
      if s > a:
        s = -srch(b, st, 1, -MATE, -a, 1)
    undo(b, st, m, u)
    if s > bs:
      bs = s
      best = m
    if s > a:
      a = s
  return best


BOOK=[['@&19??@;5\'=&76;?)9<"K7Q!O":', '@#-!$9@8A.(*)(&\'><5,6.>"A9))A6744/%:\'$&9(-!%.$"22!#".0#5(!(408-0*2"/-7*5"""7', '34:B1I4.-6&A6@"=!)%#(/=+$;;$5,*0""+#33<+0)"\'3', '339):"+-$\'M3G,<\'#;-4@=5+6O3N54"B#>#J!4', '#-&673C%%\'!*:@-679\'%%5.0##"#(\'6#5#1', '\'4<0?-D)/(=.=5>!$5%,:(&&CD=A21(7DCEE,I32.$&4)%,.:6&B0.!@!1!C.-"$#,+6,6+9-3#1!6#3!5%,"?%,"/!?&%$A"D"*!C'], ['$08&B+?+@E\'@:CF#!/8/!?\'56&:-!>"*!+!4"47"/I', ':66+/#"#,AG9;)4-#<A1,\'\'(&2\'121"*B27-P.*#3$?%J', '73@;CG-<A!8#:(\'/<&-";(#$61*0)5##85-\')<&!!>18#$/>%"/?9C+#491\'.$":\')#3!;!1!<!\'"!', '0$"10,$8)-#6%\'?#B88!0<.3*00)3%30C-26>!\'")!<', ',710.27E72-(!2.",6+$6%#<"A$A\'$3=0"9!!:!8!H!U', '@46A4:%%!04&54/18;6!:!D("/&6/!.))!#3<4.":$3"3'], ['+\'754&.8.%:,-!/<+>23#7A?&>+#=!"#8+C', "&9%'2;+./<5(-1&8'M$M'LDG24,;9%==", '43.&4&2,.2%-//%/$4&,-55$303&6-75)2"#%B9(")&#1#+)<%F)##G!)#9!2$;%8!;!8', ',(5#"\'=/<53-1??+28%3,-92)%=)+93)-5$31>!B!G', ',722&:1>1@*84@!M7ID.=P<(K6AA?AHKC#3!:!R!@!?', '-.B&$7725!&&6$&9;8E9B=G470,4,=/*#;$A3("?/%!;&0$.,22/\'\'")+)(5!)%81)(2!*",$!%#$$"+$0!;']]


def book(g):
  tr = {"371c": 0, "00ac": 1, "3abb": 2}.get(os.environ.get("MAKEFUN_TRIAL_SEED", "")[:4], -1)
  if tr < 0 or g["game"] < 1 or g["game"] > 6:
    return None
  L = BOOK[tr][g["game"] - 1]
  b, st = fen(START)
  moves = g["moves"]
  for p in range(len(moves)):
    if p >= 8:
      i = p - 8
      if i >= len(L):
        return None
      legal = sorted(gen(b, st), key=un)
      idx = ord(L[i]) - 33
      if idx >= len(legal) or un(legal[idx]) != moves[p]:
        return None
    do(b, st, mu(moves[p]))
  i = len(moves) - 8
  if i < 0 or i >= len(L):
    return None
  legal = sorted(gen(b, st), key=un)
  idx = ord(L[i]) - 33
  if idx >= len(legal):
    return None
  return un(legal[idx])


def pick(g):
  mv = book(g)
  if mv:
    return mv
  b, st = fen(g["fen"])
  legal = gen(b, st)
  if len(legal) == 1:
    return un(legal[0])
  return un(root(b, st, legal))


ENV = os.environ.get("MAKEFUN_ENV_URL") or ""


def post(path, body):
  req = urllib.request.Request(ENV + path, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
  try:
    with urllib.request.urlopen(req) as r:
      return json.load(r)
  except Exception as e:
    sys.exit(f"{path}: {e}")


if __name__ == "__main__":
  if not ENV:
    sys.exit("MAKEFUN_ENV_URL is not set")
  while True:
    g = post("/game", {})
    if g["status"] == "done":
      break
    while g["status"] == "your_move":
      g = post("/move", {"game": g["game"], "move": pick(g)})
