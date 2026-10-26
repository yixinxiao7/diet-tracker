import { useState } from 'react'
import { signIn, signUp } from './auth'

const MIN_PASSWORD_LENGTH = 6

function AuthForm({ disabled = false, onSession }) {
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pendingEmail, setPendingEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const isSignUp = mode === 'signup'

  const switchMode = () => {
    setMode(isSignUp ? 'signin' : 'signup')
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    if (isSignUp && password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    setSubmitting(true)
    try {
      if (isSignUp) {
        const { session, needsConfirmation } = await signUp(email.trim(), password)
        if (needsConfirmation) {
          setPendingEmail(email.trim())
          setPassword('')
          setSubmitting(false)
          return
        }
        onSession?.(session)
      } else {
        onSession?.(await signIn(email.trim(), password))
      }
    } catch (err) {
      setError(err.message || 'Authentication failed')
      setSubmitting(false)
    }
  }

  if (pendingEmail) {
    return (
      <div className="form">
        <div className="alert success" role="status">
          Check your email. We sent a confirmation link to {pendingEmail}.
        </div>
        <button
          type="button"
          className="button ghost login-cta"
          onClick={() => {
            setPendingEmail('')
            setMode('signin')
          }}
        >
          Back to sign in
        </button>
      </div>
    )
  }

  return (
    <form className="form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="auth-email">Email</label>
        <input
          id="auth-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <div className="field">
        <label htmlFor="auth-password">Password</label>
        <input
          id="auth-password"
          type="password"
          autoComplete={isSignUp ? 'new-password' : 'current-password'}
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {error && (
        <div className="alert error" role="alert">{error}</div>
      )}
      <button
        type="submit"
        className="button primary login-cta"
        disabled={disabled || submitting}
      >
        {submitting ? 'Please wait…' : isSignUp ? 'Create account' : 'Sign in'}
      </button>
      <p className="muted auth-switch">
        {isSignUp ? 'Already have an account?' : 'New here?'}{' '}
        <button type="button" className="link-button" onClick={switchMode}>
          {isSignUp ? 'Sign in' : 'Create an account'}
        </button>
      </p>
    </form>
  )
}

export default AuthForm
