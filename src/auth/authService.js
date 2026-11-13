/**
 * Miora Authentication Service
 * Manages role-based authentication for Patients and Doctors.
 */

const STORAGE_USERS_KEY = 'miora_registered_users_v1';
const STORAGE_SESSION_KEY = 'miora_auth_user_v1';

export const DEMO_ACCOUNTS = {
  patient: {
    email: 'patient@miora.health',
    password: 'password123',
    role: 'patient',
    name: 'Amara K.',
    postpartumWeek: 6,
  },
  doctor: {
    email: 'doctor@miora.health',
    password: 'password123',
    role: 'doctor',
    name: 'Dr. Elena Rostova',
    clinic: 'Miora Maternal Care Unit',
  },
};

function getRegisteredUsers() {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return [];
    const raw = window.localStorage.getItem(STORAGE_USERS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRegisteredUser(user) {
  try {
    const list = getRegisteredUsers();
    list.push(user);
    window.localStorage.setItem(STORAGE_USERS_KEY, JSON.stringify(list));
  } catch (err) {
    console.error('Error saving user', err);
  }
}

export function getCurrentUser() {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return null;
    const raw = window.localStorage.getItem(STORAGE_SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setCurrentUser(user) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return;
    if (user) {
      window.localStorage.setItem(STORAGE_SESSION_KEY, JSON.stringify(user));
    } else {
      window.localStorage.removeItem(STORAGE_SESSION_KEY);
    }
  } catch (err) {
    console.error('Error setting current user', err);
  }
}

export function signOutUser() {
  setCurrentUser(null);
}

/**
 * Validates credentials and verifies that the account role matches the selected role.
 */
export async function authenticate({ email, password, selectedRole }) {
  // Simulate brief realistic authentication latency
  await new Promise((resolve) => setTimeout(resolve, 400));

  const trimmedEmail = (email || '').trim().toLowerCase();
  const trimmedPassword = (password || '').trim();

  // Basic validation
  if (!trimmedEmail) {
    throw new Error('Please enter your email address.');
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(trimmedEmail)) {
    throw new Error('Please enter a valid email address.');
  }

  if (!trimmedPassword) {
    throw new Error('Please enter your password.');
  }

  if (trimmedPassword.length < 6) {
    throw new Error('Password must be at least 6 characters.');
  }

  // Determine actual account role from existing registered users or predefined accounts
  const registeredUsers = getRegisteredUsers();
  const existingUser = registeredUsers.find((u) => u.email.toLowerCase() === trimmedEmail);

  let accountRole = null;
  let accountName = '';

  if (existingUser) {
    accountRole = existingUser.role;
    accountName = existingUser.name;
  } else if (
    trimmedEmail === DEMO_ACCOUNTS.doctor.email ||
    trimmedEmail.includes('doctor') ||
    trimmedEmail.startsWith('dr.') ||
    trimmedEmail.endsWith('@mioraclinical.org')
  ) {
    accountRole = 'doctor';
    accountName = DEMO_ACCOUNTS.doctor.name;
  } else if (
    trimmedEmail === DEMO_ACCOUNTS.patient.email ||
    trimmedEmail === 'mother@miora.health' ||
    trimmedEmail === 'amara@miora.health' ||
    trimmedEmail === 'sadiya@miora.health'
  ) {
    accountRole = 'patient';
    accountName = DEMO_ACCOUNTS.patient.name;
  } else {
    // Default account role for new or external accounts based on selectedRole
    accountRole = selectedRole || (trimmedEmail.includes('clinician') || trimmedEmail.includes('hospital') ? 'doctor' : 'patient');
    accountName = trimmedEmail.split('@')[0];
  }

  // Strict role verification:
  // Do not allow access to Doctor portal simply by selecting Doctor card if registered as Patient.
  // Respect authenticated account role and display clear mismatch error.
  if (selectedRole === 'doctor' && accountRole === 'patient') {
    throw new Error(
      "Access denied: This account is registered as a Patient. You cannot access the Doctor portal with patient credentials."
    );
  }

  if (selectedRole === 'patient' && accountRole === 'doctor') {
    throw new Error(
      "Access denied: This account is registered as a Healthcare Professional (Doctor). Please select Doctor to sign in."
    );
  }

  const authenticatedUser = {
    email: trimmedEmail,
    role: accountRole,
    name: accountName || (accountRole === 'doctor' ? 'Dr. Elena Rostova' : 'Amara K.'),
    authenticatedAt: new Date().toISOString(),
  };

  setCurrentUser(authenticatedUser);

  return {
    user: authenticatedUser,
    redirectUrl: accountRole === 'doctor' ? '/dashboard' : '/patient/dashboard',
  };
}

/**
 * Quick Google Authentication simulation respecting selected role.
 */
export async function authenticateWithGoogle(selectedRole) {
  await new Promise((resolve) => setTimeout(resolve, 450));

  const isDoctor = selectedRole === 'doctor';
  const user = {
    email: isDoctor ? DEMO_ACCOUNTS.doctor.email : DEMO_ACCOUNTS.patient.email,
    role: isDoctor ? 'doctor' : 'patient',
    name: isDoctor ? DEMO_ACCOUNTS.doctor.name : DEMO_ACCOUNTS.patient.name,
    avatar: isDoctor ? null : '/assets/hero-mother.png',
    provider: 'google',
    authenticatedAt: new Date().toISOString(),
  };

  setCurrentUser(user);

  return {
    user,
    redirectUrl: isDoctor ? '/dashboard' : '/patient/dashboard',
  };
}

/**
 * Account registration
 */
export async function registerAccount({ name, email, password, role }) {
  await new Promise((resolve) => setTimeout(resolve, 450));

  const trimmedEmail = (email || '').trim().toLowerCase();
  const trimmedName = (name || '').trim();
  const trimmedPassword = (password || '').trim();

  if (!trimmedName) throw new Error('Please enter your full name.');
  if (!trimmedEmail) throw new Error('Please enter your email address.');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
    throw new Error('Please enter a valid email address.');
  }
  if (!trimmedPassword || trimmedPassword.length < 6) {
    throw new Error('Password must be at least 6 characters.');
  }

  const newUser = {
    id: `usr-${Date.now()}`,
    name: trimmedName,
    email: trimmedEmail,
    role: role || 'patient',
    registeredAt: new Date().toISOString(),
  };

  saveRegisteredUser(newUser);
  setCurrentUser(newUser);

  return {
    user: newUser,
    redirectUrl: newUser.role === 'doctor' ? '/dashboard' : '/patient/dashboard',
  };
}

