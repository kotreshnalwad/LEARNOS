import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-foreground flex items-center justify-center">
              <svg className="w-4 h-4 text-background" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <span className="font-serif text-xl">LearnOS</span>
          </div>
          <h1 className="font-serif text-2xl text-foreground">Welcome back</h1>
          <p className="text-muted-foreground text-sm mt-1 font-light">Sign in to continue learning</p>
        </div>
        <SignIn
          appearance={{
            elements: {
              rootBox: 'w-full',
              card: 'bg-card border border-border shadow-sm rounded-2xl',
              headerTitle: 'font-serif',
              formButtonPrimary: 'bg-foreground hover:opacity-85 rounded-xl',
              footerActionLink: 'text-gold hover:text-gold-dark',
            },
          }}
        />
      </div>
    </div>
  )
}
