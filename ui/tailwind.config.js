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
                    bg: 'var(--color-vscode-bg)',
                    editor: 'var(--color-vscode-editor)',
                    sidebar: 'var(--color-vscode-sidebar)',
                    activity: 'var(--color-vscode-activity)',
                    text: 'var(--color-vscode-text)',
                    border: 'var(--color-vscode-border)',
                    accent: 'var(--color-vscode-accent)',
                    input: 'var(--color-vscode-input)',
                    'sidebar-header': 'var(--color-vscode-sidebar-header)',
                }
            }
        },
    },
    plugins: [],
}
