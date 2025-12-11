"""Next.js project generator.

Generates a complete Next.js project from a structured specification.
"""

import json
from pathlib import Path

from app.models.generation import CodeGenOptions, GeneratedFile, GeneratedProject
from app.models.spec import StructuredSpec


class NextJSProjectGenerator:
    """Generates Next.js projects from specifications."""

    def __init__(
        self,
        spec: StructuredSpec,
        options: CodeGenOptions,
        output_dir: Path,
    ):
        self.spec = spec
        self.options = options
        self.output_dir = output_dir
        self.files: list[GeneratedFile] = []

    async def generate(self) -> GeneratedProject:
        """Generate the complete project."""
        # Generate configuration files
        self._generate_package_json()
        self._generate_tsconfig()
        self._generate_tailwind_config()
        self._generate_next_config()

        # Generate app structure
        self._generate_layout()
        self._generate_page()
        self._generate_globals_css()

        # Generate types from data models
        self._generate_types()

        # Generate API routes
        self._generate_api_routes()

        # Generate components
        self._generate_components()

        # Generate README
        self._generate_readme()

        # Write all files
        for file in self.files:
            file_path = self.output_dir / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file.content)

        return GeneratedProject(
            output_directory=str(self.output_dir),
            files=self.files,
            entry_point="src/app/page.tsx",
            build_command="npm run build",
            start_command="npm run dev",
            dependencies=self._get_dependencies(),
            dev_dependencies=self._get_dev_dependencies(),
        )

    def _add_file(self, path: str, content: str, file_type: str = "source") -> None:
        """Add a file to the generated files list."""
        self.files.append(
            GeneratedFile(path=path, content=content, file_type=file_type)
        )

    def _generate_package_json(self) -> None:
        """Generate package.json."""
        package = {
            "name": self.spec.project_name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint",
            },
            "dependencies": self._get_dependencies(),
            "devDependencies": self._get_dev_dependencies(),
        }

        self._add_file(
            "package.json",
            json.dumps(package, indent=2),
            "config",
        )

    def _generate_tsconfig(self) -> None:
        """Generate tsconfig.json."""
        tsconfig = {
            "compilerOptions": {
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./src/*"]},
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"],
        }

        self._add_file("tsconfig.json", json.dumps(tsconfig, indent=2), "config")

    def _generate_tailwind_config(self) -> None:
        """Generate tailwind.config.ts."""
        config = '''import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
      },
    },
  },
  plugins: [],
};

export default config;
'''
        self._add_file("tailwind.config.ts", config, "config")

    def _generate_next_config(self) -> None:
        """Generate next.config.js."""
        config = '''/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

module.exports = nextConfig;
'''
        self._add_file("next.config.js", config, "config")

    def _generate_layout(self) -> None:
        """Generate app layout."""
        layout = f'''import type {{ Metadata }} from "next";
import {{ Inter }} from "next/font/google";
import "./globals.css";

const inter = Inter({{ subsets: ["latin"] }});

export const metadata: Metadata = {{
  title: "{self.spec.project_name}",
  description: "{self.spec.description}",
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="en">
      <body className={{inter.className}}>
        <div className="min-h-screen bg-gray-50">
          {{children}}
        </div>
      </body>
    </html>
  );
}}
'''
        self._add_file("src/app/layout.tsx", layout)

    def _generate_page(self) -> None:
        """Generate main page."""
        # Generate feature list for display
        features_list = "\n".join(
            f'            <li key="{f.id}" className="flex items-center gap-2">\n'
            f'              <span className="text-primary-500">✓</span> {f.name}\n'
            f"            </li>"
            for f in self.spec.features[:5]
        )

        page = f'''export default function Home() {{
  return (
    <main className="container mx-auto px-4 py-8">
      <header className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          {self.spec.project_name}
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          {self.spec.description}
        </p>
      </header>

      <section className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            Features
          </h2>
          <ul className="space-y-2 text-gray-600">
{features_list}
          </ul>
        </div>
      </section>

      <section className="max-w-4xl mx-auto mt-8">
        <div className="bg-primary-50 rounded-lg p-6 text-center">
          <p className="text-primary-700">
            🚀 This application was generated by App-Agent
          </p>
        </div>
      </section>
    </main>
  );
}}
'''
        self._add_file("src/app/page.tsx", page)

    def _generate_globals_css(self) -> None:
        """Generate global CSS."""
        css = '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply antialiased;
  }
}

@layer components {
  .btn {
    @apply px-4 py-2 rounded-md font-medium transition-colors;
  }
  
  .btn-primary {
    @apply bg-primary-500 text-white hover:bg-primary-600;
  }
  
  .btn-secondary {
    @apply bg-gray-200 text-gray-800 hover:bg-gray-300;
  }
  
  .input {
    @apply w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent;
  }
  
  .card {
    @apply bg-white rounded-lg shadow-md p-6;
  }
}
'''
        self._add_file("src/app/globals.css", css)

    def _generate_types(self) -> None:
        """Generate TypeScript types from data models."""
        if not self.spec.data_models:
            return

        types_content = '''/**
 * Auto-generated types from specification.
 */

'''
        for model in self.spec.data_models:
            types_content += f"export interface {model.name} {{\n"
            for field in model.fields:
                ts_type = self._get_ts_type(field.type)
                optional = "?" if not field.required else ""
                types_content += f"  {field.name}{optional}: {ts_type};\n"
            types_content += "}\n\n"

        self._add_file("src/types/index.ts", types_content)

    def _get_ts_type(self, field_type: str) -> str:
        """Convert field type to TypeScript type."""
        type_map = {
            "string": "string",
            "number": "number",
            "boolean": "boolean",
            "date": "Date",
            "datetime": "Date",
            "uuid": "string",
            "json": "Record<string, unknown>",
            "array": "unknown[]",
            "enum": "string",
        }
        return type_map.get(field_type.lower(), "unknown")

    def _generate_api_routes(self) -> None:
        """Generate API routes from endpoints."""
        if not self.spec.api_endpoints:
            return

        # Group endpoints by path
        routes: dict[str, list] = {}
        for endpoint in self.spec.api_endpoints:
            # Normalize path for Next.js App Router
            path = endpoint.path.replace("/api/", "").replace("{", "[").replace("}", "]")
            if path not in routes:
                routes[path] = []
            routes[path].append(endpoint)

        for path, endpoints in routes.items():
            route_content = self._generate_route_handler(path, endpoints)
            self._add_file(f"src/app/api/{path}/route.ts", route_content)

    def _generate_route_handler(self, path: str, endpoints: list) -> str:
        """Generate a route handler file."""
        handlers = []

        for endpoint in endpoints:
            method = endpoint.method.upper()
            handler = f'''export async function {method}(request: Request) {{
  try {{
    // TODO: Implement {endpoint.description}
    return Response.json({{ message: "{endpoint.description}" }});
  }} catch (error) {{
    console.error("{method} {path} error:", error);
    return Response.json({{ error: "Internal server error" }}, {{ status: 500 }});
  }}
}}
'''
            handlers.append(handler)

        return "import { NextRequest } from 'next/server';\n\n" + "\n".join(handlers)

    def _generate_components(self) -> None:
        """Generate UI components."""
        # Always generate Header component
        header = '''interface HeaderProps {
  title: string;
}

export function Header({ title }: HeaderProps) {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4 py-4">
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
      </div>
    </header>
  );
}
'''
        self._add_file("src/components/Header.tsx", header)

        # Generate Button component
        button = '''interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
  size?: "sm" | "md" | "lg";
  children: React.ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  children,
  className = "",
  ...props
}: ButtonProps) {
  const baseStyles = "font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2";
  
  const variants = {
    primary: "bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-500",
    secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-500",
    danger: "bg-red-500 text-white hover:bg-red-600 focus:ring-red-500",
  };
  
  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-base",
    lg: "px-6 py-3 text-lg",
  };
  
  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
