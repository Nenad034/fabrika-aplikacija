/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                vscode: {
                    bg: '#121212',
                    editor: '#1e1e1e',
                    sidebar: '#333333',
                    activity: '#2c2c2c',
                    text: '#cccccc',
                    border: '#444444',
                    accent: '#3b82f6',
                }
            }
        },
    },
    plugins: [],
}
