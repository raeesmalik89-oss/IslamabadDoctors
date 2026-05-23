// ── REAL-TIME DATA LOADER ──
// Tries to fetch fresh doctors.json (built by scraper.py / GitHub Actions).
// Falls back to the static `doctors` array in data.js if the file isn't ready yet.

let _dataLastUpdated = null;

async function loadLiveData() {
  try {
    const res = await fetch('doctors.json?_=' + Date.now());
    if (!res.ok) throw new Error('No live data yet');
    const json = await res.json();
    if (Array.isArray(json.doctors) && json.doctors.length > 0) {
      // Merge: live data takes priority; keep any local entries not in live set
      const liveIds = new Set(json.doctors.map(d => d.id));
      const localOnly = doctors.filter(d => !liveIds.has(d.id));
      // Replace the global `doctors` array in-place (data.js declared it with const/var)
      doctors.length = 0;
      json.doctors.forEach(d => doctors.push(d));
      localOnly.forEach(d => doctors.push(d));
      _dataLastUpdated = json.updated || null;
      console.log(`✅ Live data loaded: ${json.doctors.length} doctors (updated ${_dataLastUpdated})`);
    }
  } catch {
    console.log('ℹ️  Using static data.js (run scraper.py to enable live data)');
  }
}

// ── INIT ──
document.addEventListener('DOMContentLoaded', async () => {
  const page = document.body.dataset.page || detectPage();
  await loadLiveData();         // fetch live JSON before rendering
  if (page === 'index') initIndex();
  if (page === 'doctors') initDoctors();
  setMinDate();
  showDataBadge();
});

function detectPage() {
  return location.pathname.includes('doctors') ? 'doctors' : 'index';
}

// ── LIVE DATA BADGE ──
function showDataBadge() {
  const badge = document.getElementById('liveDataBadge');
  if (!badge) return;
  if (_dataLastUpdated) {
    const d = new Date(_dataLastUpdated);
    const ago = timeSince(d);
    badge.innerHTML = `🟢 Live data · ${doctors.length} doctors · Updated ${ago}`;
    badge.style.display = 'inline-block';
  } else {
    badge.innerHTML = `⚪ Static data · ${doctors.length} doctors`;
    badge.style.display = 'inline-block';
  }
}

function timeSince(date) {
  const sec = Math.floor((new Date() - date) / 1000);
  if (sec < 60) return 'just now';
  const min = Math.floor(sec / 60);
  if (min < 60) return min + 'm ago';
  const hr = Math.floor(min / 60);
  if (hr < 24) return hr + 'h ago';
  return Math.floor(hr / 24) + 'd ago';
}

function setMinDate() {
  const d = document.getElementById('bookingDate');
  if (d) d.min = new Date().toISOString().split('T')[0];
}

// ── INDEX PAGE ──
function initIndex() {
  renderSpecialties();
  renderFeaturedDoctors();
  populateAreaSelect('heroArea');
}

function renderSpecialties() {
  const grid = document.getElementById('specialtiesGrid');
  if (!grid) return;
  grid.innerHTML = specialties.map(s => `
    <a class="specialty-card" href="doctors.html?specialty=${encodeURIComponent(s.name)}">
      <div class="sp-icon">${s.icon}</div>
      <div class="sp-name">${s.name}</div>
      <div class="sp-count">${s.count} doctors</div>
    </a>
  `).join('');
}

function renderFeaturedDoctors() {
  const grid = document.getElementById('featuredDoctors');
  if (!grid) return;
  const top = [...doctors].sort((a, b) => b.rating - a.rating).slice(0, 6);
  grid.innerHTML = top.map(d => doctorCardHTML(d)).join('');
}

function sourceBadge(d) {
  const sourceMap = {
    'Marham':        { color: '#0ea5e9', url: 'https://www.marham.pk/doctors/islamabad' },
    'Oladoc':        { color: '#7c3aed', url: 'https://oladoc.com/pakistan/islamabad/doctors' },
    'InstaCare':     { color: '#16a34a', url: 'https://instacare.pk/doctors/islamabad' },
    'Shifa Hospital':{ color: '#1d4ed8', url: 'https://www.shifa.com.pk/find-a-doctor/' },
    'Kulsum Hospital':{ color: '#15803d', url: 'https://kih.com.pk/find-a-doctor/' },
    'AIH':           { color: '#7e22ce', url: 'https://aih.com.pk/advanced-internaional-hospital-all-doctors/' },
  };
  if (!d.source) return '';
  const s = sourceMap[d.source] || { color: '#6b7280', url: '#' };
  const link = d.profileUrl || s.url;
  return `<a class="source-badge" href="${link}" target="_blank" rel="noopener"
    style="background:${s.color}20;color:${s.color};border:1px solid ${s.color}40"
    onclick="event.stopPropagation()">↗ ${d.source}</a>`;
}

