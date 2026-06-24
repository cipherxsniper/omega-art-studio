#!/usr/bin/env python3
with open("/data/data/com.termux/files/home/omega_gallery.html", "r") as f:
    content = f.read()

# 1. Add cart CSS after existing styles
cart_css = '''
/* ── Cart ── */
#cart-icon{position:fixed;top:16px;right:16px;z-index:1000;background:#1C1612;border:1px solid #C9A84C;border-radius:50%;width:44px;height:44px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:18px;}
#cart-badge{position:absolute;top:-6px;right:-6px;background:#C9A84C;color:#0D0B0E;border-radius:50%;width:18px;height:18px;font-size:10px;font-weight:bold;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;}
#cart-drawer{position:fixed;top:0;right:-420px;width:400px;height:100vh;background:#13100F;border-left:1px solid #C9A84C;z-index:999;transition:right 0.3s ease;overflow-y:auto;padding:20px;}
#cart-drawer.open{right:0;}
#cart-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:998;display:none;}
#cart-overlay.open{display:block;}
.cart-header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #C9A84C;padding-bottom:12px;margin-bottom:16px;}
.cart-title{font-family:'JetBrains Mono',monospace;color:#C9A84C;font-size:13px;letter-spacing:2px;text-transform:uppercase;}
.cart-close{background:none;border:none;color:#C9A84C;font-size:20px;cursor:pointer;padding:0;}
.cart-item{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #2a1f15;}
.cart-item-info{flex:1;}
.cart-item-title{color:#F0E6D3;font-size:12px;font-weight:bold;}
.cart-item-sub{color:#8B7355;font-size:10px;font-family:'JetBrains Mono',monospace;margin-top:2px;}
.cart-item-price{color:#C9A84C;font-size:13px;font-weight:bold;font-family:'JetBrains Mono',monospace;}
.cart-item-remove{background:none;border:none;color:#8B7355;cursor:pointer;font-size:16px;padding:0 4px;}
.cart-item-remove:hover{color:#C9A84C;}
.cart-total{padding:16px 0;border-top:1px solid #C9A84C;margin-top:8px;display:flex;justify-content:space-between;align-items:center;}
.cart-total-label{color:#8B7355;font-size:11px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;}
.cart-total-amount{color:#C9A84C;font-size:18px;font-weight:bold;font-family:'JetBrains Mono',monospace;}
.cart-checkout-btn{display:block;width:100%;padding:12px;background:#C9A84C;color:#0D0B0E;border:none;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:bold;cursor:pointer;margin-top:12px;font-family:'JetBrains Mono',monospace;}
.cart-checkout-btn:hover{background:#a8883e;}
.cart-empty{text-align:center;color:#8B7355;font-size:12px;padding:40px 0;font-style:italic;}
.sold-overlay{position:absolute;inset:0;background:rgba(13,11,14,.7);display:flex;align-items:center;justify-content:center;border-radius:10px;}
.sold-badge{background:#1C1612;border:1px solid #8B7355;color:#8B7355;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:3px;padding:6px 14px;text-transform:uppercase;}
.in-cart-badge{position:absolute;bottom:32px;left:6px;right:6px;background:rgba(201,168,76,.9);color:#0D0B0E;font-size:9px;font-family:'JetBrains Mono',monospace;letter-spacing:1px;text-align:center;padding:3px;border-radius:2px;}
'''

# Insert cart CSS before closing </style>
if '</style>' not in content:
    print("ERROR: </style> not found")
    raise SystemExit(1)
content = content.replace('</style>', cart_css + '</style>', 1)

# 2. Add cart HTML before closing </body>
cart_html = '''
<!-- Cart Icon -->
<div id="cart-icon" onclick="toggleCart()">
  🛒
  <div id="cart-badge" style="display:none;">0</div>
</div>

<!-- Cart Overlay -->
<div id="cart-overlay" onclick="toggleCart()"></div>

<!-- Cart Drawer -->
<div id="cart-drawer">
  <div class="cart-header">
    <div class="cart-title">Your Collection</div>
    <button class="cart-close" onclick="toggleCart()">✕</button>
  </div>
  <div id="cart-items"></div>
  <div id="cart-footer" style="display:none;">
    <div class="cart-total">
      <div class="cart-total-label">Total</div>
      <div class="cart-total-amount" id="cart-total">$0</div>
    </div>
    <button class="cart-checkout-btn" onclick="checkout()">Checkout →</button>
  </div>
</div>
'''
content = content.replace('</body>', cart_html + '</body>', 1)

