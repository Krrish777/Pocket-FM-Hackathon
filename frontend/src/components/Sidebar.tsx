"use client";

import {
  BookOpen,
  Heart,
  Home,
  type LucideIcon,
  Moon,
  Orbit,
  Settings,
} from "lucide-react";

import { ProceduralPortrait } from "@/components/ProceduralPortrait";
import { playSelect } from "@/lib/audio";
import { t, ui, type Locale } from "@/lib/mockData";
import { cn } from "@/lib/utils";
import { useDemoStore } from "@/store/demoStore";

export const SIDEBAR_WIDTH = 104;

/**
 * The persistent left rail — new for the Shelf redesign (see reference mock).
 *
 * Only "home" is a real destination (back to the shelf). The other four items
 * are shelf-realism: present at full visual weight so the app doesn't read as
 * a single screen, same spirit as the two non-playable story cards. Clicking
 * them sets the active tint but does not navigate — there is nothing behind
 * them yet.
 */
const NAV_ITEMS: { id: string; icon: LucideIcon; label: keyof typeof ui }[] = [
  { id: "home", icon: Home, label: "navHome" },
  { id: "journeys", icon: BookOpen, label: "navJourneys" },
  { id: "timeMachine", icon: Moon, label: "navTimeMachine" },
  { id: "universe", icon: Orbit, label: "navUniverse" },
  { id: "favorites", icon: Heart, label: "navFavorites" },
  { id: "settings", icon: Settings, label: "navSettings" },
];

export function Sidebar({ locale }: { locale: Locale }) {
  const active = useDemoStore((s) => s.sidebarActive);
  const setSidebarActive = useDemoStore((s) => s.setSidebarActive);
  const reset = useDemoStore((s) => s.reset);

  return (
    <aside
      style={{ width: SIDEBAR_WIDTH }}
      className="border-ink-line bg-shell-void fixed inset-y-0 left-0 z-50 flex flex-col items-center border-r py-6"
    >
      <div
        className="flex size-11 items-center justify-center rounded-full"
        style={{
          background: "linear-gradient(135deg, #f2994a, #e05f8a)",
        }}
        aria-hidden="true"
      >
        <Moon className="size-5 text-white" strokeWidth={2} fill="white" />
      </div>

      <nav
        className="mt-10 flex flex-1 flex-col items-center gap-2"
        aria-label="Primary"
      >
        {NAV_ITEMS.map(({ id, icon: Icon, label }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              type="button"
              aria-pressed={isActive}
              onClick={() => {
                playSelect();
                setSidebarActive(id);
                if (id === "home") reset();
              }}
              className={cn(
                "flex w-[76px] cursor-pointer flex-col items-center gap-1.5 rounded-2xl px-2 py-3 transition-colors duration-150 ease-out",
                isActive
                  ? "bg-accent-wash text-accent"
                  : "text-ink-faint hover:text-ink-muted",
              )}
            >
              <Icon className="size-5" strokeWidth={1.75} />
              <span className="type-index text-[0.6rem] leading-tight normal-case">
                {t(ui[label], locale)}
              </span>
            </button>
          );
        })}
      </nav>

      <button
        type="button"
        aria-label="Account"
        className="border-ink-line block size-9 cursor-pointer overflow-hidden rounded-full border"
      >
        <ProceduralPortrait characterId="operator" initial="C" />
      </button>
    </aside>
  );
}
