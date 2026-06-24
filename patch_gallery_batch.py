#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_gallery.html", "r") as f:
    content = f.read()

# Fix 1: update stale API URL
content = content.replace(
    'const PROVENANCE_API = "https://observed-principal-leaves-reflected.trycloudflare.com";',
    'const PROVENANCE_API = "https://vaccine-maria-timber-offices.trycloudflare.com";'
)

# Fix 2: replace loadCollection with batched version
old = '''async function loadCollection(coll) {
  const tokens = [];
  const [start,end] = coll.range;
  const promises = [];
  for (let id=start; id<=end; id++) {
    const idStr = coll.pad ? String(id).padStart(coll.pad, '0') : String(id);
    promises.push(
      fetch(`${coll.folder}/metadata/${idStr}.json`)
        .then(r => r.ok ? r.json() : null)
        .then(meta => { if (meta) tokens.push({...meta, _slug:coll.slug, _cls:coll.cls, _folder:coll.folder, _pad:coll.pad}); })
        .catch(()=>{})
    );
  }
  await Promise.all(promises);
  return tokens;
}'''

new = '''async function fetchBatch(urls, coll) {
  const results = await Promise.all(urls.map(({id, idStr}) =>
    fetch(`${coll.folder}/metadata/${idStr}.json`)
      .then(r => r.ok ? r.json() : null)
      .then(meta => { if (meta) return {...meta, _slug:coll.slug, _cls:coll.cls, _folder:coll.folder, _pad:coll.pad}; return null; })
      .catch(() => null)
  ));
  return results.filter(Boolean);
}

async function loadCollection(coll) {
  const tokens = [];
  const [start,end] = coll.range;
  const BATCH = 10;
  const ids = [];
  for (let id=start; id<=end; id++) {
    const idStr = coll.pad ? String(id).padStart(coll.pad, '0') : String(id);
    ids.push({id, idStr});
  }
  for (let i=0; i<ids.length; i+=BATCH) {
    const batch = ids.slice(i, i+BATCH);
    const results = await fetchBatch(batch, coll);
    tokens.push(...results);
    if (i+BATCH < ids.length) await new Promise(r => setTimeout(r, 50));
  }
  return tokens;
}'''

if old not in content:
    print("ERROR: loadCollection block not found — check whitespace")
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_gallery.html", "w") as f:
    f.write(content)

print("Patch applied")
