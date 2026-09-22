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

def norm(s):
    return re.sub(r'[^a-z0-9]+',' ',s.lower()).strip()

def search_blob(item):
    return (' '.join([item.get('title',''),*item.get('lines',[]),*item.get('aliases',[])])).lower()

def extract_pdf(path):
    d=fitz.open(path)
    return [clean_lines(p.get_text('text')) for p in d]

def detect_protocol(data,path,lines):
    # Exact ID filename is accepted, but not required.
    stem=path.stem.lower()
    direct=[x for x in data if x['id'].lower()==stem]
    if direct:
        return direct[0]

    text=norm(' '.join(lines))
    opening=norm(' '.join(lines[:45]))

    # Prefer an official protocol title appearing near the start of the upload.
    near=[x for x in data if norm(x['title']) and norm(x['title']) in opening]
    if near:
        near.sort(key=lambda x:len(norm(x['title'])),reverse=True)
        return near[0]

    # Fall back to title anywhere in the uploaded replacement.
    anywhere=[x for x in data if norm(x['title']) and norm(x['title']) in text]
    if anywhere:
        anywhere.sort(key=lambda x:len(norm(x['title'])),reverse=True)
        return anywhere[0]
    return None

def replace_single(data,path):
    pages=extract_pdf(path)
    lines=[x for pg in pages for x in pg]
    if not lines:
        print(f'ERROR: no extractable text in {path.name}',file=sys.stderr)
        return False

    item=detect_protocol(data,path,lines)
    if item is None:
        print(f'ERROR: could not identify which existing protocol {path.name} replaces. No changes published.',file=sys.stderr)
        return False

    dest=PUB/f'{item["id"]}.pdf'
    shutil.copy2(path,dest)
    item['lines']=lines
    item['search']=search_blob({**item,'lines':lines})
    item['sourceFile']=f'updates/published/{item["id"]}.pdf'
    item['updated']=datetime.date.today().isoformat()
    item['page']=1
    item['endPage']=len(pages)
    path.unlink()
    print(f'Published single-protocol update: {item["title"]}')
    return True

def rebuild_full(data,path):
    doc=fitz.open(path)
    ptexts=[p.get_text('text') for p in doc]
    bootstrap=all(not x.get('lines') for x in data)

    if bootstrap:
        # First publication uses the verified page map already stored in protocols.json.
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
        # Later complete books are re-indexed by official protocol title.
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
