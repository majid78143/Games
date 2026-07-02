const FIREBASE_CONFIG = {
  apiKey: "AIzaSyCuZDyri0F0ky2sHxFO-p2OKvEB2sQfihw",
  authDomain: "dreamdrop-3ca3d.firebaseapp.com",
  databaseURL: "https://dreamdrop-3ca3d-default-rtdb.firebaseio.com",
  projectId: "dreamdrop-3ca3d",
  storageBucket: "dreamdrop-3ca3d.firebasestorage.app",
  messagingSenderId: "882827368473",
  appId: "1:882827368473:web:bf146e6c9f5db32edbb288",
  measurementId: "G-Z6B3CZZRC9"
};

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { getAuth } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { getDatabase } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-database.js";

const app = initializeApp(FIREBASE_CONFIG);
const auth = getAuth(app);
const db = getDatabase(app);

export { app, auth, db };
