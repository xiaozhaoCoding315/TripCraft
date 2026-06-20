import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

// Import Google Fonts
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
})

function Root() {
  const [loggedIn, setLoggedIn] = React.useState(() => {
    return !!localStorage.getItem('tripcraft_token')
  })

  const handleLogout = () => {
    localStorage.removeItem('tripcraft_token')
    localStorage.removeItem('tripcraft_user')
    setLoggedIn(false)
  }

  const handleLoginSuccess = () => {
    setLoggedIn(true)
  }

  return (
    <App
      loggedIn={loggedIn}
      onLogout={handleLogout}
      onLoginSuccess={handleLoginSuccess}
    />
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <Root />
    </QueryClientProvider>
  </React.StrictMode>,
)
