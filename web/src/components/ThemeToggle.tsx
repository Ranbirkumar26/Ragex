"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

type Theme = "light" | "dark";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.classList.toggle("dark", next === "dark");
    localStorage.setItem("ragex-theme", next);
    setTheme(next);
  }

  const Icon = theme === "dark" ? Sun : Moon;
  return (
    <button className="icon-button" onClick={toggleTheme} title="Toggle theme" aria-label="Toggle theme">
      <Icon size={18} />
    </button>
  );
}