function doctorCardHTML(d) {
  const fee = d.fee > 0 ? `PKR ${d.fee.toLocaleString()} <span>/ visit</span>` : `<span style="color:var(--text-muted)">Fee on request</span>`;
  const rating = d.rating > 0 ? `★ ${d.rating}` : '★ —';
  const exp = d.experience > 0 ? `${d.experience} yrs exp` : 'Experienced';
  return `
    <div class="doctor-card" onclick="openBooking(${d.id})">
      <div class="doctor-card-top">
        <img class="doctor-avatar" src="${d.photo}" alt="${d.name}" />
        <div class="doctor-info">
          <h3>${d.name}</h3>
          <div class="doctor-specialty">${d.specialty}</div>
          <div class="doctor-qual">${d.qualification}</div>
          <span class="badge-avail ${d.available ? 'yes' : 'no'}">
            ${d.available ? '● Available Today' : '● Next: ' + d.nextSlot}
          </span>
        </div>
      </div>
      <div class="doctor-meta">
        <span><span class="rating">${rating}</span> (${d.reviews})</span>
        <span>🏥 ${exp}</span>
        <span>📍 ${d.area}</span>
      </div>
      <div class="doctor-tags">${d.tags.slice(0,3).map(t => `<span class="tag">${t}</span>`).join('')}${sourceBadge(d)}</div>
      <div class="doctor-card-footer">
        <div class="doctor-fee">${fee}</div>
        <button class="btn-primary" onclick="event.stopPropagation();openBooking(${d.id})">Book Now</button>
      </div>
    </div>
  `;
}

function searchDoctors() {
  const q = document.getElementById('heroSearch')?.value.trim() || '';
  const area = document.getElementById('heroArea')?.value || '';
  const gender = document.getElementById('heroGender')?.value || '';
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (area) params.set('area', area);
  if (gender) params.set('gender', gender);
  location.href = 'doctors.html?' + params.toString();
}

// ── DOCTORS PAGE ──
function initDoctors() {
  populateAreaSelect('filterArea');
  populateSpecialtySelect('filterSpecialty');
  populateSidebarSpecialties();

  const params = new URLSearchParams(location.search);
  if (params.get('q')) document.getElementById('searchInput').value = params.get('q');
  if (params.get('specialty')) document.getElementById('filterSpecialty').value = params.get('specialty');
  if (params.get('area')) document.getElementById('filterArea').value = params.get('area');
  if (params.get('gender')) document.getElementById('filterGender').value = params.get('gender');

  filterDoctors();
}

function populateAreaSelect(id) {
  const sel = document.getElementById(id);
  if (!sel) return;
  areas.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a === 'All Areas' ? '' : a;
    opt.textContent = a;
    sel.appendChild(opt);
  });
}

function populateSpecialtySelect(id) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const unique = [...new Set(doctors.map(d => d.specialty))].sort();
  unique.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s; opt.textContent = s;
    sel.appendChild(opt);
  });
}

function populateSidebarSpecialties() {
  const div = document.getElementById('sidebarSpecialties');
  if (!div) return;
  const unique = [...new Set(doctors.map(d => d.specialty))].sort();
  div.innerHTML = unique.map(s => `
    <label class="checkbox-label">
      <input type="checkbox" value="${s}" class="sp-check" onchange="filterDoctors()" />
      ${s}
    </label>
  `).join('');
}

