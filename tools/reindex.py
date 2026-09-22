#!/usr/bin/env python3
from pathlib import Path
import json,re,shutil,sys,datetime
import fitz

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'protocols.json'
SINGLE=ROOT/'updates'/'single'
FULL=ROOT/'updates'/'full'
PUB=ROOT/'updates'/'published'
CURRENT_BOOK=PUB/'current-protocol-book.pdf'

def clean_lines(text):
    out=[]
    for raw in text.splitlines():
        s=re.sub(r'\s+',' ',raw).strip()
        if not s or re.fullmatch(r'\d+',s):
            continue
        out.append(s)
    return out

def search_blob(item):
    return (' '.join([item.get('title',''),*item.get('lines',[]),*item.get('aliases',[])])).lower()

def extract_pdf(path):
    d=fitz.open(path)
    return [clean_lines(p.get_text('text')) for p in d]

def replace_single(data,path):
    slug=path.stem
    matches=[x for x in data if x['id']==slug]
    if not matches:
        print(f'ERROR: no existing protocol id {slug!r}. Rename the PDF to match the protocol id.',file=sys.stderr)
        return False
    pages=extract_pdf(path)
    lines=[x for pg in pages for x in pg]
    if not lines:
        print(f'ERROR: no extractable text in {path.name}',file=sys.stderr)
        return False
    item=matches[0]
    dest=PUB/path.name
    shutil.copy2(path,dest)
    item['lines']=lines
    item['search']=search_blob({**item,'lines':lines})
    item['sourceFile']=f'updates/published/{path.name}'
    item['updated']=datetime.date.today().isoformat()
    item['page']=1
    item['endPage']=len(pages)
    path.unlink()
    print(f'Updated {item["title"]}')
    return True

def norm(s):
    return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()

def rebuild_full(data,path):
    doc=fitz.open(path)
    ptexts=[p.get_text('text') for p in doc]
    bootstrap=all(not x.get('lines') for x in data)

    if bootstrap:
        for item in data:
            start=max(0,int(item['page'])-1)
            end=min(len(doc),int(item['endPage']))
            lines=[]
            for pno in range(start,end):
                lines+=clean_lines(ptexts[pno])
            if not lines:
                print(f'FULL BOOK NOT PUBLISHED: no extractable text for {item["title"]}',file=sys.stderr)
                return False
            item['lines']=lines
            item['search']=search_blob({**item,'lines':lines})
            item['updated']=datetime.date.today().isoformat()
            item['sourceFile']=f'updates/published/current-protocol-book.pdf#page={item["page"]}'
    else:
        normpages=[norm(t) for t in ptexts]
        starts=[]
        missing=[]
        for item in data:
            needle=norm(item['title'])
            found=None
            for i,t in enumerate(normpages):
                if needle and needle in t[:1800]:
                    found=i
                    break
            if found is None:
                missing.append(item['id'])
            starts.append(found)

        if missing:
            print('FULL BOOK NOT PUBLISHED. Could not confidently locate:')
            for x in missing:
                print(' -',x)
            return False

        ordered=sorted((s,i) for i,s in enumerate(starts))
        next_start={i:(ordered[n+1][0] if n+1<len(ordered) else len(doc)) for n,(s,i) in enumerate(ordered)}
        for i,item in enumerate(data):
            s=starts[i]
            e=next_start[i]
            lines=[]
            for pno in range(s,e):
                lines+=clean_lines(ptexts[pno])
            item['lines']=lines
            item['page']=s+1
            item['endPage']=e
            item['updated']=datetime.date.today().isoformat()
            item['search']=search_blob({**item,'lines':lines})
            item['sourceFile']=f'updates/published/current-protocol-book.pdf#page={item["page"]}'

    shutil.copy2(path,CURRENT_BOOK)
    path.unlink()
    print('Published complete protocol book and rebuilt index.')
    return True

def main():
    data=json.loads(DATA.read_text())
    changed=False

    fp=FULL/'protocol-book.pdf'
    if fp.exists():
        changed=rebuild_full(data,fp) or changed

    for p in sorted(SINGLE.glob('*.pdf')):
        changed=replace_single(data,p) or changed

    if changed:
        DATA.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    else:
        print('No publishable protocol updates found.')

if __name__=='__main__':
    main()
