import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'LAE v4 Substitution Engine',
  description: 'Intelligent lighting substitution and matching engine',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <nav className="navbar">
          <div className="navbar-logo">
            <b>LAE</b> Lighting Substitution Engine <span className="version-badge">v4</span>
          </div>
          <div className="navbar-links">
            <a href="#" className="active">Dashboard</a>
            <a href="#">Projects</a>
            <a href="#">Templates</a>
            <a href="#">Support</a>
          </div>
          <button className="btn-new-project">New Project</button>
        </nav>
        <main className="container" style={{ flex: 1 }}>
          {children}
        </main>
        <footer className="site-footer">
          <div>© 2026 Lighting Substitution Engine. All rights reserved.</div>
          <div className="site-footer-links">
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Contact</a>
          </div>
        </footer>
      </body>
    </html>
  )
}
