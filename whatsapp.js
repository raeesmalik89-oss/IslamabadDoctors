// ── WHATSAPP INTEGRATION ──

function waBookingMessage(doctor, patient) {
  return `*New Appointment Request*\n\n` +
    `👨‍⚕️ *Doctor:* ${doctor.name}\n` +
    `🏥 *Clinic:* ${doctor.clinic}\n` +
    `📋 *Specialty:* ${doctor.specialty}\n\n` +
    `👤 *Patient:* ${patient.name}\n` +
    `📞 *Phone:* ${patient.phone}\n` +
    `📅 *Date:* ${patient.date}\n` +
    `🕐 *Time:* ${patient.time}\n` +
    `📝 *Reason:* ${patient.reason || 'Not specified'}\n\n` +
    `_Sent via DocBook Islamabad_`;
}

function waConfirmationMessage(doctor, patient) {
  return `Hello ${patient.name}! ✅\n\n` +
    `Your appointment with *${doctor.name}* (${doctor.specialty}) has been received.\n\n` +
    `📅 Date: ${patient.date}\n` +
    `🕐 Time: ${patient.time}\n` +
    `📍 Location: ${doctor.address}\n` +
    `💰 Fee: PKR ${doctor.fee?.toLocaleString()}\n\n` +
    `Please arrive 10 minutes early. For queries call: ${doctor.phone}\n\n` +
    `_DocBook Islamabad_`;
}

// Open WhatsApp with pre-filled message to business number
function waNotifyBusiness(doctor, patient) {
  const msg = waBookingMessage(doctor, patient);
  const url = `https://wa.me/${WHATSAPP_BUSINESS_NUMBER}?text=${encodeURIComponent(msg)}`;
  window.open(url, '_blank');
}

// Open WhatsApp to confirm appointment to patient
function waConfirmPatient(doctor, patient) {
  const phone = patient.phone.replace(/\D/g, '');
  const normalized = phone.startsWith('0') ? '92' + phone.slice(1) : phone.startsWith('92') ? phone : '92' + phone;
  const msg = waConfirmationMessage(doctor, patient);
  const url = `https://wa.me/${normalized}?text=${encodeURIComponent(msg)}`;
  window.open(url, '_blank');
}

// Direct WhatsApp link for a doctor
function waDoctorDirect(doctor, patientQuery) {
  const msg = `Hello Dr. ${doctor.name.replace('Dr. ', '')},\n\n` +
    `I found your profile on DocBook Islamabad.\n\n` +
    (patientQuery ? `*My query:* ${patientQuery}\n\n` : '') +
    `I would like to book an appointment. Please let me know your availability.\n\n` +
    `_Sent via DocBook Islamabad_`;
  const phone = doctor.whatsapp || doctor.phone?.replace(/\D/g, '');
  if (!phone) { alert('WhatsApp number not available for this doctor.'); return; }
  const normalized = phone.startsWith('0') ? '92' + phone.slice(1) : phone;
  window.open(`https://wa.me/${normalized}?text=${encodeURIComponent(msg)}`, '_blank');
}
