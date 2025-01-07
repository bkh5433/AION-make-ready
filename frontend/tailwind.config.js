/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        './pages/**/*.{js,jsx}',
        './components/**/*.{js,jsx}',
        './app/**/*.{js,jsx}',
        './src/**/*.{js,jsx}',
    ],
    theme: {
        container: {
            center: true,
            padding: "2rem",
            screens: {
                "2xl": "1400px",
            },
        },
        extend: {
            colors: {
                border: "hsl(var(--border))",
                input: "hsl(var(--input))",
                ring: "hsl(var(--ring))",
                background: "hsl(var(--background))",
                foreground: "hsl(var(--foreground))",
                primary: {
                    DEFAULT: "hsl(var(--primary))",
                    foreground: "hsl(var(--primary-foreground))",
                },
                secondary: {
                    DEFAULT: "hsl(var(--secondary))",
                    foreground: "hsl(var(--secondary-foreground))",
                },
                destructive: {
                    DEFAULT: "hsl(var(--destructive))",
                    foreground: "hsl(var(--destructive-foreground))",
                },
                muted: {
                    DEFAULT: "hsl(var(--muted))",
                    foreground: "hsl(var(--muted-foreground))",
                },
                accent: {
                    DEFAULT: "hsl(var(--accent))",
                    foreground: "hsl(var(--accent-foreground))",
                },
                popover: {
                    DEFAULT: "hsl(var(--popover))",
                    foreground: "hsl(var(--popover-foreground))",
                },
                card: {
                    DEFAULT: "hsl(var(--card))",
                    foreground: "hsl(var(--card-foreground))",
                },
            },
            borderRadius: {
                lg: "var(--radius)",
                md: "calc(var(--radius) - 2px)",
                sm: "calc(var(--radius) - 4px)",
            },
            keyframes: {
                "accordion-down": {
                    from: {height: 0},
                    to: {height: "var(--radix-accordion-content-height)"},
                },
                "accordion-up": {
                    from: {height: "var(--radix-accordion-content-height)"},
                    to: {height: 0},
                },
                "progress-ring": {
                    "0%": {strokeDashoffset: "280"},
                    "100%": {strokeDashoffset: "0"}
                },
                "float-orb": {
                    "0%, 100%": {transform: "translateY(0)"},
                    "50%": {transform: "translateY(-10px)"}
                },
                "glow-pulse": {
                    '0%': {
                        transform: 'scale(1) rotate(0deg)',
                        opacity: '0.4',
                        filter: 'blur(0px)'
                    },
                    '50%': {
                        transform: 'scale(1.3) rotate(180deg)',
                        opacity: '0.2',
                        filter: 'blur(2px)'
                    },
                    '100%': {
                        transform: 'scale(1) rotate(360deg)',
                        opacity: '0.4',
                        filter: 'blur(0px)'
                    }
                },
                "sonar-ping": {
                    '0%': {
                        transform: 'scale(1)',
                        opacity: '0.55'
                    },
                    '35%': {
                        transform: 'scale(2)',
                        opacity: '0.3'
                    },
                    '75%': {
                        transform: 'scale(3.2)',
                        opacity: '0.1'
                    },
                    '100%': {
                        transform: 'scale(4)',
                        opacity: '0'
                    }
                }
            },
            animation: {
                "accordion-down": "accordion-down 0.2s ease-out",
                "accordion-up": "accordion-up 0.2s ease-out",
                "progress-ring": "progress-ring 2s ease-out forwards",
                "float-orb": "float-orb 3s ease-in-out infinite",
                "glow-pulse": "glow-pulse 8s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                "sonar-ping": "sonar-ping 7.5s cubic-bezier(0.15, 0, 0.25, 1) infinite"
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
}