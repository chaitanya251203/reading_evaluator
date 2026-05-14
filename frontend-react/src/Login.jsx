import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { BookOpen, AlertCircle } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE || (window.location.hostname === "localhost" && window.location.port === "5173" ? "http://localhost:8000" : window.location.origin);

export default function Login({ onLogin }) {
  const [isSignup, setIsSignup] = useState(false);
  const [name, setName] = useState('');
  const [subject, setSubject] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const endpoint = isSignup ? `${API}/auth/signup` : `${API}/auth/login`;
      const body = isSignup ? { name, subject, email, password } : { email, password };
      
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      if (!res.ok) {
        const d = await res.json().catch(()=>({}));
        throw new Error(d.detail || 'Authentication failed');
      }
      
      const data = await res.json();
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    setError('');
    
    try {
      const res = await fetch(`${API}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: credentialResponse.credential })
      });
      
      if (!res.ok) throw new Error('Google authentication failed');
      
      const data = await res.json();
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', fontFamily: 'var(--font)' }}>
      <div style={{ background: 'var(--surface)', padding: '40px', borderRadius: '24px', boxShadow: 'var(--shadow)', width: '100%', maxWidth: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <BookOpen size={48} color="var(--primary)" style={{ marginBottom: '16px' }} />
          <h1 style={{ fontSize: '28px', color: 'var(--ink)', margin: 0 }}>Welcome to Vāchanam</h1>
          <p style={{ color: 'var(--ink3)', marginTop: '8px' }}>Log in to access your dashboard</p>
        </div>

        {error && (
          <div style={{ background: '#ffebee', color: '#c62828', padding: '12px', borderRadius: '8px', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}

        <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'center' }}>
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => setError('Google Login Failed')}
            theme="outline"
            size="large"
            text="continue_with"
            width="100%"
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', margin: '20px 0', color: 'var(--ink3)', fontSize: '14px' }}>
          <div style={{ flex: 1, height: '1px', background: 'var(--ink4)' }}></div>
          <span style={{ padding: '0 10px' }}>or {isSignup ? 'sign up' : 'log in'} with email</span>
          <div style={{ flex: 1, height: '1px', background: 'var(--ink4)' }}></div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {isSignup && (
            <>
              <input
                type="text"
                placeholder="Full Name"
                required
                value={name}
                onChange={e => setName(e.target.value)}
                style={{ padding: '12px 16px', borderRadius: '12px', border: '1px solid var(--ink4)', fontSize: '16px', outline: 'none' }}
              />
              <input
                type="text"
                placeholder="Subject (e.g. English)"
                required
                value={subject}
                onChange={e => setSubject(e.target.value)}
                style={{ padding: '12px 16px', borderRadius: '12px', border: '1px solid var(--ink4)', fontSize: '16px', outline: 'none' }}
              />
            </>
          )}
          <input
            type="email"
            placeholder="Email Address"
            required
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={{ padding: '12px 16px', borderRadius: '12px', border: '1px solid var(--ink4)', fontSize: '16px', outline: 'none' }}
          />
          <input
            type="password"
            placeholder="Password"
            required
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={{ padding: '12px 16px', borderRadius: '12px', border: '1px solid var(--ink4)', fontSize: '16px', outline: 'none' }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '14px',
              borderRadius: '12px',
              background: 'var(--primary)',
              color: 'white',
              border: 'none',
              fontSize: '16px',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              marginTop: '8px'
            }}
          >
            {loading ? (isSignup ? 'Signing up...' : 'Logging in...') : (isSignup ? 'Sign Up' : 'Log In')}
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '14px', color: 'var(--ink3)' }}>
          {isSignup ? "Already have an account? " : "Don't have an account? "}
          <button 
            type="button" 
            onClick={() => { setIsSignup(!isSignup); setError(''); }} 
            style={{ background: 'none', border: 'none', color: 'var(--primary)', fontWeight: 'bold', cursor: 'pointer', padding: 0 }}
          >
            {isSignup ? 'Log In' : 'Sign Up'}
          </button>
        </div>
      </div>
    </div>
  );
}