# 3. Add cart JavaScript before closing </script>
cart_js = '''
// ── Cart Logic ──
const PRICE_MAP = {
  "Impossible Diamond": 2500,
  "Black Diamond": 500,
  "Super Rare": 150,
  "Rare": 75,
  "Medium": 35,
  "Common": 15
};

let cart = JSON.parse(localStorage.getItem('omega_cart') || '[]');

function saveCart() {
  localStorage.setItem('omega_cart', JSON.stringify(cart));
  updateCartUI();
}

function addToCart(tokenId, collection, title, rarity, stripeLink) {
  const key = collection + '_' + tokenId;
  if (cart.find(i => i.key === key)) return;
  cart.push({key, tokenId, collection, title, rarity, stripeLink});
  saveCart();
  updateCardStates();
}

function removeFromCart(key) {
  cart = cart.filter(i => i.key !== key);
  saveCart();
  updateCardStates();
}

function toggleCart() {
  document.getElementById('cart-drawer').classList.toggle('open');
  document.getElementById('cart-overlay').classList.toggle('open');
}

function updateCartUI() {
  const badge = document.getElementById('cart-badge');
  const itemsEl = document.getElementById('cart-items');
  const footer = document.getElementById('cart-footer');
  const totalEl = document.getElementById('cart-total');

  if (cart.length === 0) {
    badge.style.display = 'none';
    itemsEl.innerHTML = '<div class="cart-empty">Your collection is empty</div>';
    footer.style.display = 'none';
    return;
  }

  badge.style.display = 'flex';
  badge.textContent = cart.length;

  let total = 0;
  itemsEl.innerHTML = cart.map(item => {
    const price = PRICE_MAP[item.rarity] || 15;
    total += price;
    return '<div class="cart-item">' +
      '<div class="cart-item-info">' +
        '<div class="cart-item-title">' + item.title + '</div>' +
        '<div class="cart-item-sub">' + item.collection + ' #' + String(item.tokenId).padStart(4,'0') + ' · ' + item.rarity + '</div>' +
      '</div>' +
      '<div class="cart-item-price">$' + price.toLocaleString() + '</div>' +
      '<button class="cart-item-remove" onclick="removeFromCart(\'' + item.key + '\')">✕</button>' +
    '</div>';
  }).join('');

  totalEl.textContent = '$' + total.toLocaleString();
  footer.style.display = 'block';
}

function checkout() {
  if (cart.length === 0) return;
  cart.forEach((item, i) => {
    setTimeout(() => { window.open(item.stripeLink, '_blank'); }, i * 400);
  });
}

function updateCardStates() {
  document.querySelectorAll('.card-wrap').forEach(card => {
    const inCartBadge = card.querySelector('.in-cart-badge');
    if (inCartBadge) inCartBadge.remove();
  });
  cart.forEach(item => {
    const cards = document.querySelectorAll('.card-wrap');
    cards.forEach(card => {
      const back = card.querySelector('.face-back');
      if (back && back.innerHTML.includes(item.collection + ' #' + String(item.tokenId).padStart(4,'0'))) {
        const front = card.querySelector('.face-front');
        if (front && !front.querySelector('.in-cart-badge')) {
          const badge = document.createElement('div');
          badge.className = 'in-cart-badge';
          badge.textContent = 'IN CART';
          front.appendChild(badge);
        }
      }
    });
  });
}

// Init cart on load
updateCartUI();
'''

content = content.replace('</script>', cart_js + '\n</script>', 1)

# 4. Fix card back button — replace Add to Cart anchor with cart function
old_btn = """(t.stripe_payment_link ?
              '<a href="' + t.stripe_payment_link + '" target="_blank" style="display:block;text-align:center;background:#C9A84C;color:#0D0B0E;padding:8px;font-size:10px;letter-spacing:2px;text-decoration:none;font-weight:bold;text-transform:uppercase;border-radius:2px;">Add to Cart · ' + ({"Impossible Diamond":"$2,500","Black Diamond":"$500","Super Rare":"$150","Rare":"$75","Medium":"$35","Common":"$15"}[t.rarity]||"$15") + '</a>'
              : '<div style="text-align:center;color:#8B7355;font-size:9px;">Not for sale</div>'
            )"""

new_btn = """(t.sale_status === 'sold' ?
              '<div style="text-align:center;background:#1C1612;border:1px solid #8B7355;color:#8B7355;padding:8px;font-size:10px;letter-spacing:2px;font-family:\\'JetBrains Mono\\',monospace;">SOLD</div>'
              : t.is_founder_linked ?
              '<div style="text-align:center;color:#8B7355;font-size:9px;font-style:italic;">Founder Held · Not For Sale</div>'
              : t.stripe_payment_link ?
              '<button onclick="event.stopPropagation();addToCart(' + t.token_id + ',\\''+t.collection+'\\',\\''+t.title+'\\',\\''+t.rarity+'\\',\\''+t.stripe_payment_link+'\\')" style="display:block;width:100%;background:#C9A84C;color:#0D0B0E;padding:8px;font-size:10px;letter-spacing:2px;font-weight:bold;text-transform:uppercase;border:none;cursor:pointer;font-family:\\'JetBrains Mono\\',monospace;">Add to Cart · ' + ({"Impossible Diamond":"$2,500","Black Diamond":"$500","Super Rare":"$150","Rare":"$75","Medium":"$35","Common":"$15"}[t.rarity]||"$15") + '</button>'
              : '<div style="text-align:center;color:#8B7355;font-size:9px;">Not available</div>'
            )"""

if old_btn not in content:
    print("ERROR: button block not found")
    raise SystemExit(1)

content = content.replace(old_btn, new_btn, 1)

# 5. Add sold overlay on card front
old_front = "'<div class=\"rarity-tag\">' + (t.rarity||'?') + '</div>' +"
new_front = "'<div class=\"rarity-tag\">' + (t.rarity||'?') + '</div>' +" + """
          (t.sale_status === 'sold' ? '<div class=\"sold-overlay\"><div class=\"sold-badge\">Sold</div></div>' : '') +"""

if old_front not in content:
    print("ERROR: rarity-tag line not found")
    raise SystemExit(1)

content = content.replace(old_front, new_front, 1)

with open("/data/data/com.termux/files/home/omega_gallery.html", "w") as f:
    f.write(content)
print("Patch applied")
