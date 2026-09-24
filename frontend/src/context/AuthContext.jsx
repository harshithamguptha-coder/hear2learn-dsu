import { createContext, useContext, useEffect, useState } from 'react'

import { getCurrentUser, login as loginRequest, register as registerRequest } from '../api/client'

const TOKEN_KEY = 'accessible-classroom-token'
const AuthContext = createContext(null)

function saveAuth(result) {
  localStorage.setItem(TOKEN_KEY, result.access_token)
  return result.user
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || '')
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(Boolean(token))

  useEffect(() => {
    let cancelled = false
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return undefined
    }

    getCurrentUser(token)
      .then((currentUser) => {
        if (!cancelled) setUser(currentUser)
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem(TOKEN_KEY)
          setToken('')
          setUser(null)
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [token])

  async function login(credentials) {
    const result = await loginRequest(credentials)
    setToken(result.access_token)
    setUser(saveAuth(result))
    return result.user
  }

  async function register(details) {
    const result = await registerRequest(details)
    setToken(result.access_token)
    setUser(saveAuth(result))
    return result.user
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setToken('')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
