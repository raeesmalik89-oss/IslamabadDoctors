// ── DATABASE SERVICE LAYER ──
// Falls back to local data.js when Firebase is not configured

// ── DOCTORS ──
async function dbGetDoctors() {
  if (!isFirebaseReady) return doctors;
  try {
    const snap = await db.collection('doctors').orderBy('rating', 'desc').get();
    if (snap.empty) {
      await dbSeedDoctors();
      return doctors;
    }
    return snap.docs.map(d => ({ ...d.data(), id: d.id, _firestoreId: d.id }));
  } catch (e) {
    console.warn('Firestore read failed, using local data', e);
    return doctors;
  }
}

async function dbAddDoctor(data) {
  if (!isFirebaseReady) throw new Error('Firebase not connected');
  const ref = await db.collection('doctors').add({ ...data, createdAt: firebase.firestore.FieldValue.serverTimestamp() });
  return ref.id;
}

async function dbUpdateDoctor(firestoreId, data) {
  if (!isFirebaseReady) throw new Error('Firebase not connected');
  await db.collection('doctors').doc(firestoreId).update({ ...data, updatedAt: firebase.firestore.FieldValue.serverTimestamp() });
}

async function dbDeleteDoctor(firestoreId) {
  if (!isFirebaseReady) throw new Error('Firebase not connected');
  await db.collection('doctors').doc(firestoreId).delete();
}

// ── BOOKINGS ──
async function dbAddBooking(data) {
  const booking = {
    ...data,
    status: 'pending',
    createdAt: isFirebaseReady ? firebase.firestore.FieldValue.serverTimestamp() : new Date().toISOString()
  };
  if (!isFirebaseReady) {
    const local = JSON.parse(localStorage.getItem('bookings') || '[]');
    booking.id = Date.now().toString();
    booking.createdAt = new Date().toISOString();
    local.push(booking);
    localStorage.setItem('bookings', JSON.stringify(local));
    return booking.id;
  }
  const ref = await db.collection('bookings').add(booking);
  return ref.id;
}

async function dbGetBookings() {
  if (!isFirebaseReady) {
    return JSON.parse(localStorage.getItem('bookings') || '[]');
  }
  const snap = await db.collection('bookings').orderBy('createdAt', 'desc').get();
  return snap.docs.map(d => ({ ...d.data(), _firestoreId: d.id, createdAt: d.data().createdAt?.toDate?.()?.toISOString() || '' }));
}

async function dbUpdateBookingStatus(firestoreId, status) {
  if (!isFirebaseReady) {
    const local = JSON.parse(localStorage.getItem('bookings') || '[]');
    const idx = local.findIndex(b => b.id === firestoreId);
    if (idx !== -1) { local[idx].status = status; localStorage.setItem('bookings', JSON.stringify(local)); }
    return;
  }
  await db.collection('bookings').doc(firestoreId).update({ status, updatedAt: firebase.firestore.FieldValue.serverTimestamp() });
}

async function dbDeleteBooking(firestoreId) {
  if (!isFirebaseReady) {
    const local = JSON.parse(localStorage.getItem('bookings') || '[]').filter(b => b.id !== firestoreId);
    localStorage.setItem('bookings', JSON.stringify(local));
    return;
  }
  await db.collection('bookings').doc(firestoreId).delete();
}

// ── SEED FIRESTORE WITH INITIAL DOCTORS ──
async function dbSeedDoctors() {
  if (!isFirebaseReady || !doctors?.length) return;
  const batch = db.batch();
  doctors.forEach(d => {
    const ref = db.collection('doctors').doc();
    batch.set(ref, { ...d, createdAt: firebase.firestore.FieldValue.serverTimestamp() });
  });
  await batch.commit();
  console.log('✅ Seeded', doctors.length, 'doctors to Firestore');
}

// ── STATS ──
async function dbGetStats() {
  const [docs, bookings] = await Promise.all([dbGetDoctors(), dbGetBookings()]);
  const today = new Date().toISOString().split('T')[0];
  return {
    totalDoctors:   docs.length,
    totalBookings:  bookings.length,
    todayBookings:  bookings.filter(b => b.date === today).length,
    pending:        bookings.filter(b => b.status === 'pending').length,
    confirmed:      bookings.filter(b => b.status === 'confirmed').length,
  };
}
