#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_gallery.html", "r") as f:
    content = f.read()

old_btn = """            (t.stripe_payment_link ?
              '<a href="' + t.stripe_payment_link + '" target="_blank" style="display:block;text-align:center;background:#C9A84C;color:#0D0B0E;padding:8px;font-size:10px;letter-spacing:2px;text-decoration:none;font-weight:bold;text-transform:uppercase;border-radius:2px;">Purchase · ' + ({"Impossible Diamond":"$2,500","Black Diamond":"$500","Super Rare":"$150","Rare":"$75","Medium":"$35","Common":"$15"}[t.rarity]||"$15") + '</a>'
              : '<div style="text-align:center;color:#8B7355;font-size:9px;">Not for sale</div>'
            )"""

new_btn = """            (t.sale_status === 'sold' ?
              '<div style="text-align:center;background:#1C1612;border:1px solid #8B7355;color:#8B7355;padding:8px;font-size:10px;letter-spacing:2px;font-family:\\'JetBrains Mono\\',monospace;">SOLD</div>'
              : t.is_founder_linked ?
              '<div style="text-align:center;color:#8B7355;font-size:9px;font-style:italic;">Founder Held · Not For Sale</div>'
              : t.stripe_payment_link ?
              '<button onclick="event.stopPropagation();addToCart(' + t.token_id + ',\\''+t.collection+'\\',\\''+t.title+'\\',\\''+t.rarity+'\\',\\''+t.stripe_payment_link+'\\')" style="display:block;width:100%;background:#C9A84C;color:#0D0B0E;padding:8px;font-size:10px;letter-spacing:2px;font-weight:bold;text-transform:uppercase;border:none;cursor:pointer;font-family:\\'JetBrains Mono\\',monospace;">Add to Cart · ' + ({"Impossible Diamond":"$2,500","Black Diamond":"$500","Super Rare":"$150","Rare":"$75","Medium":"$35","Common":"$15"}[t.rarity]||"$15") + '</button>'
              : '<div style="text-align:center;color:#8B7355;font-size:9px;">Not available</div>'
            )"""

if old_btn not in content:
    print("ERROR: not found — showing lines 132-138")
    lines = content.split('\n')
    for i,l in enumerate(lines[131:138], 132):
        print(f"{i}: {repr(l)}")
    raise SystemExit(1)

content = content.replace(old_btn, new_btn, 1)

# Add cart CSS before </style>
cart_css = '''
#cart-icon{position:fixed;top:16px;right:16px;z-index:1000;background:#1C1612;border:1px solid #C9A84C;border-radius:50%;width:44px;height:44px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:20px;}
#cart-badge{position:absolute;top:-6px;right:-6px;background:#C9A84C;color:#0D0B0E;border-radius:50%;width:18px;height:18px;font-size:10px;font-weight:bold;display:flex;align-items:center;justify-content:center;}
#cart-drawer{position:fixed;top:0;right:-420px;width:380px;height:100vh;background:#13100F;border-left:1px solid #C9A84C;z-index:999;transition:right 0.3s ease;overflow-y:auto;padding:20px;box-sizing:border-box;}
#cart-drawer.open{right:0;}
#cart-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:998;display:none;}
#cart-overlay.open{display:block;}
.cart-header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #C9A84C;padding-bottom:12px;margin-bottom:16px;}
.cart-title{font-family:'JetBrains Mono',monospace;color:#C9A84C;font-size:12px;letter-spacing:2px;text-transform:uppercase;}
.cart-close{background:none;border:none;color:#C9A84C;font-size:20px;cursor:pointer;}
.cart-item{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #2a1f15;align-items:center;}
.cart-item-info{flex:1;}
.cart-item-title{color:#F0E6D3;font-size:11px;font-weight:bold;}
.cart-item-sub{color:#8B7355;font-size:9px;font-family:'JetBrains Mono',monospace;margin-top:2px;}
.cart-item-price{color:#C9A84C;font-size:12px;font-weight:bold;font-family:'JetBrains Mono',monospace;white-space:nowrap;}
.cart-remove{background:none;border:none;color:#8B7355;cursor:pointer;font-size:16px;}
.cart-remove:hover{color:#C9A84C;}
.cart-total-row{display:flex;justify-content:space-between;padding:14px 0;border-top:1px solid #C9A84C;margin-top:8px;}
.cart-total-label{color:#8B7355;font-size:11px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;}
.cart-total-amt{color:#C9A84C;font-size:16px;font-weight:bold;font-family:'JetBrains Mono',monospace;}
.checkout-btn{display:block;width:100%;padding:12px;background:#C9A84C;color:#0D0B0E;border:none;font-size:11px;letter-spacing:2px;text-transform:uppercase;font-weight:bold;cursor:pointer;margin-top:10px;font-family:'JetBrains Mono',monospace;}
.checkout-btn:hover{background:#a8883e;}
.cart-empty{text-align:center;color:#8B7355;font-size:11px;padding:40px 0;font-style:italic;}
.sold-overlay{position:absolute;inset:0;background:rgba(13,11,14,.75);display:flex;align-items:center;justify-content:center;border-radius:10px;pointer-events:none;}
.sold-badge{border:1px solid #8B7355;color:#8B7355;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:3px;padding:5px 12px;text-transform:uppercase;}
.in-cart-tag{position:absolute;bottom:32px;left:6px;right:6px;background:rgba(201,168,76,.9);color:#0D0B0E;font-size:8px;font-family:'JetBrains Mono',monospace;letter-spacing:1px;text-align:center;padding:3px;border-radius:2px;pointer-events:none;}
'''
content = content.replace('</style>', cart_css + '</style>', 1)

