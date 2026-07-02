import { auth } from "./firebase-config.js";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const provider = new GoogleAuthProvider();

async function setServerSession(user) {
  const idToken = await user.getIdToken(true);
  const refreshToken = user.refreshToken;
  const res = await fetch("/auth/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ idToken, refreshToken })
  });
  const data = await res.json();
  if (data.redirect) window.location.href = data.redirect;
}

window.loginEmail = async function(email, password) {
  try {
    const cred = await signInWithEmailAndPassword(auth, email, password);
    await setServerSession(cred.user);
  } catch (e) {
    throw new Error(getFriendlyError(e.code));
  }
};

window.registerEmail = async function(email, password) {
  try {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    await sendEmailVerification(cred.user);
    await setServerSession(cred.user);
  } catch (e) {
    throw new Error(getFriendlyError(e.code));
  }
};

window.loginGoogle = async function() {
  try {
    const cred = await signInWithPopup(auth, provider);
    await setServerSession(cred.user);
  } catch (e) {
    if (e.code !== "auth/popup-closed-by-user") {
      throw new Error(getFriendlyError(e.code));
    }
  }
};

window.sendVerification = async function() {
  const user = auth.currentUser;
  if (user) {
    await sendEmailVerification(user);
  }
};

window.forgotPassword = async function(email) {
  try {
    await sendPasswordResetEmail(auth, email);
  } catch (e) {
    throw new Error(getFriendlyError(e.code));
  }
};

function getFriendlyError(code) {
  const map = {
    "auth/user-not-found": "No account found with this email.",
    "auth/wrong-password": "Incorrect password. Please try again.",
    "auth/email-already-in-use": "Email is already registered.",
    "auth/weak-password": "Password must be at least 6 characters.",
    "auth/invalid-email": "Please enter a valid email address.",
    "auth/too-many-requests": "Too many attempts. Please try again later.",
    "auth/network-request-failed": "Network error. Check your connection.",
    "auth/popup-blocked": "Popup was blocked. Allow popups and try again.",
    "auth/invalid-credential": "Invalid credentials. Check your email and password."
  };
  return map[code] || "Authentication failed. Please try again.";
}