function filterDoctors() {
  const q = (document.getElementById('searchInput')?.value || '').toLowerCase();
  const specialty = document.getElementById('filterSpecialty')?.value || '';
  const area = document.getElementById('filterArea')?.value || '';
  const gender = document.getElementById('filterGender')?.value || '';
  const availOnly = document.getElementById('availToday')?.checked || false;
  const maxFee = parseInt(document.getElementById('feeRange')?.value || 5000);
  const sortVal = document.getElementById('sortBy')?.value || 'rating';
  const sidebarGender = document.querySelector('input[name="sgender"]:checked')?.value || '';

  const checkedSpecialties = [...document.querySelectorAll('.sp-check:checked')].map(c => c.value);

  let filtered = doctors.filter(d => {
    if (q && !d.name.toLowerCase().includes(q) &&
        !d.specialty.toLowerCase().includes(q) &&
        !d.tags.some(t => t.toLowerCase().includes(q)) &&
        !d.clinic.toLowerCase().includes(q)) return false;
    if (specialty && d.specialty !== specialty) return false;
    if (area && d.area !== area) return false;
    if (gender && d.gender !== gender) return false;
    if (sidebarGender && d.gender !== sidebarGender) return false;
    if (availOnly && !d.available) return false;
    if (d.fee > maxFee && maxFee < 5000) return false;
    if (checkedSpecialties.length && !checkedSpecialties.includes(d.specialty)) return false;
    return true;
  });

  filtered.sort((a, b) => {
    if (sortVal === 'rating') return b.rating - a.rating;
    if (sortVal === 'fee_asc') return a.fee - b.fee;
    if (sortVal === 'fee_desc') return b.fee - a.fee;
    if (sortVal === 'experience') return b.experience - a.experience;
    return 0;
  });

  renderDoctorList(filtered);
}

function renderDoctorList(list) {
  const container = document.getElementById('doctorsList');
  const noRes = document.getElementById('noResults');
  const count = document.getElementById('resultsCount');
  if (!container) return;

  if (list.length === 0) {
    container.innerHTML = '';
    noRes.style.display = 'block';
    count.textContent = '0 doctors found';
    return;
  }
  noRes.style.display = 'none';
  count.textContent = `${list.length} doctor${list.length !== 1 ? 's' : ''} found`;

  container.innerHTML = list.map(d => {
    const listFee = d.fee > 0 ? `PKR ${d.fee.toLocaleString()} <small>/ visit</small>` : `<small style="color:var(--text-muted)">Fee on request</small>`;
    const listRating = d.rating > 0 ? `★ ${d.rating}` : '★ —';
    const listExp = d.experience > 0 ? `${d.experience} yrs experience` : 'Experienced specialist';
    const viewBtn = d.profileUrl
      ? `<a class="btn-outline" href="${d.profileUrl}" target="_blank" rel="noopener" onclick="event.stopPropagation()">View Profile ↗</a>`
      : `<button class="btn-outline" onclick="event.stopPropagation();showDoctorDetails(${d.id})">View Profile</button>`;
    return `
    <div class="doctor-list-card" onclick="openBooking(${d.id})">
      <img class="list-avatar" src="${d.photo}" alt="${d.name}" />
      <div class="list-info">
        <h3>${d.name} ${sourceBadge(d)}</h3>
        <div class="list-specialty">${d.specialty}</div>
        <div class="list-qual">${d.qualification}</div>
        <div class="list-meta">
          <span><span class="rating">${listRating}</span> (${d.reviews} reviews)</span>
          <span>🏥 ${listExp}</span>
          <span>📍 ${d.area}</span>
          ${d.timings ? `<span>🕐 ${d.timings}</span>` : ''}
        </div>
        <div class="list-tags">${d.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>
      </div>
      <div class="list-actions">
        <div>
          <div class="list-fee">${listFee}</div>
          <div class="next-slot">${d.available ? '✅ Available Today' : '⏰ Next: ' + d.nextSlot}</div>
        </div>
        <button class="btn-primary" onclick="event.stopPropagation();openBooking(${d.id})">Book Now</button>
        ${viewBtn}
      </div>
    </div>
  `;}).join('');
}

function updateFeeLabel(val) {
  const el = document.getElementById('feeVal');
  if (el) el.textContent = val >= 5000 ? '5,000+' : 'PKR ' + parseInt(val).toLocaleString();
}

function resetFilters() {
  ['searchInput','filterSpecialty','filterArea','filterGender','filterAvail','sortBy'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = el.tagName === 'SELECT' && id === 'sortBy' ? 'rating' : '';
  });
  const feeRange = document.getElementById('feeRange');
  if (feeRange) { feeRange.value = 5000; updateFeeLabel(5000); }
  const availToday = document.getElementById('availToday');
  if (availToday) availToday.checked = false;
  document.querySelectorAll('.sp-check').forEach(c => c.checked = false);
  const anyGender = document.querySelector('input[name="sgender"][value=""]');
  if (anyGender) anyGender.checked = true;
  filterDoctors();
}

// ── BOOKING MODAL ──
let currentDoctorId = null;