'''
        self._add_file("src/components/Button.tsx", button)

        # Generate Input component
        input_comp = '''interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({ label, error, className = "", ...props }: InputProps) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <input
        className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
          error ? "border-red-500" : "border-gray-300"
        } ${className}`}
        {...props}
      />
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}
'''
        self._add_file("src/components/Input.tsx", input_comp)

        # Generate Card component
        card = '''interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Card({ title, children, className = "" }: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-md p-6 ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      )}
      {children}
    </div>
  );
}
'''
        self._add_file("src/components/Card.tsx", card)

        # Generate index export
        components_index = '''export { Header } from "./Header";
export { Button } from "./Button";
export { Input } from "./Input";
export { Card } from "./Card";
'''
        self._add_file("src/components/index.ts", components_index)

    def _generate_readme(self) -> None:
        """Generate README.md."""
        features_list = "\n".join(f"- {f.name}" for f in self.spec.features)

        readme = f'''# {self.spec.project_name}

{self.spec.description}

## Features

{features_list}

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
```

### Production

```bash
npm start
```

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Language**: TypeScript

---

Generated by [App-Agent](https://github.com/app-agent)
'''
        self._add_file("README.md", readme, "docs")

    def _get_dependencies(self) -> dict[str, str]:
        """Get project dependencies."""
        return {
            "next": "14.0.4",
            "react": "18.2.0",
            "react-dom": "18.2.0",
        }

    def _get_dev_dependencies(self) -> dict[str, str]:
        """Get development dependencies."""
        deps = {
            "@types/node": "20.10.5",
            "@types/react": "18.2.45",
            "@types/react-dom": "18.2.18",
            "autoprefixer": "10.4.16",
            "eslint": "8.56.0",
            "eslint-config-next": "14.0.4",
            "postcss": "8.4.32",
            "tailwindcss": "3.4.0",
            "typescript": "5.3.3",
        }

        if self.options.include_tests:
            deps.update({
                "vitest": "1.1.0",
                "@testing-library/react": "14.1.2",
                "@vitejs/plugin-react": "4.2.1",
                "jsdom": "23.0.1",
            })

        return deps
