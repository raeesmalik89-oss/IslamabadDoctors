// ── ADMIN INIT ──
let adminDoctors = [];
let adminBookings = [];
let editingDoctorId = null;

document.addEventListener('DOMContentLoaded', () => {
  initFirebase();
  checkFirebaseStatus();

  // Check if already logged in (local mode)
  const localAdmin = sessionStorage.getItem('adminLoggedIn');
  if (localAdmin === 'true' || isFirebaseReady) {
    if (isFirebaseReady) {
      auth.onAuthStateChanged(user => {
        if (user) showAdminDashboard(user.email);
        else showLoginScreen();
      });
    } else if (localAdmin === 'true') {
      showAdminDashboard(sessionStorage.getItem('adminEmail') || 'admin@local');
    } else {
      showLoginScreen();
    }
  } else {
    showLoginScreen();
  }

  populateDoctorFormDataLists();
});

// ── AUTH ──
async function adminLogin(e) {
  e.preventDefault();
  const email = document.getElementById('adminEmail').value;
  const pass  = document.getElementById('adminPassword').value;
  const errEl = document.getElementById('loginError');
  errEl.textContent = '';

  if (isFirebaseReady) {
    try {
      await auth.signInWithEmailAndPassword(email, pass);
      showAdminDashboard(email);
    } catch (err) {
      errEl.textContent = 'Invalid email or password. Please try again.';
    }
  } else {
    // Local fallback (for demo without Firebase)
    if (pass.length >= 6) {
      sessionStorage.setItem('adminLoggedIn', 'true');
      sessionStorage.setItem('adminEmail', email);
      showAdminDashboard(email);
    } else {
      errEl.textContent = 'Password must be at least 6 characters.';
    }
  }
}

