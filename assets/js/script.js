/* Dashboard script:
   - modal handling with centered modals & blur overlay
   - profile save/load with picture (localStorage)
   - pantry CRUD with sample data (localStorage)
   - generate meal from ingredient selections
   - favorites + print + recent recipes
*/





/*
(() => {
  // helpers
  const $ = (s, ctx=document) => ctx.querySelector(s);
  const $$ = (s, ctx=document) => Array.from(ctx.querySelectorAll(s));
  const TOAST = $('#toast');
  const PROFILE_KEY = 'mp_profile_theme';
  const PANTRY_KEY = 'mp_pantry_theme';
  const RECENT_KEY = 'mp_recent_theme';
  const FAV_KEY = 'mp_fav_theme';

  function toast(msg, t=2200){
    if(!TOAST) return;
    TOAST.textContent = msg;
    TOAST.classList.add('show');
    setTimeout(()=> TOAST.classList.remove('show'), t);
  }

  // modal open/close
  function openModal(id){ const el = document.getElementById(id); if(!el) return; el.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; }
  function closeModal(id){ const el = document.getElementById(id); if(!el) return; el.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }

  // overlay click closes
  $$('.modal').forEach(m=> m.addEventListener('click', e => { if(e.target===m) closeModal(m.id); }));

  // close buttons
  $$('[data-close]').forEach(btn=>btn.addEventListener('click', ()=> closeModal(btn.getAttribute('data-close')) ));

  // ESC key closes
  document.addEventListener('keydown', e => { if(e.key === 'Escape') $$('.modal[aria-hidden="false"]').forEach(m=> closeModal(m.id)); });

  // initial UI bindings
  $('#btnOpenProfile')?.addEventListener('click', ()=> openModal('modalProfile'));
  $('#btnOpenGenerate')?.addEventListener('click', ()=> openModal('modalGenerate'));
  $('#btnManagePantry')?.addEventListener('click', ()=> openModal('modalPantry'));
  $('#btnOpenPantry')?.addEventListener('click', ()=> openModal('modalPantry'));
  $('#btnOpenFavorites')?.addEventListener('click', ()=> { renderFavorites(); openModal('modalFavorites'); } );
  $('#quickGenerate')?.addEventListener('click', ()=> { openModal('modalGenerate'); setTimeout(()=> { const cb = document.querySelector('#ingredientsGrid input'); if(cb) cb.checked=true; }, 120); });

/*   // ---------------- Profile ----------------
  let profileImageData = null;
  function loadProfile(){
    const raw = localStorage.getItem(PROFILE_KEY);
    if(!raw){
      $('#profileName').textContent = 'Guest';
      $('#avatar').textContent = 'G';
      $('#welcomeFirst').textContent = 'Chef';
      return;
    }
    try{
      const p = JSON.parse(raw);
      $('#profile_name').value = p.name || '';
      $('#profile_email').value = p.email || '';
      $('#profile_phone').value = p.phone || '';
      $('#profile_age').value = p.age || '';
      $('#profile_gender').value = p.gender || '';
      $('#profile_diet').value = p.diet || '';
      $('#profile_address').value = p.address || '';
      profileImageData = p.picture || null;
      if(profileImageData){
        $('#profile_thumb').innerHTML = `<img src="${profileImageData}" alt="avatar">`;
        $('#avatar').innerHTML = `<img src="${profileImageData}" style="width:100%;height:100%;object-fit:cover;border-radius:10px">`;
      } else {
        $('#profile_thumb').innerHTML = '';
        $('#avatar').textContent = (p.name ? p.name[0].toUpperCase() : 'G');
      }
      $('#profileName').textContent = p.name || 'Guest';
      $('#welcomeFirst').textContent = (p.name ? p.name.split(' ')[0] : 'Chef');
    } catch(e){ console.error('profile load', e); }
  }

  $('#profile_pic')?.addEventListener('change', e => {
    const f = e.target.files[0]; if(!f) return;
    const r = new FileReader();
    r.onload = ev => { profileImageData = ev.target.result; $('#profile_thumb').innerHTML = `<img src="${profileImageData}" alt="avatar">`; };
    r.readAsDataURL(f);
  });

  $('#profileForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const data = {
      name: $('#profile_name').value.trim(),
      email: $('#profile_email').value.trim(),
      phone: $('#profile_phone').value.trim(),
      age: $('#profile_age').value,
      gender: $('#profile_gender').value,
      diet: $('#profile_diet').value,
      address: $('#profile_address').value,
      picture: profileImageData
    };
    if(!data.name || !data.email){ toast('Please enter name and email.'); return; }
    localStorage.setItem(PROFILE_KEY, JSON.stringify(data));
    loadProfile();
    closeModal('modalProfile');
    toast('Profile saved');
  }); 
//----------------ediited editprofile js--------
  function openModal(id){
    const m = document.getElementById(id);
    if(m){ m.setAttribute('aria-hidden', 'false'); }
  }

  function closeModal(id){
    const m = document.getElementById(id);
    if(m){ m.setAttribute('aria-hidden', 'true'); }
  }


  // ---------------- Pantry ----------------
  function genId(){ return 'id_' + Math.random().toString(36).slice(2,9); }

  function seedPantry(){
    const sample = [
      { id: genId(), name: 'Tomato', qty: 2, unit: 'kg', expiry: '2025-08-20', category: 'Veggies', image: 'https://images.unsplash.com/photo-1542444459-db63d6b40b37?w=600&q=60' },
      { id: genId(), name: 'Milk', qty: 1, unit: 'l', expiry: '2025-08-10', category: 'Dairy', image: 'https://images.unsplash.com/photo-1582719478172-7d0b1b8f5b29?w=600&q=60' },
      { id: genId(), name: 'Chicken', qty: 0.5, unit: 'kg', expiry: '', category: 'Meat', image: '' }
    ];
    localStorage.setItem(PANTRY_KEY, JSON.stringify(sample));
    return sample;
  }

  let pantry = [];
  function loadPantry(){
    const raw = localStorage.getItem(PANTRY_KEY);
    if(!raw){ pantry = seedPantry(); } else {
      try{ pantry = JSON.parse(raw); } catch(e){ pantry = seedPantry(); }
    }
    renderPantryPreview();
    renderPantryGrid();
  }
  function savePantry(){ localStorage.setItem(PANTRY_KEY, JSON.stringify(pantry)); renderPantryPreview(); renderPantryGrid(); updateCounts(); }

  function renderPantryPreview(){
    const el = $('#pantryPreview'); el.innerHTML = '';
    pantry.slice(0,6).forEach(it=>{
      const d = document.createElement('div'); d.className='pantry-mini';
      d.innerHTML = `<strong>${it.name}</strong><div class="muted">${it.qty || '-'} ${it.unit || ''}</div>`;
      el.appendChild(d);
    });
  }

  function isNearExpiry(dateStr){
    if(!dateStr) return false;
    const d = new Date(dateStr); const now = new Date();
    const diff = (d - now)/(1000*60*60*24);
    return diff >= 0 && diff <= 7;
  }

  function renderPantryGrid(filter=null){
    const grid = $('#pantryGrid'); grid.innerHTML = '';
    const list = filter ? pantry.filter(p => p.category === filter) : pantry;
    if(!list.length){ grid.innerHTML = `<div class="muted">No items. Add some using the form.</div>`; return; }
    list.forEach(it => {
      const node = document.createElement('div'); node.className = 'pantry-card';
      node.innerHTML = `
        <img src="${it.image || 'https://via.placeholder.com/120?text=Food'}" alt="${it.name}" />
        <div class="pantry-meta">
          <strong>${it.name}</strong>
          <div class="muted">${it.qty} ${it.unit} • ${it.category}</div>
          <div style="margin-top:6px;font-size:12px;color:${isNearExpiry(it.expiry)?'#c23':'var(--muted)'}">${it.expiry? 'Expires: '+it.expiry : ''}</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <button class="btn" data-edit="${it.id}">Edit</button>
          <button class="btn" data-remove="${it.id}">Remove</button>
        </div>
      `;
      grid.appendChild(node);
    });

    grid.querySelectorAll('[data-edit]').forEach(b => b.addEventListener('click', () => openEditor(b.getAttribute('data-edit'))));
    grid.querySelectorAll('[data-remove]').forEach(b => b.addEventListener('click', () => {
      const id = b.getAttribute('data-remove');
      if(confirm('Remove this item?')){ pantry = pantry.filter(p => p.id !== id); savePantry(); toast('Removed'); }
    }));
  }

  $('#btnAddItem')?.addEventListener('click', ()=> { $('#pantryForm').reset(); $('#item_id').value = ''; $('#editorTitle').textContent = 'Add Item'; });

  function openEditor(id){
    const it = pantry.find(p => p.id === id); if(!it) return;
    $('#item_id').value = it.id;
    $('#item_name').value = it.name;
    $('#item_qty').value = it.qty;
    $('#item_unit').value = it.unit;
    $('#item_expiry').value = it.expiry;
    $('#item_category').value = it.category;
    $('#item_img').value = it.image || '';
    $('#editorTitle').textContent = 'Edit Item';
  }

  $('#pantryForm')?.addEventListener('submit', e => {
    e.preventDefault();
    const id = $('#item_id').value;
    const item = {
      id: id || genId(),
      name: $('#item_name').value.trim(),
      qty: parseFloat($('#item_qty').value) || 0,
      unit: $('#item_unit').value,
      expiry: $('#item_expiry').value,
      category: $('#item_category').value,
      image: $('#item_img').value.trim()
    };
    if(!item.name){ toast('Enter item name'); return; }
    if(id){ pantry = pantry.map(p => p.id === id ? item : p); toast('Item updated'); } else { pantry.unshift(item); toast('Item added'); }
    savePantry();
    $('#pantryForm').reset();
  });

  $('#btnRemoveItem')?.addEventListener('click', () => {
    const id = $('#item_id').value;
    if(!id){ toast('Select item first'); return; }
    if(confirm('Remove this item?')){ pantry = pantry.filter(p => p.id !== id); savePantry(); $('#pantryForm').reset(); $('#item_id').value=''; toast('Removed'); }
  });

  $('#btnFilterVeg')?.addEventListener('click', () => renderPantryGrid('Veggies'));
  $('#btnFilterAll')?.addEventListener('click', () => renderPantryGrid(null));

  // ---------------- Ingredients & Generate ----------------
  const INGREDIENTS = [
    {key:'Tomato', img:'https://images.unsplash.com/photo-1542444459-db63d6b40b37?w=600&q=60'},
    {key:'Potato', img:'https://images.unsplash.com/photo-1506806732259-39c2d0268443?w=600&q=60'},
    {key:'Chicken', img:'https://images.unsplash.com/photo-1606756791741-1af6d8f6a0b8?w=600&q=60'},
    {key:'Paneer', img:'https://images.unsplash.com/photo-1604908176923-9d4b45d4f6e6?w=600&q=60'},
    {key:'Spinach', img:'https://images.unsplash.com/photo-1518972559570-2f2a8d51b6a3?w=600&q=60'},
    {key:'Rice', img:'https://images.unsplash.com/photo-1573020645169-1ea3b6b8c4c3?w=600&q=60'},
    {key:'Egg', img:'https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=600&q=60'},
    {key:'Onion', img:'https://images.unsplash.com/photo-1544025162-d76694265947?w=600&q=60'},
    {key:'Milk', img:'https://images.unsplash.com/photo-1582719478172-7d0b1b8f5b29?w=600&q=60'}
  ];

  function renderIngredientsGrid(){
    const grid = $('#ingredientsGrid'); grid.innerHTML = '';
    INGREDIENTS.forEach((it, idx) => {
      const div = document.createElement('div'); div.className='ingredient';
      div.innerHTML = `<label><input type="checkbox" id="ing_${idx}" data-name="${it.key}" /> <img src="${it.img}" alt="${it.key}" /> <span>${it.key}</span></label>`;
      grid.appendChild(div);
      div.querySelector('label').addEventListener('click', e => {
        if(e.target.tagName === 'INPUT') return;
        const cb = div.querySelector('input');
        cb.checked = !cb.checked;
        div.classList.toggle('active', cb.checked);
      });
    });

    // also render same into modal ingredients
    const mgrid = $('#modalIngredientsGrid'); if(mgrid){ mgrid.innerHTML=''; INGREDIENTS.forEach((it, idx) => {
      const div = document.createElement('div'); div.className='ingredient';
      div.innerHTML = `<label><input type="checkbox" id="ming_${idx}" data-name="${it.key}" /> <img src="${it.img}" alt="${it.key}" /> <span>${it.key}</span></label>`;
      mgrid.appendChild(div);
      div.querySelector('label').addEventListener('click', e => {
        if(e.target.tagName === 'INPUT') return;
        const cb = div.querySelector('input');
        cb.checked = !cb.checked;
        div.classList.toggle('active', cb.checked);
      });
    }); }
  }

  // ---------------- Recipe generation ----------------
  let lastRecipe = null;
  function estimateNutrition(ingredients, servings){
    const kcal = Math.max(100, Math.round(ingredients.length * 160 / Math.max(1, servings)));
    const protein = Math.max(4, Math.round(ingredients.length * 4 / Math.max(1, servings)));
    return `~${kcal} kcal • Protein: ~${protein} g (per serving)`;
  }

  function buildInstructions(ingredients, mealType){
    if(!ingredients.length) return 'No instructions available.';
    const intro = `Prepare: ${ingredients.join(', ')}.`;
    const cook = mealType === 'Breakfast' ? 'Quickly sauté or scramble and serve.' :
                 mealType === 'Lunch' ? 'Cook on medium heat and serve with sides.' :
                 mealType === 'Dinner' ? 'Slow-cook for best flavor and serve warm.' :
                 'Cook to preference and serve.';
    return `${intro} ${cook}`;
  }

  $('#btnGenerate')?.addEventListener('click', () => {
    const selected = $$('#ingredientsGrid input[type="checkbox"]:checked').map(cb => cb.dataset.name);
    if(!selected.length){ toast('Select at least one ingredient'); return; }
    const mealType = $('#mealType').value;
    const servings = parseInt($('#servingSize').value) || 1;
    const title = `${mealType} • ${selected.slice(0,3).join(', ')}`;
    const instructions = buildInstructions(selected, mealType);
    const nutrition = estimateNutrition(selected, servings);
    const image = (INGREDIENTS.find(i=>i.key===selected[0]) || {}).img || '';
    const recipe = { id: genId(), title, ingredients: selected, instructions, nutrition, image, created: Date.now() };

    // store recent
    const recent = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    recent.unshift(recipe);
    localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, 10)));
    renderRecent();
    openRecipeModal(recipe);
  });

  $('#btnRegenerate')?.addEventListener('click', () => {
    const boxes = $$('#ingredientsGrid input[type="checkbox"]');
    boxes.forEach(b=>b.checked=false);
    const count = Math.max(1, Math.floor(Math.random()*4));
    const shuffled = INGREDIENTS.slice().sort(()=>Math.random()-0.5).slice(0,count);
    boxes.forEach(b => { if(shuffled.some(s=>s.key===b.dataset.name)) { b.checked=true; b.closest('.ingredient').classList.add('active'); } else b.closest('.ingredient').classList.remove('active'); });
  });

  // modal generate (from modal)
  $('#modalGenerateBtn')?.addEventListener('click', () => {
    const selected = $$('#modalIngredientsGrid input[type="checkbox"]:checked').map(cb => cb.dataset.name);
    if(!selected.length){ toast('Select at least one ingredient'); return; }
    const mealType = $('#modalMealType').value;
    const servings = parseInt($('#modalServingSize').value) || 1;
    const title = `${mealType} • ${selected.slice(0,3).join(', ')}`;
    const instructions = buildInstructions(selected, mealType);
    const nutrition = estimateNutrition(selected, servings);
    const image = (INGREDIENTS.find(i=>i.key===selected[0]) || {}).img || '';
    const recipe = { id: genId(), title, ingredients: selected, instructions, nutrition, image, created: Date.now() };

    const recent = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    recent.unshift(recipe);
    localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, 10)));
    renderRecent();
    closeModal('modalGenerate');
    openRecipeModal(recipe);
  });

  // ---------------- Recipe modal ----------------
  function openRecipeModal(recipe){
    lastRecipe = recipe;
    $('#recipeTitle').textContent = recipe.title;
    $('#recipeIngredients').innerHTML = recipe.ingredients.map(i => `<li>${i}</li>`).join('');
    $('#recipeInstr').textContent = recipe.instructions;
    $('#recipeNutrition').textContent = recipe.nutrition;
    $('#recipeImage').src = recipe.image || 'https://via.placeholder.com/800x400?text=Recipe';
    openModal('modalRecipe');
    renderFavorites(); // update
  }

  $('#btnPrint')?.addEventListener('click', () => {
    if(!lastRecipe) return;
    const html = `<html><head><title>${lastRecipe.title}</title></head><body><h1>${lastRecipe.title}</h1><img src="${lastRecipe.image}" style="max-width:100%"><h3>Ingredients</h3><ul>${lastRecipe.ingredients.map(i=>`<li>${i}</li>`).join('')}</ul><p>${lastRecipe.instructions}</p><p>${lastRecipe.nutrition}</p></body></html>`;
    const w = window.open('', '_blank'); w.document.write(html); w.document.close(); setTimeout(()=> w.print(), 500);
  });

  // favorites
  function getFavs(){ return JSON.parse(localStorage.getItem(FAV_KEY) || '[]'); }
  function saveFavs(a){ localStorage.setItem(FAV_KEY, JSON.stringify(a)); updateFavCount(); }

  $('#btnFav')?.addEventListener('click', () => {
    if(!lastRecipe) return;
    let favs = getFavs();
    const exists = favs.find(f => f.title === lastRecipe.title && JSON.stringify(f.ingredients) === JSON.stringify(lastRecipe.ingredients));
    if(exists){ favs = favs.filter(f => f.id !== exists.id); toast('Removed from favorites'); }
    else { favs.unshift(lastRecipe); toast('Added to favorites'); }
    saveFavs(favs);
    renderFavorites();
  });

  function renderFavorites(){
    const list = $('#favList'); if(!list) return;
    const favs = getFavs(); list.innerHTML = '';
    if(!favs.length){ list.innerHTML = '<div class="muted">No favorites yet.</div>'; return; }
    favs.forEach(f => {
      const card = document.createElement('div'); card.className = 'card'; card.style.marginBottom='8px';
      card.innerHTML = `<strong>${f.title}</strong><div class="muted" style="font-size:13px">${f.ingredients.join(', ')}</div>
        <div style="margin-top:8px"><button class="btn" data-open="${f.id}">Open</button> <button class="btn" data-rem="${f.id}">Remove</button></div>`;
      list.appendChild(card);
      card.querySelector('[data-open]')?.addEventListener('click', ()=> openRecipeModal(f));
      card.querySelector('[data-rem]')?.addEventListener('click', ()=> { saveFavs(getFavs().filter(x => x.id !== f.id)); renderFavorites(); });
    });
    $('#favCount').textContent = favs.length;
  }

  function updateFavCount(){ $('#favCount').textContent = getFavs().length; }

  // recent recipes
  function renderRecent(){
    const el = $('#recentList'); el.innerHTML = '';
    const recent = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
    if(!recent.length) { el.innerHTML = '<li class="muted">No recent recipes</li>'; $('#todayMeal').textContent = '—'; return; }
    recent.slice(0,6).forEach(r => {
      const li = document.createElement('li'); li.innerHTML = `<a href="#" class="recent-link">${r.title}</a>`; el.appendChild(li);
      li.querySelector('.recent-link').addEventListener('click', (ev) => { ev.preventDefault(); openRecipeModal(r); });
    });
    $('#todayMeal').textContent = recent[0] ? recent[0].title : '—';
  }

  // init
  function updateCounts(){ $('#pantryCount').textContent = pantry.length; updateFavCount(); }
  function renderPantryGridAll(){ renderPantryGrid(null); }
  function renderIngredients(){ renderIngredientsGrid(); /* copy to modal also const mg = $('#modalIngredientsGrid'); if(mg) mg.innerHTML = document.getElementById('ingredientsGrid').innerHTML; }

  // wire modal open for generate
  $('#btnOpenGenerate')?.addEventListener('click', () => { renderIngredients(); openModal('modalGenerate'); });
  $('#btnManagePantry')?.addEventListener('click', () => openModal('modalPantry'));

  // On load
  loadPantry();
  loadProfile();
  renderIngredientsGrid();
  renderRecent();
  renderFavorites();
  updateCounts();

  // small search highlight
  $('#searchInput')?.addEventListener('input', e => {
    const q = e.target.value.trim().toLowerCase();
    $$('#ingredientsGrid .ingredient').forEach(card => {
      const txt = card.textContent.toLowerCase();
      card.style.opacity = !q || txt.includes(q) ? '1' : '0.45';
    });
  });

  
})();
*/