#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_gallery.html", "r") as f:
    content = f.read()

old = '''async function fetchBatch(urls, coll) {
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

new = '''async function loadCollection(coll) {
  try {
    const r = await fetch(`http://127.0.0.1:8082/collection/${coll.slug}`);
    const data = await r.json();
    if (!data.tokens) return [];
    return data.tokens.map(t => ({
      ...t,
      token_id: t.token_id,
      _slug: coll.slug,
      _cls: coll.cls,
      _folder: coll.folder,
      _pad: coll.pad,
    }));
  } catch(e) {
    console.error("Collection load failed:", coll.slug, e);
    return [];
  }
}'''

if old not in content:
    print("ERROR: fetchBatch block not found")
    raise SystemExit(1)

content = content.replace(old, new, 1)

with open("/data/data/com.termux/files/home/omega_gallery.html", "w") as f:
    f.write(content)
print("Patch applied")