function openBooking(id) {
  currentDoctorId = id;
  const d = doctors.find(x => x.id === id);
  if (!d) return;
  const info = document.getElementById('bookingDoctorInfo');
  if (info) {
    info.innerHTML = `
      <div class="booking-doctor-mini">
        <img src="${d.photo}" alt="${d.name}" />
        <div>
          <h4>${d.name}</h4>
          <p>${d.specialty} · ${d.clinic}</p>
          <p style="color:var(--primary);font-weight:700">PKR ${d.fee.toLocaleString()} / visit</p>
        </div>
      </div>
    `;
  }
  showModal('bookingModal');
}

function confirmBooking(e) {
  e.preventDefault();
  closeModal('bookingModal');
  showToast('✅ Appointment booked successfully! You will receive a confirmation SMS.', 'success');
}

function showDoctorDetails(id) {
  const d = doctors.find(x => x.id === id);
  if (!d) return;
  const content = `
    <div style="display:flex;gap:16px;align-items:center;margin-bottom:16px">
      <img src="${d.photo}" style="width:80px;height:80px;border-radius:50%"/>
      <div>
        <h3 style="font-size:18px;font-weight:700">${d.name}</h3>
        <div style="color:var(--primary);font-weight:600">${d.specialty}</div>
        <div style="font-size:13px;color:var(--text-muted)">${d.qualification}</div>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
      <div style="background:var(--bg);padding:12px;border-radius:8px">
        <div style="font-size:12px;color:var(--text-muted)">Experience</div>
        <div style="font-weight:700">${d.experience} years</div>
      </div>
      <div style="background:var(--bg);padding:12px;border-radius:8px">
        <div style="font-size:12px;color:var(--text-muted)">Rating</div>
        <div style="font-weight:700;color:#f59e0b">★ ${d.rating} (${d.reviews} reviews)</div>
      </div>
      <div style="background:var(--bg);padding:12px;border-radius:8px">
        <div style="font-size:12px;color:var(--text-muted)">Consultation Fee</div>
        <div style="font-weight:700;color:var(--primary)">PKR ${d.fee.toLocaleString()}</div>
      </div>
      <div style="background:var(--bg);padding:12px;border-radius:8px">
        <div style="font-size:12px;color:var(--text-muted)">Availability</div>
        <div style="font-weight:700;color:${d.available ? 'var(--accent)' : '#ef4444'}">${d.available ? 'Available Today' : d.nextSlot}</div>
      </div>
    </div>
    <div style="margin-bottom:14px">
      <div style="font-weight:600;margin-bottom:6px">About</div>
      <p style="font-size:14px;color:var(--text-muted)">${d.about}</p>
    </div>
    <div style="margin-bottom:14px">
      <div style="font-weight:600;margin-bottom:6px">Clinic</div>
      <p style="font-size:14px">📍 ${d.address}</p>
      <p style="font-size:14px">📞 ${d.phone}</p>
      <p style="font-size:14px">🕐 ${d.timings}</p>
    </div>
    <div style="margin-bottom:20px">
      <div style="font-weight:600;margin-bottom:8px">Specializes In</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px">${d.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>
    </div>
    <button class="btn-primary" style="width:100%;padding:12px" onclick="closeModal('profileModal');openBooking(${d.id})">Book Appointment</button>
  `;

  let modal = document.getElementById('profileModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'profileModal';
    modal.innerHTML = `<div class="modal"><button class="modal-close" onclick="closeModal('profileModal')">✕</button><div id="profileContent"></div></div>`;
    document.body.appendChild(modal);
  }
  document.getElementById('profileContent').innerHTML = content;
  showModal('profileModal');
}

// ── MODALS ──
function showModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.add('open'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.remove('open'); document.body.style.overflow = ''; }
}

document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
    document.body.style.overflow = '';
  }
});

// ── AUTH ──
function handleLogin(e) {
  e.preventDefault();
  closeModal('loginModal');
  showToast('✅ Logged in successfully!', 'success');
}
function handleRegister(e) {
  e.preventDefault();
  closeModal('registerModal');
  showToast('✅ Account created! Welcome to DocBook Islamabad.', 'success');
}

// ── TOAST ──
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = 'toast show' + (type ? ' ' + type : '');
  setTimeout(() => { t.className = 'toast'; }, 4000);
}

// ── MOBILE MENU ──
function toggleMobileMenu() {
  document.getElementById('mobileMenu')?.classList.toggle('open');
}
