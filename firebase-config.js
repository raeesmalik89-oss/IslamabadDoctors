// ─────────────────────────────────────────────
// STEP 1: Go to https://console.firebase.google.com
// STEP 2: Create a new project (e.g. "docbook-islamabad")
// STEP 3: Click "Web" app (</>), register app
// STEP 4: Copy your config values below
// ─────────────────────────────────────────────
const firebaseConfig = {
  apiKey:            "REPLACE_WITH_YOUR_API_KEY",
  authDomain:        "REPLACE_WITH_YOUR_PROJECT.firebaseapp.com",
  projectId:         "REPLACE_WITH_YOUR_PROJECT_ID",
  storageBucket:     "REPLACE_WITH_YOUR_PROJECT.appspot.com",
  messagingSenderId: "REPLACE_WITH_YOUR_SENDER_ID",
  appId:             "REPLACE_WITH_YOUR_APP_ID"
};

// WhatsApp Business number (with country code, no + or spaces)
// e.g. Pakistani number: 923001234567
const WHATSAPP_BUSINESS_NUMBER = "923001234567";

// Admin email (set this to your email)
const ADMIN_EMAIL = "admin@docbook.pk";

let db, auth, isFirebaseReady = false;

function initFirebase() {
  try {
    if (typeof firebase === 'undefined') return false;
    if (!firebase.apps.length) firebase.initializeApp(firebaseConfig);
    db   = firebase.firestore();
    auth = firebase.auth();
    window.db   = db;
    window.auth = auth;
    isFirebaseReady = true;
    console.log("✅ Firebase connected");
    return true;
  } catch (e) {
    console.warn("⚠️ Firebase not configured, using local data:", e.message);
    return false;
  }
}