async function adminSetupAccount() {
  const email = prompt('Enter admin email:');
  const pass  = prompt('Enter admin password (min 6 chars):');
  if (!email || !pass) return;
  if (!isFirebaseReady) {
    sessionStorage.setItem('adminLoggedIn', 'true');
    sessionStorage.setItem('adminEmail', email);
    showAdminDashboard(email);
    showToast('✅ Account created (local mode — connect Firebase for real auth)', 'success');
    return;
  }
  try {
    await auth.createUserWithEmailAndPassword(email, pass);
    showToast('✅ Admin account created!', 'success');
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

function adminLogout() {
  sessionStorage.removeItem('adminLoggedIn');
  sessionStorage.removeItem('adminEmail');
  if (isFirebaseReady) auth.signOut();
  showLoginScreen();
}

function showLoginScreen() {
  document.getElementById('loginScreen').style.display = 'flex';
  document.getElementById('adminDashboard').style.display = 'none';
}

function showAdminDashboard(email) {
  document.getElementById('loginScreen').style.display = 'none';
  document.getElementById('adminDashboard').style.display = 'flex';
  document.getElementById('adminUserInfo').textContent = email;
  loadDashboard();
}

// ── DASHBOARD ──
async function loadDashboard() {
  try {
    const [stats, bookings] = await Promise.all([dbGetStats(), dbGetBookings()]);
    adminBookings = bookings;

    document.getElementById('s-doctors').textContent  = stats.totalDoctors;
    document.getElementById('s-bookings').textContent = stats.totalBookings;
    document.getElementById('s-today').textContent    = stats.todayBookings;
    document.getElementById('s-pending').textContent  = stats.pending;
    document.getElementById('pendingBadge').textContent = stats.pending;

    renderRecentBookings(bookings.slice(0, 5));
  } catch (err) {
    console.error('Dashboard load error:', err);
  }
}

function renderRecentBookings(list) {
  const el = document.getElementById('recentBookings');
  if (!list.length) { el.innerHTML = '<p style="color:var(--text-muted);font-size:14px">No bookings yet.</p>'; return; }
  el.innerHTML = list.map(b => `
    <div class="recent-booking-item">
      <div>
        <div class="rb-name">${b.patientName}</div>
        <div class="rb-meta">Dr. ${b.doctorName} · ${b.date} ${b.time}</div>
      </div>
      <span class="status-badge status-${b.status}">${b.status}</span>
    </div>
  `).join('');
}

// ── TAB SWITCHING ──
function switchTab(name, el) {
  document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.admin-nav-item').forEach(a => a.classList.remove('active'));
  document.getElementById('tab-' + name)?.classList.add('active');
  if (el) el.classList.add('active');

  const titles = { dashboard: ['Dashboard', "Welcome back! Here's what's happening today."], doctors: ['Doctors', 'Manage your doctor listings'], bookings: ['Bookings', 'View and manage all appointments'], settings: ['Settings', 'Configure your platform'] };
  const [title, sub] = titles[name] || ['', ''];
  document.getElementById('pageTitle').textContent = title;
  document.getElementById('pageSub').textContent   = sub;

  if (name === 'dashboard') loadDashboard();
  if (name === 'doctors')   loadAdminDoctors();
  if (name === 'bookings')  loadAdminBookings();
  if (name === 'settings')  checkFirebaseStatus();
  return false;
}

// ── DOCTORS MANAGEMENT ──
async function loadAdminDoctors() {
  adminDoctors = await dbGetDoctors();
  populateDoctorSpecialtyFilter();
  renderAdminDoctors();
}

function populateDoctorSpecialtyFilter() {
  const sel = document.getElementById('doctorFilterSpec');
  if (!sel) return;
  const current = sel.value;
  while (sel.options.length > 1) sel.remove(1);
  [...new Set(adminDoctors.map(d => d.specialty))].sort().forEach(s => {
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    sel.appendChild(o);
  });
  sel.value = current;
}

function renderAdminDoctors() {
  const q    = (document.getElementById('doctorSearch')?.value || '').toLowerCase();
  const spec = document.getElementById('doctorFilterSpec')?.value || '';
  const tbody = document.getElementById('doctorsTableBody');
  if (!tbody) return;

  let list = adminDoctors.filter(d =>
    (!q || d.name.toLowerCase().includes(q) || d.area?.toLowerCase().includes(q)) &&
    (!spec || d.specialty === spec)
  );

  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading-text">No doctors found.</td></tr>';
    return;
  }

  tbody.innerHTML = list.map(d => `
    <tr>
      <td>
        <div class="doc-cell">
          <img src="${d.photo || avatarUrl(d.name)}" alt="${d.name}" />
          <div><div class="doc-cell-name">${d.name}</div><div class="doc-cell-qual">${d.qualification || ''}</div></div>
        </div>
      </td>
      <td>${d.specialty}</td>
      <td>${d.area}</td>
      <td>PKR ${Number(d.fee).toLocaleString()}</td>
      <td><span style="color:#f59e0b;font-weight:700">★ ${d.rating || '–'}</span></td>
      <td><span class="status-badge ${d.available ? 'status-confirmed' : 'status-cancelled'}">${d.available ? 'Yes' : 'No'}</span></td>
      <td>
        <div class="action-btns">
          <button class="btn-sm btn-sm-edit"   onclick="openEditDoctor('${d._firestoreId || d.id}')">✏️ Edit</button>
          <button class="btn-sm btn-sm-delete" onclick="confirmDeleteDoctor('${d._firestoreId || d.id}', '${d.name}')">🗑 Delete</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function openAddDoctorModal() {
  editingDoctorId = null;
  document.getElementById('doctorModalTitle').textContent = 'Add New Doctor';
  document.getElementById('doctorForm').reset();
  document.getElementById('df-firestoreId').value = '';
  document.getElementById('df-available').checked = true;
  showModal('doctorModal');
}

function openEditDoctor(id) {
  const d = adminDoctors.find(x => (x._firestoreId || String(x.id)) === String(id));
  if (!d) return;
  editingDoctorId = id;
  document.getElementById('doctorModalTitle').textContent = 'Edit Doctor';
  document.getElementById('df-firestoreId').value  = d._firestoreId || '';
  document.getElementById('df-name').value         = d.name || '';
  document.getElementById('df-specialty').value    = d.specialty || '';
  document.getElementById('df-qualification').value= d.qualification || '';
  document.getElementById('df-experience').value   = d.experience || '';
  document.getElementById('df-fee').value          = d.fee || '';
  document.getElementById('df-gender').value       = d.gender || '';
  document.getElementById('df-clinic').value       = d.clinic || '';
  document.getElementById('df-area').value         = d.area || '';
  document.getElementById('df-address').value      = d.address || '';
  document.getElementById('df-phone').value        = d.phone || '';
  document.getElementById('df-whatsapp').value     = d.whatsapp || '';
  document.getElementById('df-timings').value      = d.timings || '';
  document.getElementById('df-tags').value         = (d.tags || []).join(', ');
  document.getElementById('df-about').value        = d.about || '';
  document.getElementById('df-photo').value        = d.photo || '';
  document.getElementById('df-available').checked  = !!d.available;
  showModal('doctorModal');
}

async function saveDoctorForm(e) {
  e.preventDefault();
  const fid = document.getElementById('df-firestoreId').value;
  const tags = document.getElementById('df-tags').value.split(',').map(t => t.trim()).filter(Boolean);
  const name = document.getElementById('df-name').value;

  const data = {
    name,
    specialty:     document.getElementById('df-specialty').value,
    qualification: document.getElementById('df-qualification').value,
    experience:    parseInt(document.getElementById('df-experience').value),
    fee:           parseInt(document.getElementById('df-fee').value),
    gender:        document.getElementById('df-gender').value,
    clinic:        document.getElementById('df-clinic').value,
    area:          document.getElementById('df-area').value,
    address:       document.getElementById('df-address').value,
    phone:         document.getElementById('df-phone').value,
    whatsapp:      document.getElementById('df-whatsapp').value,
    timings:       document.getElementById('df-timings').value,
    tags,
    about:         document.getElementById('df-about').value,
    photo:         document.getElementById('df-photo').value || avatarUrl(name),
    available:     document.getElementById('df-available').checked,
    rating:        editingDoctorId ? (adminDoctors.find(x => (x._firestoreId || String(x.id)) === String(editingDoctorId))?.rating || 4.5) : 4.5,
    reviews:       editingDoctorId ? (adminDoctors.find(x => (x._firestoreId || String(x.id)) === String(editingDoctorId))?.reviews || 0) : 0,
  };

  try {
    if (fid && isFirebaseReady) {
      await dbUpdateDoctor(fid, data);
      showToast('✅ Doctor updated successfully!', 'success');
    } else if (isFirebaseReady) {
      await dbAddDoctor(data);
      showToast('✅ Doctor added successfully!', 'success');
    } else {
      showToast('✅ Saved locally (connect Firebase to persist)', 'success');
    }
    closeModal('doctorModal');
    await loadAdminDoctors();
  } catch (err) {
    showToast('❌ Error: ' + err.message);
  }
}

async function confirmDeleteDoctor(id, name) {
  if (!confirm(`Delete Dr. ${name}? This cannot be undone.`)) return;
  try {
    await dbDeleteDoctor(id);
    showToast('🗑 Doctor removed', '');
    await loadAdminDoctors();
  } catch (err) {
    showToast('❌ Error: ' + err.message);
  }
}

// ── BOOKINGS MANAGEMENT ──
async function loadAdminBookings() {
  adminBookings = await dbGetBookings();
  renderAdminBookings();
}

function renderAdminBookings() {
  const q      = (document.getElementById('bookingSearch')?.value || '').toLowerCase();
  const status = document.getElementById('bookingFilterStatus')?.value || '';
  const tbody  = document.getElementById('bookingsTableBody');
  if (!tbody) return;

  let list = adminBookings.filter(b =>
    (!q || b.patientName?.toLowerCase().includes(q) || b.doctorName?.toLowerCase().includes(q) || b.phone?.includes(q)) &&
    (!status || b.status === status)
  );

  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="loading-text">No bookings found.</td></tr>';
    return;
  }

  tbody.innerHTML = list.map(b => `
    <tr>
      <td>
        <div style="font-weight:600">${b.patientName}</div>
        <div style="font-size:12px;color:var(--text-muted)">${b.phone}</div>
      </td>
      <td>${b.doctorName}<div style="font-size:12px;color:var(--text-muted)">${b.doctorSpecialty || ''}</div></td>
      <td>${b.date}<div style="font-size:12px;color:var(--text-muted)">${b.time}</div></td>
      <td style="max-width:160px;font-size:13px">${b.reason || '–'}</td>
      <td><span class="status-badge status-${b.status}">${b.status}</span></td>
      <td>
        <div class="action-btns">
          <button class="btn-sm btn-sm-confirm" onclick="updateStatus('${b._firestoreId || b.id}', 'confirmed')">✅</button>
          <button class="btn-sm btn-sm-cancel"  onclick="updateStatus('${b._firestoreId || b.id}', 'cancelled')">❌</button>
          <button class="btn-sm btn-sm-wa"      onclick="adminWaNotify(${JSON.stringify(b).replace(/'/g,"&#39;")})">📱</button>
          <button class="btn-sm btn-sm-delete"  onclick="deleteBooking('${b._firestoreId || b.id}')">🗑</button>
        </div>
      </td>
    </tr>
  `).join('');
}

async function updateStatus(id, status) {
  try {
    await dbUpdateBookingStatus(id, status);
    const b = adminBookings.find(x => (x._firestoreId || x.id) === id);
    if (b) b.status = status;
    renderAdminBookings();
    document.getElementById('s-pending').textContent = adminBookings.filter(x => x.status === 'pending').length;
    document.getElementById('pendingBadge').textContent = adminBookings.filter(x => x.status === 'pending').length;
    showToast(`✅ Booking marked as ${status}`, 'success');
  } catch (err) {
    showToast('❌ Error: ' + err.message);
  }
}

async function deleteBooking(id) {
  if (!confirm('Delete this booking?')) return;
  await dbDeleteBooking(id);
  adminBookings = adminBookings.filter(b => (b._firestoreId || b.id) !== id);
  renderAdminBookings();
  showToast('🗑 Booking deleted');
}

function adminWaNotify(booking) {
  const doctor = adminDoctors.find(d => d.name === booking.doctorName) || { name: booking.doctorName, clinic: '', fee: '' };
  const msg = `*Appointment ${booking.status === 'confirmed' ? 'CONFIRMED ✅' : 'Update'}*\n\n` +
    `Patient: ${booking.patientName}\n` +
    `Doctor: ${booking.doctorName}\n` +
    `Date: ${booking.date} at ${booking.time}\n` +
    `Status: ${booking.status?.toUpperCase()}\n\n_DocBook Islamabad_`;
  const phone = booking.phone?.replace(/\D/g, '');
  const norm  = phone?.startsWith('0') ? '92' + phone.slice(1) : phone;
  window.open(`https://wa.me/${norm}?text=${encodeURIComponent(msg)}`, '_blank');
}

// ── EXPORT CSV ──
function exportBookingsCSV() {
  const rows = [['Patient', 'Phone', 'Doctor', 'Specialty', 'Date', 'Time', 'Reason', 'Status', 'Created']];
  adminBookings.forEach(b => {
    rows.push([b.patientName, b.phone, b.doctorName, b.doctorSpecialty || '', b.date, b.time, b.reason || '', b.status, b.createdAt || '']);
  });
  const csv  = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = 'docbook_bookings_' + new Date().toISOString().split('T')[0] + '.csv';
  a.click();
  showToast('📥 CSV exported!', 'success');
}

// ── SETTINGS ──
function checkFirebaseStatus() {
  const el = document.getElementById('firebaseStatus');
  if (!el) return;
  if (isFirebaseReady) {
    el.textContent   = '✅ Connected to Firebase';
    el.className     = 'firebase-status connected';
  } else {
    el.textContent   = '⚠️ Not connected — using local storage (data will not persist)';
    el.className     = 'firebase-status local';
  }
}

function saveSettings(e) {
  e.preventDefault();
  const settings = {
    bizName:    document.getElementById('biz-name').value,
    whatsapp:   document.getElementById('biz-whatsapp').value,
    address:    document.getElementById('biz-address').value,
    email:      document.getElementById('biz-email').value,
    phone:      document.getElementById('biz-phone').value,
  };
  localStorage.setItem('docbook_settings', JSON.stringify(settings));
  if (settings.whatsapp) window.WHATSAPP_BUSINESS_NUMBER = settings.whatsapp;
  showToast('✅ Settings saved!', 'success');
}

function changePassword(e) {
  e.preventDefault();
  const p1 = document.getElementById('newPass').value;
  const p2 = document.getElementById('confirmPass').value;
  if (p1 !== p2) { showToast('❌ Passwords do not match'); return; }
  if (!isFirebaseReady) { showToast('⚠️ Connect Firebase to change password'); return; }
  auth.currentUser?.updatePassword(p1)
    .then(() => showToast('✅ Password updated!', 'success'))
    .catch(err => showToast('❌ ' + err.message));
}

// ── HELPERS ──
function avatarUrl(name) {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0ea5e9&color=fff&size=128`;
}

function populateDoctorFormDataLists() {
  const specList = document.getElementById('specialtyList');
  const areaList = document.getElementById('areaList');
  if (specList) [...new Set(doctors.map(d => d.specialty))].sort().forEach(s => { const o = document.createElement('option'); o.value = s; specList.appendChild(o); });
  if (areaList) areas?.forEach(a => { if (a !== 'All Areas') { const o = document.createElement('option'); o.value = a; areaList.appendChild(o); } });
}

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

function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className   = 'toast show' + (type ? ' ' + type : '');
  setTimeout(() => { t.className = 'toast'; }, 4000);
}