# Add cart HTML before </body>
cart_html = '''
<div id="cart-icon" onclick="toggleCart()">🛒<span id="cart-badge" style="display:none;">0</span></div>
<div id="cart-overlay" onclick="toggleCart()"></div>
<div id="cart-drawer">
  <div class="cart-header">
    <div class="cart-title">Your Collection</div>
    <button class="cart-close" onclick="toggleCart()">✕</button>
  </div>
  <div id="cart-items"><div class="cart-empty">Your collection is empty</div></div>
  <div id="cart-footer" style="display:none;">
    <div class="cart-total-row">
      <div class="cart-total-label">Total</div>
      <div class="cart-total-amt" id="cart-total">$0</div>
    </div>
    <button class="checkout-btn" onclick="checkout()">Checkout →</button>
  </div>
</div>
'''
content = content.replace('</body>', cart_html + '</body>', 1)

# Add cart JS before </script>
cart_js = '''
const PRICES={"Impossible Diamond":2500,"Black Diamond":500,"Super Rare":150,"Rare":75,"Medium":35,"Common":15};
let cart=JSON.parse(localStorage.getItem('omega_cart')||'[]');

function saveCart(){localStorage.setItem('omega_cart',JSON.stringify(cart));renderCart();}

function addToCart(tokenId,collection,title,rarity,stripeLink){
  const key=collection+'_'+tokenId;
  if(cart.find(i=>i.key===key)){toggleCart();return;}
  cart.push({key,tokenId,collection,title,rarity,stripeLink});
  saveCart();
  toggleCart();
}

function removeFromCart(key){cart=cart.filter(i=>i.key!==key);saveCart();}

function toggleCart(){
  document.getElementById('cart-drawer').classList.toggle('open');
  document.getElementById('cart-overlay').classList.toggle('open');
}

function renderCart(){
  const badge=document.getElementById('cart-badge');
  const items=document.getElementById('cart-items');
  const footer=document.getElementById('cart-footer');
  const total=document.getElementById('cart-total');
  badge.style.display=cart.length?'flex':'none';
  badge.textContent=cart.length;
  if(!cart.length){items.innerHTML='<div class="cart-empty">Your collection is empty</div>';footer.style.display='none';return;}
  let sum=0;
  items.innerHTML=cart.map(item=>{
    const p=PRICES[item.rarity]||15;sum+=p;
    return '<div class="cart-item"><div class="cart-item-info"><div class="cart-item-title">'+item.title+'</div><div class="cart-item-sub">'+item.collection+' #'+String(item.tokenId).padStart(4,'0')+' · '+item.rarity+'</div></div><div class="cart-item-price">$'+p.toLocaleString()+'</div><button class="cart-remove" onclick="removeFromCart(\\''+item.key+'\\')">✕</button></div>';
  }).join('');
  total.textContent='$'+sum.toLocaleString();
  footer.style.display='block';
}

function checkout(){
  if(!cart.length)return;
  cart.forEach((item,i)=>setTimeout(()=>window.open(item.stripeLink,'_blank'),i*500));
}

renderCart();
'''
content = content.replace('</script>', cart_js + '\n</script>', 1)

# Add sold overlay on card front
old_rarity = "'<div class=\"rarity-tag\">' + (t.rarity||'?') + '</div>' +"
new_rarity = "'<div class=\"rarity-tag\">' + (t.rarity||'?') + '</div>' +" + \
    "\n          (t.sale_status==='sold'?'<div class=\"sold-overlay\"><div class=\"sold-badge\">Sold</div></div>':'') +"

if old_rarity in content:
    content = content.replace(old_rarity, new_rarity, 1)
    print("Sold overlay added")
else:
    print("WARNING: rarity-tag not found for sold overlay")

with open("/data/data/com.termux/files/home/omega_gallery.html", "w") as f:
    f.write(content)
print("Cart patch applied")
