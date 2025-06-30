# Firebase Integration for Frontend

## Overview
This document outlines the Firebase integration points for the OrderFox vanilla JavaScript frontend using Firebase Web SDK.

## Required Dependencies

Add to `package.json`:
```json
{
  "dependencies": {
    "firebase": "^10.7.0"
  }
}
```

Install:
```bash
npm install firebase
```

## Firebase Configuration

### File: `src/config/firebase.js`
```javascript
import { initializeApp } from 'firebase/app';
import { getAuth, connectAuthEmulator } from 'firebase/auth';
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore';
import { getAnalytics } from 'firebase/analytics';

// Firebase configuration
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase services
const auth = getAuth(app);
const db = getFirestore(app);
const analytics = getAnalytics(app);

// Connect to emulators in development
if (import.meta.env.DEV) {
  const emulatorHost = import.meta.env.VITE_FIREBASE_EMULATOR_HOST || 'localhost';
  
  // Connect Auth emulator
  if (!auth._delegate._config.emulator) {
    connectAuthEmulator(auth, `http://${emulatorHost}:4001`);
  }
  
  // Connect Firestore emulator
  if (!db._delegate._settings?.host?.includes('localhost')) {
    connectFirestoreEmulator(db, emulatorHost, 4002);
  }
}

export { auth, db, analytics };
export default app;
```

## Environment Variables

Add to `.env.local`:
```env
# Firebase Configuration
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=orderfox-dev.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=orderfox-dev
VITE_FIREBASE_STORAGE_BUCKET=orderfox-dev.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:abc123def456
VITE_FIREBASE_MEASUREMENT_ID=G-ABCD123456

# Firebase Emulator (Development)  
VITE_FIREBASE_EMULATOR_HOST=localhost
```

## Integration Points

### 1. Authentication Service

### File: `src/services/AuthService.js`
```javascript
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  updateProfile
} from 'firebase/auth';
import { auth } from '../config/firebase.js';

class AuthService {
  constructor() {
    this.currentUser = null;
    this.authStateListeners = [];
    
    // Listen for auth state changes
    onAuthStateChanged(auth, (user) => {
      this.currentUser = user;
      this.notifyAuthStateListeners(user);
    });
  }
  
  // Sign in with email and password
  async signIn(email, password) {
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      return userCredential.user;
    } catch (error) {
      throw new Error(`Sign in failed: ${error.message}`);
    }
  }
  
  // Create new user account
  async signUp(email, password, displayName) {
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      
      // Update profile with display name
      if (displayName) {
        await updateProfile(userCredential.user, { displayName });
      }
      
      return userCredential.user;
    } catch (error) {
      throw new Error(`Sign up failed: ${error.message}`);
    }
  }
  
  // Sign out
  async signOut() {
    try {
      await signOut(auth);
    } catch (error) {
      throw new Error(`Sign out failed: ${error.message}`);
    }
  }
  
  // Get current user
  getCurrentUser() {
    return this.currentUser;
  }
  
  // Get ID token for API requests
  async getIdToken() {
    if (!this.currentUser) {
      throw new Error('No user signed in');
    }
    return await this.currentUser.getIdToken();
  }
  
  // Subscribe to auth state changes
  onAuthStateChange(callback) {
    this.authStateListeners.push(callback);
    // Call immediately with current state
    callback(this.currentUser);
  }
  
  // Notify auth state listeners
  notifyAuthStateListeners(user) {
    this.authStateListeners.forEach(callback => callback(user));
  }
  
  // Reset password
  async resetPassword(email) {
    try {
      await sendPasswordResetEmail(auth, email);
    } catch (error) {
      throw new Error(`Password reset failed: ${error.message}`);
    }
  }
}

export default new AuthService();
```

### 2. Firestore Data Service

### File: `src/services/FirestoreService.js`
```javascript
import { 
  collection, 
  doc, 
  getDoc, 
  getDocs, 
  addDoc, 
  updateDoc, 
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  onSnapshot
} from 'firebase/firestore';
import { db } from '../config/firebase.js';
import AuthService from './AuthService.js';

class FirestoreService {
  constructor() {
    this.listeners = new Map();
  }
  
  // Get user's trading data
  async getUserTradingData(userId) {
    try {
      const docRef = doc(db, 'trading', userId);
      const docSnap = await getDoc(docRef);
      
      if (docSnap.exists()) {
        return docSnap.data();
      } else {
        return null;
      }
    } catch (error) {
      throw new Error(`Failed to get trading data: ${error.message}`);
    }
  }
  
  // Save trading order
  async saveTradingOrder(orderData) {
    try {
      const user = AuthService.getCurrentUser();
      if (!user) throw new Error('User not authenticated');
      
      const ordersRef = collection(db, 'trading', user.uid, 'orders');
      const docRef = await addDoc(ordersRef, {
        ...orderData,
        timestamp: new Date(),
        userId: user.uid
      });
      
      return docRef.id;
    } catch (error) {
      throw new Error(`Failed to save order: ${error.message}`);
    }
  }
  
  // Get user's trading orders
  async getUserOrders(userId, limitCount = 50) {
    try {
      const ordersRef = collection(db, 'trading', userId, 'orders');
      const q = query(
        ordersRef,
        orderBy('timestamp', 'desc'),
        limit(limitCount)
      );
      
      const querySnapshot = await getDocs(q);
      return querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
    } catch (error) {
      throw new Error(`Failed to get orders: ${error.message}`);
    }
  }
  
