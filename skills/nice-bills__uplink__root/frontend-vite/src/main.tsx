import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { WagmiProvider } from 'wagmi'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RainbowKitProvider, darkTheme } from '@rainbow-me/rainbowkit'
import App from './App'
import { config } from './lib/wallet'
import './index.css'

const queryClient = new QueryClient()

const genesisTheme = darkTheme({
  accentColor: 'hsl(0 0% 100%)',
  accentColorForeground: 'hsl(0 0% 4%)',
  borderRadius: 'large',
  fontStack: 'system',
})

genesisTheme.colors.connectButtonBackground = 'hsl(201 100% 13% / 0.6)'
genesisTheme.colors.connectButtonInnerBackground = 'hsl(0 0% 10%)'
genesisTheme.colors.connectButtonText = 'hsl(0 0% 100%)'
genesisTheme.colors.modalBackground = 'hsl(201 80% 11%)'
genesisTheme.colors.modalBorder = 'hsl(0 0% 18%)'
genesisTheme.fonts.body = "'Inter', sans-serif"

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <WagmiProvider config={config}>
        <QueryClientProvider client={queryClient}>
          <RainbowKitProvider theme={genesisTheme}>
            <App />
          </RainbowKitProvider>
        </QueryClientProvider>
      </WagmiProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
