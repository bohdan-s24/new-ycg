# Web Application Implementation Plan

## 1. Project Setup

### 1.1 Create Next.js Project
```bash
npx create-next-app@latest ycg-web --typescript --tailwind
cd ycg-web
```

### 1.2 Install Dependencies
```bash
npm install @headlessui/react @heroicons/react axios react-hot-toast
```

### 1.3 Set Up Project Structure
```
/pages
  /api
  /auth
    login.tsx
    register.tsx
  /dashboard
    index.tsx
    credits.tsx
    history.tsx
  /pricing
    index.tsx
  /checkout
    success.tsx
    cancel.tsx
  index.tsx
  _app.tsx
  _document.tsx

/components
  /auth
    GoogleSignInButton.tsx
    AuthForm.tsx
  /dashboard
    CreditBalance.tsx
    TransactionHistory.tsx
    ChapterGenerator.tsx
  /layout
    Header.tsx
    Footer.tsx
    Sidebar.tsx
  /ui
    Button.tsx
    Card.tsx
    Input.tsx

/lib
  /api
    auth.ts
    credits.ts
    chapters.ts
    payment.ts
  /context
    AuthContext.tsx
  /hooks
    useAuth.ts
    useCredits.ts
  /utils
    fetcher.ts
```

## 2. Authentication Implementation

### 2.1 Auth Context
Create an authentication context to manage user state across the application:

```tsx
// lib/context/AuthContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types';
import { getUser, verifyToken } from '../api/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on mount
    const token = localStorage.getItem('auth_token');
    if (token) {
      verifyToken(token)
        .then(valid => {
          if (valid) {
            return getUser(token);
          }
          throw new Error('Invalid token');
        })
        .then(userData => {
          setUser(userData);
        })
        .catch(() => {
          localStorage.removeItem('auth_token');
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (token: string) => {
    localStorage.setItem('auth_token', token);
    const userData = await getUser(token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

### 2.2 Login Page
Create a login page with Google Sign-In:

```tsx
// pages/auth/login.tsx
import { useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../../lib/hooks/useAuth';
import { loginWithGoogle } from '../../lib/api/auth';
import GoogleSignInButton from '../../components/auth/GoogleSignInButton';
import toast from 'react-hot-toast';

export default function Login() {
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleGoogleLogin = async (credential: string) => {
    try {
      setLoading(true);
      const { token } = await loginWithGoogle(credential);
      await login(token);
      toast.success('Successfully logged in!');
      router.push('/dashboard');
    } catch (error) {
      toast.error('Failed to log in. Please try again.');
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to your account
          </h2>
        </div>
        <div className="mt-8 space-y-6">
          <GoogleSignInButton onSuccess={handleGoogleLogin} disabled={loading} />
        </div>
      </div>
    </div>
  );
}
```

## 3. Dashboard Implementation

### 3.1 Dashboard Layout
Create a dashboard layout with sidebar navigation:

```tsx
// components/layout/DashboardLayout.tsx
import { ReactNode } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import { useAuth } from '../../lib/hooks/useAuth';
import { useRouter } from 'next/router';

interface DashboardLayoutProps {
  children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  // Redirect if not authenticated
  if (!loading && !isAuthenticated) {
    router.push('/auth/login');
    return null;
  }

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
```

### 3.2 Credit Balance Component
Create a component to display the user's credit balance:

```tsx
// components/dashboard/CreditBalance.tsx
import { useCredits } from '../../lib/hooks/useCredits';
import { Card } from '../ui/Card';

export default function CreditBalance() {
  const { credits, loading } = useCredits();

  return (
    <Card>
      <div className="p-6">
        <h3 className="text-lg font-medium text-gray-900">Credit Balance</h3>
        <div className="mt-2 text-3xl font-bold">
          {loading ? 'Loading...' : credits}
        </div>
        <p className="mt-1 text-sm text-gray-500">
          Each chapter generation costs 1 credit
        </p>
        <button className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
          Buy More Credits
        </button>
      </div>
    </Card>
  );
}
```

### 3.3 Chapter Generator Component
Create a component for generating chapters:

```tsx
// components/dashboard/ChapterGenerator.tsx
import { useState } from 'react';
import { generateChapters } from '../../lib/api/chapters';
import { useCredits } from '../../lib/hooks/useCredits';
import { Card } from '../ui/Card';
import toast from 'react-hot-toast';

export default function ChapterGenerator() {
  const [videoUrl, setVideoUrl] = useState('');
  const [chapters, setChapters] = useState('');
  const [loading, setLoading] = useState(false);
  const { credits, refreshCredits } = useCredits();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!videoUrl) {
      toast.error('Please enter a YouTube video URL');
      return;
    }
    
    if (credits < 1) {
      toast.error('You need at least 1 credit to generate chapters');
      return;
    }
    
    try {
      setLoading(true);
      const videoId = extractVideoId(videoUrl);
      
      if (!videoId) {
        toast.error('Invalid YouTube URL');
        return;
      }
      
      const result = await generateChapters(videoId);
      setChapters(result.chapters);
      refreshCredits(); // Update credit balance
      toast.success('Chapters generated successfully!');
    } catch (error: any) {
      if (error.status === 402) {
        toast.error('Insufficient credits. Please purchase more credits.');
      } else {
        toast.error('Failed to generate chapters. Please try again.');
      }
      console.error('Generation error:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const extractVideoId = (url: string) => {
    const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
  };

  return (
    <Card>
      <div className="p-6">
        <h3 className="text-lg font-medium text-gray-900">Generate Chapters</h3>
        <form onSubmit={handleSubmit} className="mt-4">
          <div>
            <label htmlFor="videoUrl" className="block text-sm font-medium text-gray-700">
              YouTube Video URL
            </label>
            <input
              type="text"
              id="videoUrl"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="https://www.youtube.com/watch?v=..."
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || credits < 1}
            className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
          >
            {loading ? 'Generating...' : 'Generate Chapters'}
          </button>
        </form>
        
        {chapters && (
          <div className="mt-6">
            <h4 className="text-md font-medium text-gray-900">Generated Chapters</h4>
            <pre className="mt-2 p-4 bg-gray-50 rounded-md overflow-auto text-sm">
              {chapters}
            </pre>
            <button
              onClick={() => {
                navigator.clipboard.writeText(chapters);
                toast.success('Copied to clipboard!');
              }}
              className="mt-2 inline-flex items-center px-3 py-1 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Copy to Clipboard
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}
```

## 4. Pricing and Checkout Implementation

### 4.1 Pricing Page
Create a pricing page with plan options:

```tsx
// pages/pricing/index.tsx
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { getPlans, createCheckoutSession } from '../../lib/api/payment';
import { useAuth } from '../../lib/hooks/useAuth';
import toast from 'react-hot-toast';

interface Plan {
  id: string;
  name: string;
  credits: number;
  price: number;
  description: string;
}

export default function Pricing() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const plansData = await getPlans();
        setPlans(plansData);
      } catch (error) {
        console.error('Error fetching plans:', error);
        toast.error('Failed to load pricing plans');
      } finally {
        setLoading(false);
      }
    };

    fetchPlans();
  }, []);

  const handlePurchase = async (planId: string) => {
    if (!isAuthenticated) {
      toast.error('Please log in to purchase credits');
      router.push('/auth/login');
      return;
    }

    try {
      setCheckoutLoading(true);
      const { url } = await createCheckoutSession(
        planId,
        `${window.location.origin}/checkout/success`,
        `${window.location.origin}/checkout/cancel`
      );
      window.location.href = url;
    } catch (error) {
      console.error('Checkout error:', error);
      toast.error('Failed to create checkout session');
    } finally {
      setCheckoutLoading(false);
    }
  };

  if (loading) {
    return <div>Loading pricing plans...</div>;
  }

  return (
    <div className="bg-white">
      <div className="max-w-7xl mx-auto py-24 px-4 sm:px-6 lg:px-8">
        <div className="sm:flex sm:flex-col sm:align-center">
          <h1 className="text-5xl font-extrabold text-gray-900 sm:text-center">Pricing Plans</h1>
          <p className="mt-5 text-xl text-gray-500 sm:text-center">
            Choose the plan that works best for you
          </p>
        </div>
        <div className="mt-12 space-y-4 sm:mt-16 sm:space-y-0 sm:grid sm:grid-cols-3 sm:gap-6 lg:max-w-4xl lg:mx-auto xl:max-w-none xl:mx-0">
          {plans.map((plan) => (
            <div key={plan.id} className="border border-gray-200 rounded-lg shadow-sm divide-y divide-gray-200">
              <div className="p-6">
                <h2 className="text-lg leading-6 font-medium text-gray-900">{plan.name}</h2>
                <p className="mt-4 text-sm text-gray-500">{plan.description}</p>
                <p className="mt-8">
                  <span className="text-4xl font-extrabold text-gray-900">${plan.price}</span>
                </p>
                <p className="mt-2 text-sm text-gray-500">
                  {plan.credits} credits
                </p>
                <button
                  onClick={() => handlePurchase(plan.id)}
                  disabled={checkoutLoading || plan.id === 'free'}
                  className="mt-8 block w-full bg-indigo-600 border border-transparent rounded-md py-2 text-sm font-semibold text-white text-center hover:bg-indigo-700 disabled:bg-gray-400"
                >
                  {plan.id === 'free' ? 'Free with Registration' : 'Buy Now'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

## 5. API Integration

### 5.1 Auth API
Create API client functions for authentication:

```tsx
// lib/api/auth.ts
import axios from 'axios';
import { User } from '../types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://new-ycg.vercel.app/api';

export async function loginWithGoogle(token: string) {
  const response = await axios.post(`${API_URL}/auth/login/google`, {
    token,
    platform: 'web'
  });
  return response.data.data;
}

export async function getUser(token: string): Promise<User> {
  const response = await axios.get(`${API_URL}/auth/user`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return response.data.data;
}

export async function verifyToken(token: string): Promise<boolean> {
  try {
    const response = await axios.post(`${API_URL}/auth/verify`, { token });
    return response.data.data.valid;
  } catch (error) {
    return false;
  }
}
```

### 5.2 Credits API
Create API client functions for credits:

```tsx
// lib/api/credits.ts
import axios from 'axios';
import { getAuthToken } from '../utils/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://new-ycg.vercel.app/api';

export async function getCredits() {
  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');
  
  const response = await axios.get(`${API_URL}/credits/balance`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return response.data.data.balance;
}

export async function getTransactionHistory() {
  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');
  
  const response = await axios.get(`${API_URL}/credits/transactions`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return response.data.data.transactions;
}
```

### 5.3 Chapters API
Create API client functions for chapter generation:

```tsx
// lib/api/chapters.ts
import axios from 'axios';
import { getAuthToken } from '../utils/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://new-ycg.vercel.app/api';

export async function generateChapters(videoId: string) {
  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');
  
  const response = await axios.post(
    `${API_URL}/generate`,
    { videoId },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  );
  return response.data.data;
}
```

### 5.4 Payment API
Create API client functions for payments:

```tsx
// lib/api/payment.ts
import axios from 'axios';
import { getAuthToken } from '../utils/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://new-ycg.vercel.app/api';

export async function getPlans() {
  const response = await axios.get(`${API_URL}/payment/plans`);
  return response.data.data.plans;
}

export async function createCheckoutSession(planId: string, successUrl: string, cancelUrl: string) {
  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');
  
  const response = await axios.post(
    `${API_URL}/payment/checkout`,
    {
      plan_id: planId,
      success_url: successUrl,
      cancel_url: cancelUrl
    },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  );
  return response.data.data;
}

export async function getPurchaseHistory() {
  const token = getAuthToken();
  if (!token) throw new Error('Not authenticated');
  
  const response = await axios.get(`${API_URL}/payment/purchases`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return response.data.data.purchases;
}
```

## 6. Deployment

### 6.1 Prepare for Deployment
Create a Vercel configuration file:

```json
// vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/next"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/$1"
    }
  ],
  "env": {
    "NEXT_PUBLIC_API_URL": "https://new-ycg.vercel.app/api"
  }
}
```

### 6.2 Deploy to Vercel
```bash
vercel
```

Or connect your GitHub repository to Vercel for automatic deployments.