  // Save trading session
  async saveTradingSession(sessionData) {
    try {
      const user = AuthService.getCurrentUser();
      if (!user) throw new Error('User not authenticated');
      
      const sessionsRef = collection(db, 'trading', user.uid, 'sessions');
      const docRef = await addDoc(sessionsRef, {
        ...sessionData,
        startTime: new Date(),
        userId: user.uid
      });
      
      return docRef.id;
    } catch (error) {
      throw new Error(`Failed to save session: ${error.message}`);
    }
  }
  
  // Update portfolio data
  async updatePortfolio(portfolioData) {
    try {
      const user = AuthService.getCurrentUser();
      if (!user) throw new Error('User not authenticated');
      
      const portfolioRef = doc(db, 'trading', user.uid, 'portfolio', 'current');
      await updateDoc(portfolioRef, {
        ...portfolioData,
        lastUpdated: new Date(),
        userId: user.uid
      });
    } catch (error) {
      throw new Error(`Failed to update portfolio: ${error.message}`);
    }
  }
  
  // Subscribe to real-time updates
  subscribeToUserOrders(userId, callback) {
    const ordersRef = collection(db, 'trading', userId, 'orders');
    const q = query(
      ordersRef,
      orderBy('timestamp', 'desc'),
      limit(20)
    );
    
    const unsubscribe = onSnapshot(q, (querySnapshot) => {
      const orders = querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      callback(orders);
    });
    
    this.listeners.set(`orders_${userId}`, unsubscribe);
    return unsubscribe;
  }
  
  // Unsubscribe from all listeners
  unsubscribeAll() {
    this.listeners.forEach(unsubscribe => unsubscribe());
    this.listeners.clear();
  }
}

export default new FirestoreService();
```

### 3. API Client with Authentication

### File: `src/services/ApiClient.js` (Updated)
```javascript
import AuthService from './AuthService.js';

class ApiClient {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  }
  
  // Make authenticated request
  async authenticatedRequest(endpoint, options = {}) {
    try {
      // Get Firebase ID token
      const idToken = await AuthService.getIdToken();
      
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
        ...options.headers
      };
      
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers
      });
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      throw new Error(`API request failed: ${error.message}`);
    }
  }
  
  // Public request (no authentication required)
  async publicRequest(endpoint, options = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, options);
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }
    
    return await response.json();
  }
}

export default new ApiClient();
```

### 4. Authentication UI Components

### File: `src/components/AuthComponents.js`
```javascript
import AuthService from '../services/AuthService.js';

export class LoginForm {
  constructor(container) {
    this.container = container;
    this.render();
    this.attachEventListeners();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="auth-form">
        <h2>Sign In</h2>
        <form id="login-form">
          <input type="email" id="email" placeholder="Email" required>
          <input type="password" id="password" placeholder="Password" required>
          <button type="submit">Sign In</button>
        </form>
        <p>Don't have an account? <a href="#" id="switch-to-signup">Sign Up</a></p>
        <p><a href="#" id="forgot-password">Forgot Password?</a></p>
      </div>
    `;
  }
  
  attachEventListeners() {
    const form = this.container.querySelector('#login-form');
    form.addEventListener('submit', this.handleSubmit.bind(this));
  }
  
  async handleSubmit(event) {
    event.preventDefault();
    
    const email = this.container.querySelector('#email').value;
    const password = this.container.querySelector('#password').value;
    
    try {
      await AuthService.signIn(email, password);
      // User signed in successfully
    } catch (error) {
      alert(error.message);
    }
  }
}

export class SignUpForm {
  constructor(container) {
    this.container = container;
    this.render();
    this.attachEventListeners();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="auth-form">
        <h2>Sign Up</h2>
        <form id="signup-form">
          <input type="text" id="displayName" placeholder="Display Name" required>
          <input type="email" id="email" placeholder="Email" required>
          <input type="password" id="password" placeholder="Password" required>
          <button type="submit">Sign Up</button>
        </form>
        <p>Already have an account? <a href="#" id="switch-to-login">Sign In</a></p>
      </div>
    `;
  }
  
  attachEventListeners() {
    const form = this.container.querySelector('#signup-form');
    form.addEventListener('submit', this.handleSubmit.bind(this));
  }
  
  async handleSubmit(event) {
    event.preventDefault();
    
    const displayName = this.container.querySelector('#displayName').value;
    const email = this.container.querySelector('#email').value;
    const password = this.container.querySelector('#password').value;
    
    try {
      await AuthService.signUp(email, password, displayName);
      // User signed up successfully
    } catch (error) {
      alert(error.message);
    }
  }
}
```

## Usage in Main Application

### Update `main.js`:
```javascript
import AuthService from './src/services/AuthService.js';
import { LoginForm, SignUpForm } from './src/components/AuthComponents.js';

// Initialize authentication state
AuthService.onAuthStateChange((user) => {
  if (user) {
    // User is signed in
    showTradingInterface();
  } else {
    // User is signed out
    showAuthInterface();
  }
});

function showAuthInterface() {
  const authContainer = document.getElementById('auth-container');
  new LoginForm(authContainer);
}

function showTradingInterface() {
  // Hide auth interface and show trading interface
  // Your existing application logic here
}
```

## Security Considerations

1. **API Key**: Firebase API key can be public (it's not a secret)
2. **Firestore Rules**: Implement proper security rules in production
3. **Token Expiration**: Handle token expiration gracefully
4. **Emulator Warning**: Never use emulators in production

## Testing with Emulators

1. Start Firebase emulators:
   ```bash
   firebase emulators:start
   ```

2. Use emulator UI at http://localhost:4004 for testing
3. Create test users and data through emulator UI
4. All data is ephemeral unless persistence is configured

## Next Steps

1. Install Firebase SDK: `npm install firebase`
2. Configure environment variables
3. Implement authentication flow
4. Integrate with existing components
5. Add real-time data synchronization
6. Test with Firebase emulators